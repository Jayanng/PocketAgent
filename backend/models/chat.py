from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class Conversation(BaseModel):
    id: str
    agent_id: str
    title: str | None = None
    created_at: datetime | None = None


class ConversationCreate(BaseModel):
    agent_id: str
    title: str | None = None


class Message(BaseModel):
    id: str
    conversation_id: str
    role: Literal["user", "assistant"]
    content: str
    chain_calls: list[dict] = Field(default_factory=list)
    tokens_used: int = 0
    created_at: datetime | None = None


class MessageCreate(BaseModel):
    conversation_id: str
    role: Literal["user", "assistant"]
    content: str
    chain_calls: list[dict] = Field(default_factory=list)
    tokens_used: int = 0


class RelayLog(BaseModel):
    id: str
    agent_id: str | None = None
    chain: str
    method: str
    request_payload: dict = Field(default_factory=dict)
    response_status: int
    latency_ms: int
    relay_cost_pokt: float
    created_at: datetime | None = None


class RelayLogCreate(BaseModel):
    agent_id: str | None = None
    chain: str
    method: str
    request_payload: dict = Field(default_factory=dict)
    response_status: int = 200
    latency_ms: int = 0
    relay_cost_pokt: float = 0.0


class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None
    agent_id: str | None = None
    connected_wallet_address: str | None = None


class ChatResponse(BaseModel):
    conversation_id: str
    message: Message


class ChatAPIResponse(BaseModel):
    response: str
    conversation_id: str
    chain_calls: list[dict] = Field(default_factory=list)
    tokens_used: int = 0


class ConversationSummary(BaseModel):
    id: str
    title: str
    created_at: datetime | str | None = None


class ConversationMessageResponse(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    chain_calls: list[dict] = Field(default_factory=list)
    created_at: datetime | str | None = None
