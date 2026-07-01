from typing import Any
import asyncio
import json
import sqlite3

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from openai import OpenAIError

try:
    from ..database import (
        delete_conversation,
        get_agent,
        get_conversation,
        get_db,
        list_conversations,
        list_messages,
    )
    from ..models.chat import ChatAPIResponse, ConversationMessageResponse, ConversationSummary, ChatRequest
    from ..services.agent_auth import verify_agent_access_token
    from ..services.ai_agent import AIAgentService
    from ..services.confirmation import BROKER as CONFIRMATION_BROKER
except ImportError:
    from database import (
        delete_conversation,
        get_agent,
        get_conversation,
        get_db,
        list_conversations,
        list_messages,
    )
    from models.chat import ChatAPIResponse, ConversationMessageResponse, ConversationSummary, ChatRequest
    from services.agent_auth import verify_agent_access_token
    from services.ai_agent import AIAgentService
    from services.confirmation import BROKER as CONFIRMATION_BROKER

router = APIRouter(prefix="/api", tags=["chat"])


def _require_agent_access(agent: dict[str, Any], access_token: str | None) -> None:
    if not verify_agent_access_token(agent, access_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Valid X-Agent-Access-Token header is required for this agent.",
        )


@router.post("/chat", response_model=ChatAPIResponse)
async def chat(
    request: ChatRequest,
    access_token: str | None = Header(None, alias="X-Agent-Access-Token"),
    db=Depends(get_db),
) -> dict[str, Any]:
    if not request.agent_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="agent_id is required",
        )
    agent = await get_agent(db, request.agent_id)
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    if not agent.get("is_active", True):
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Agent is inactive")
    _require_agent_access(agent, access_token)

    try:
        service = AIAgentService()
        try:
            chat_kwargs: dict[str, Any] = {
                "message": request.message,
                "agent_id": request.agent_id,
                "conversation_id": request.conversation_id,
            }
            if request.connected_wallet_address:
                chat_kwargs["connected_wallet_address"] = request.connected_wallet_address
            result = await service.chat(**chat_kwargs)
        finally:
            close = getattr(service, "close", None)
            if close is not None:
                await close()
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        message = str(exc)
        code = status.HTTP_410_GONE if "inactive" in message.lower() else status.HTTP_403_FORBIDDEN
        raise HTTPException(status_code=code, detail=message) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except OpenAIError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"OpenAI request failed: {exc}",
        ) from exc
    except sqlite3.IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Chat persistence failed: {exc}",
        ) from exc
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid tool arguments: missing {exc}",
        ) from exc

    message = result["message"]
    return {
        "response": message["content"],
        "conversation_id": result["conversation_id"],
        "chain_calls": message.get("chain_calls", []),
        "tokens_used": message.get("tokens_used", 0),
    }


@router.get("/conversations", response_model=list[ConversationSummary])
async def conversations(
    agent_id: str = Query(...),
    access_token: str | None = Header(None, alias="X-Agent-Access-Token"),
    db=Depends(get_db),
) -> list[dict[str, Any]]:
    agent = await get_agent(db, agent_id)
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    if not agent.get("is_active", True):
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Agent is inactive")
    _require_agent_access(agent, access_token)

    rows = await list_conversations(db, agent_id)
    return [
        {
            "id": row["id"],
            "title": row.get("title") or "Untitled conversation",
            "created_at": row.get("created_at"),
        }
        for row in rows
    ]


@router.get("/conversations/{conversation_id}/messages", response_model=list[ConversationMessageResponse])
async def conversation_messages(
    conversation_id: str,
    access_token: str | None = Header(None, alias="X-Agent-Access-Token"),
    db=Depends(get_db),
) -> list[dict[str, Any]]:
    conversation = await get_conversation(db, conversation_id)
    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    agent = await get_agent(db, conversation["agent_id"])
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    _require_agent_access(agent, access_token)

    rows = await list_messages(db, conversation_id, limit=500)
    return [
        {
            "role": row["role"],
            "content": row["content"],
            "chain_calls": row.get("chain_calls", []),
            "created_at": row.get("created_at"),
        }
        for row in rows
    ]


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_conversation(
    conversation_id: str,
    access_token: str | None = Header(None, alias="X-Agent-Access-Token"),
    db=Depends(get_db),
) -> None:
    conversation = await get_conversation(db, conversation_id)
    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    agent = await get_agent(db, conversation["agent_id"])
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    _require_agent_access(agent, access_token)
    deleted = await delete_conversation(db, conversation_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )


@router.get("/conversations/{conversation_id}/stream")
async def conversation_stream(
    conversation_id: str,
    request: Request,
    access_token: str | None = Header(None, alias="X-Agent-Access-Token"),
    token: str | None = Query(None, alias="access_token"),
    db=Depends(get_db),
) -> StreamingResponse:
    """Server-Sent Events stream for a conversation.

    Emits a ``ping`` event on connect, then a ``tx_confirmation`` event for each
    new on-chain confirmation message written by the background polling
    service. Stays open until the client disconnects.

    ``EventSource`` cannot set custom headers, so ``access_token`` is also
    accepted as a query parameter as a fallback for browser clients. Prefer
    the ``X-Agent-Access-Token`` header in non-browser contexts.
    """
    # Query param is for browser EventSource; header takes precedence.
    effective_token = access_token or token
    conversation = await get_conversation(db, conversation_id)
    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    agent = await get_agent(db, conversation["agent_id"])
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    _require_agent_access(agent, effective_token)

    subscriber = await CONFIRMATION_BROKER.subscribe(conversation_id)

    async def event_generator() -> Any:
        try:
            # Initial ping so the client knows the stream is live.
            yield _format_sse({"type": "ping", "conversation_id": conversation_id})
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(subscriber.queue.get(), timeout=15.0)
                except asyncio.TimeoutError:
                    # Heartbeat keeps proxies from idling the connection out.
                    yield _format_sse({"type": "ping", "conversation_id": conversation_id})
                    continue
                yield _format_sse(event)
        finally:
            await CONFIRMATION_BROKER.unsubscribe(subscriber)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # disable nginx buffering if proxied
            "Connection": "keep-alive",
        },
    )


def _format_sse(payload: dict[str, Any]) -> str:
    """Serialize a dict as an SSE ``data:`` frame."""
    return f"data: {json.dumps(payload, separators=(',', ':'))}\n\n"
