from typing import Any
import sqlite3
from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi import Query
from pydantic import BaseModel, Field

try:
    from ..database import create_agent, get_agent, get_db, list_agents, update_agent
    from ..models.agent import AgentCreateResponse, AgentDetail, AgentFundResponse, AgentSummary
    from ..services.agent_auth import generate_agent_access_token, hash_agent_access_token, verify_agent_access_token
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
