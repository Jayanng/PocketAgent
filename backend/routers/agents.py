from typing import Any, Literal, Union
import sqlite3
import time
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi import Query
from pydantic import BaseModel, Field

try:
    from ..database import create_agent, get_agent, get_db, list_agents, update_agent
    from ..models.agent import AgentCreateResponse, AgentDetail, AgentFundResponse, AgentSummary
    from ..services.agent_auth import generate_agent_access_token, hash_agent_access_token, verify_agent_access_token
    from ..services.agent_token_service import (
        generate_access_token as generate_new_access_token,
        hash_access_token,
        verify_proof,
    )
    from ..services.pocket_rpc import PocketRPCClient
    from ..services.wallets import (
        create_agent_wallets,
        ensure_agent_write_wallets,
        wallet_address_for_chain,
        wallet_maps,
    )
except ImportError:
    from database import create_agent, get_agent, get_db, list_agents, update_agent
    from models.agent import AgentCreateResponse, AgentDetail, AgentFundResponse, AgentSummary
    from services.agent_auth import generate_agent_access_token, hash_agent_access_token, verify_agent_access_token
    from services.agent_token_service import (
        generate_access_token as generate_new_access_token,
        hash_access_token,
        verify_proof,
    )
    from services.pocket_rpc import PocketRPCClient
    from services.wallets import (
        create_agent_wallets,
        ensure_agent_write_wallets,
        wallet_address_for_chain,
        wallet_maps,
    )

router = APIRouter(prefix="/api/agents", tags=["agents"])


class AgentCreateRequest(BaseModel):
    name: str
    description: str | None = None
    chains: list[str] = Field(default_factory=list)
    capabilities: list[str] = Field(default_factory=list)
    spending_cap: float = 0.1


class AgentUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    chains: list[str] | None = None
    capabilities: list[str] | None = None
    spending_cap: float | None = None


class CurrentTokenProof(BaseModel):
    type: Literal["current_token"] = "current_token"
    token: str


class WalletSignatureProof(BaseModel):
    type: Literal["wallet_signature"] = "wallet_signature"
    chain: str
    message: str
    signature: str
    public_key: str = ""


class ReissueRequest(BaseModel):
    proof: Union[CurrentTokenProof, WalletSignatureProof] = Field(..., discriminator="type")


def _agent_summary(agent: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": agent["id"],
        "name": agent["name"],
        "description": agent.get("description"),
        "chains": agent.get("chains", []),
        "capabilities": agent.get("capabilities", []),
        "wallet_address": agent.get("wallet_address"),
        "spending_cap": agent.get("spending_cap", 0.1),
        "is_active": agent.get("is_active", True),
    }


def _agent_detail(agent: dict[str, Any]) -> dict[str, Any]:
    detail = {
        key: value
        for key, value in agent.items()
        if key not in {"encrypted_private_key", "encrypted_wallets", "access_token_hash"}
    }
    if detail.get("wallet_addresses") is None:
        detail["wallet_addresses"] = {}
    if detail.get("total_spent_by_chain") is None:
        detail["total_spent_by_chain"] = {}
    return detail


def _require_agent_access(agent: dict[str, Any], access_token: str | None) -> None:
    if not verify_agent_access_token(agent, access_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Valid X-Agent-Access-Token header is required for this agent.",
        )


@router.post("", response_model=AgentCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_new_agent(request: AgentCreateRequest, db=Depends(get_db)) -> dict[str, Any]:
    access_token = generate_agent_access_token()
    try:
        wallets = create_agent_wallets()
        encrypted_wallets, wallet_addresses = wallet_maps(wallets)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Wallet SDK dependency is unavailable: {exc}",
        ) from exc

    try:
        agent = await create_agent(
            db=db,
            name=request.name,
            description=request.description,
            chains=request.chains,
            capabilities=request.capabilities or ["read", "transact", "compare"],
            encrypted_private_key=encrypted_wallets["evm"],
            wallet_address=wallet_addresses["evm"],
            encrypted_wallets=encrypted_wallets,
            wallet_addresses=wallet_addresses,
            access_token_hash=hash_agent_access_token(access_token),
            spending_cap=request.spending_cap,
        )
    except sqlite3.DatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent persistence failed: {exc}",
        ) from exc
    return {
        "id": agent["id"],
        "name": agent["name"],
        "wallet_address": agent["wallet_address"],
        "wallet_addresses": agent.get("wallet_addresses", {}),
        "access_token": access_token,
    }


@router.get("", response_model=list[AgentSummary])
async def get_agents(db=Depends(get_db)) -> list[dict[str, Any]]:
    agents = await list_agents(db)
    return [_agent_summary(agent) for agent in agents]


@router.get("/{agent_id}", response_model=AgentDetail)
async def get_agent_detail(
    agent_id: str,
    access_token: str | None = Header(None, alias="X-Agent-Access-Token"),
    db=Depends(get_db),
) -> dict[str, Any]:
    agent = await get_agent(db, agent_id)
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    _require_agent_access(agent, access_token)
    agent = await ensure_agent_write_wallets(db, agent)
    return _agent_detail(agent)


