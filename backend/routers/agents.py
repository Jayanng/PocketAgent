from typing import Any
import sqlite3

from eth_account import Account
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

try:
    from ..database import create_agent, get_agent, get_db, list_agents, update_agent
    from ..models.agent import AgentCreateResponse, AgentDetail, AgentFundResponse, AgentSummary
    from ..services.encryption import encrypt_private_key
    from ..services.pocket_rpc import PocketRPCClient
except ImportError:
    from database import create_agent, get_agent, get_db, list_agents, update_agent
    from models.agent import AgentCreateResponse, AgentDetail, AgentFundResponse, AgentSummary
    from services.encryption import encrypt_private_key
    from services.pocket_rpc import PocketRPCClient

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
        "chains": agent.get("chains", []),
        "capabilities": agent.get("capabilities", []),
        "wallet_address": agent.get("wallet_address"),
        "is_active": agent.get("is_active", True),
    }


def _agent_detail(agent: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in agent.items()
        if key != "encrypted_private_key"
    }


@router.post("", response_model=AgentCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_new_agent(request: AgentCreateRequest, db=Depends(get_db)) -> dict[str, Any]:
    account = Account.create()
    private_key = account.key.hex()
    try:
        encrypted_private_key = encrypt_private_key(private_key)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    try:
        agent = await create_agent(
            db=db,
            name=request.name,
            description=request.description,
            chains=request.chains,
            capabilities=request.capabilities or ["read", "transact", "compare"],
            encrypted_private_key=encrypted_private_key,
            wallet_address=account.address,
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
    }


@router.get("", response_model=list[AgentSummary])
async def get_agents(db=Depends(get_db)) -> list[dict[str, Any]]:
    agents = await list_agents(db)
    return [_agent_summary(agent) for agent in agents]


@router.get("/{agent_id}", response_model=AgentDetail)
async def get_agent_detail(agent_id: str, db=Depends(get_db)) -> dict[str, Any]:
    agent = await get_agent(db, agent_id)
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return _agent_detail(agent)


@router.put("/{agent_id}", response_model=AgentDetail)
async def update_agent_config(
    agent_id: str,
    request: AgentUpdateRequest,
    db=Depends(get_db),
) -> dict[str, Any]:
    existing = await get_agent(db, agent_id)
    if existing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    if not existing.get("is_active", True):
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Agent is inactive")

    updates = request.model_dump(exclude_unset=True)
    agent = await update_agent(db, agent_id, **updates)
    return _agent_detail(agent)


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def soft_delete_agent(agent_id: str, db=Depends(get_db)) -> None:
    agent = await update_agent(db, agent_id, is_active=False)
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")


@router.post("/{agent_id}/fund", response_model=AgentFundResponse)
async def fund_agent(agent_id: str, db=Depends(get_db)) -> dict[str, Any]:
    agent = await get_agent(db, agent_id)
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    if not agent.get("is_active", True):
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Agent is inactive")
    return {
        "id": agent["id"],
        "wallet_address": agent["wallet_address"],
    }


@router.get("/{agent_id}/balances")
async def get_agent_balances(agent_id: str, db=Depends(get_db)) -> dict[str, Any]:
    agent = await get_agent(db, agent_id)
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    if not agent.get("is_active", True):
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Agent is inactive")

    wallet_address = agent.get("wallet_address")
    if not wallet_address:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent wallet not found")

    chains = [str(chain) for chain in agent.get("chains", [])]
    balances = await PocketRPCClient().multi_chain_balance(wallet_address, chains)
    return {
        "agent_id": agent_id,
        "wallet_address": wallet_address,
        "balances": balances.get("balances", {}),
    }