@router.put("/{agent_id}", response_model=AgentDetail)
async def update_agent_config(
    agent_id: str,
    request: AgentUpdateRequest,
    access_token: str | None = Header(None, alias="X-Agent-Access-Token"),
    db=Depends(get_db),
) -> dict[str, Any]:
    existing = await get_agent(db, agent_id)
    if existing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    if not existing.get("is_active", True):
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Agent is inactive")
    _require_agent_access(existing, access_token)

    updates = request.model_dump(exclude_unset=True)
    agent = await update_agent(db, agent_id, **updates)
    return _agent_detail(agent)


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def soft_delete_agent(
    agent_id: str,
    access_token: str | None = Header(None, alias="X-Agent-Access-Token"),
    db=Depends(get_db),
) -> None:
    existing = await get_agent(db, agent_id)
    if existing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    _require_agent_access(existing, access_token)
    agent = await update_agent(db, agent_id, is_active=False)
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")


@router.post("/{agent_id}/fund", response_model=AgentFundResponse)
async def fund_agent(
    agent_id: str,
    chain: str = Query("ethereum"),
    access_token: str | None = Header(None, alias="X-Agent-Access-Token"),
    db=Depends(get_db),
) -> dict[str, Any]:
    agent = await get_agent(db, agent_id)
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    if not agent.get("is_active", True):
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Agent is inactive")
    _require_agent_access(agent, access_token)
    wallet_address = wallet_address_for_chain(agent, chain)
    if not wallet_address:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent has no wallet configured for chain: {chain}",
        )
    protocol = PocketRPCClient().get_protocol(chain)
    return {
        "id": agent["id"],
        "wallet_address": wallet_address,
        "chain": chain,
        "protocol": protocol,
    }


@router.get("/{agent_id}/balances")
async def get_agent_balances(
    agent_id: str,
    access_token: str | None = Header(None, alias="X-Agent-Access-Token"),
    db=Depends(get_db),
) -> dict[str, Any]:
    agent = await get_agent(db, agent_id)
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    if not agent.get("is_active", True):
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Agent is inactive")
    _require_agent_access(agent, access_token)

    chains = [str(chain) for chain in agent.get("chains", [])]
    rpc = PocketRPCClient()
    balance_entries: dict[str, Any] = {}
    for chain in chains:
        wallet_address = wallet_address_for_chain(agent, chain)
        if not wallet_address:
            balance_entries[chain] = {"error": f"No wallet configured for chain {chain}"}
            continue
        try:
            balance_entries[chain] = await rpc.get_balance(chain, wallet_address)
        except Exception as exc:  # noqa: BLE001 - surface per-chain balance failure
            balance_entries[chain] = {"error": str(exc)}
    return {
        "agent_id": agent_id,
        "wallet_address": agent.get("wallet_address"),
        "wallet_addresses": agent.get("wallet_addresses", {}),
        "balances": balance_entries,
    }


@router.get("/{agent_id}/reissue-challenge")
async def reissue_challenge(agent_id: str, db=Depends(get_db)) -> dict[str, Any]:
    """Return the canonical message the user must sign for reissue.

    The challenge is unauthenticated (the user is proving wallet ownership, not
    token ownership), but we 404 on unknown agents to avoid probing.
    """
    agent = await get_agent(db, agent_id)
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    if not agent.get("is_active", True):
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Agent is inactive")
    timestamp = int(time.time())
    message = f"pocketagent:reissue:{agent_id}:{timestamp}"
    return {"message": message, "timestamp": timestamp}


@router.post("/{agent_id}/reissue-token")
async def reissue_access_token(
    agent_id: str,
    body: ReissueRequest,
    db=Depends(get_db),
) -> dict[str, Any]:
    """Issue a new access token, invalidating the old one.

    Two proof types are accepted:
      - current_token: caller proves they hold the existing token
      - wallet_signature: caller proves wallet ownership by signing a
        challenge with the wallet that owns this agent
    """
    agent = await get_agent(db, agent_id)
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    if not agent.get("is_active", True):
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Agent is inactive")

    proof_dict = body.proof.model_dump()
    if not verify_proof(agent, proof_dict):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid proof")

    # Replay protection for wallet signatures (5 minute window)
    if body.proof.type == "wallet_signature":
        try:
            parts = body.proof.message.split(":")
            signed_ts = int(parts[-1])
        except (ValueError, IndexError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Malformed challenge message",
            )
        if abs(int(time.time()) - signed_ts) > 300:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Challenge expired; sign a fresh message",
            )

    new_token = generate_new_access_token()
    new_hash = hash_access_token(new_token)
    now_iso = datetime.now(timezone.utc).isoformat()
    await update_agent(
        db,
        agent_id,
        access_token_hash=new_hash,
        access_token_created_at=now_iso,
        access_token_revoked_at=None,
    )

    updated = await get_agent(db, agent_id)
    return {
        "access_token": new_token,
        "access_token_created_at": now_iso,
        "agent": _agent_detail(updated) if updated else None,
    }
