from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class Agent(BaseModel):
    id: str
    name: str
    description: str | None = None
    chains: list[str] = Field(default_factory=list)
    capabilities: list[str] = Field(default_factory=list)
    encrypted_private_key: str
    wallet_address: str | None = None
    spending_cap: float = 0.1
    total_spent: float = 0.0
    is_active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None


class AgentCreate(BaseModel):
    name: str
    description: str | None = None
    chains: list[str] = Field(default_factory=list)
    capabilities: list[str] = Field(default_factory=lambda: ["read", "transact", "compare"])
    encrypted_private_key: str
    wallet_address: str | None = None
    spending_cap: float = 0.1


class AgentUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    chains: list[str] | None = None
    capabilities: list[str] | None = None
    wallet_address: str | None = None
    spending_cap: float | None = None
    total_spent: float | None = None
    is_active: bool | None = None


class AgentResponse(BaseModel):
    data: Agent
    meta: dict[str, Any] = Field(default_factory=dict)


class AgentCreateResponse(BaseModel):
    id: str
    name: str
    wallet_address: str


class AgentSummary(BaseModel):
    id: str
    name: str
    chains: list[str] = Field(default_factory=list)
    capabilities: list[str] = Field(default_factory=list)
    wallet_address: str | None = None
    is_active: bool = True


class AgentDetail(BaseModel):
    id: str
    name: str
    description: str | None = None
    chains: list[str] = Field(default_factory=list)
    capabilities: list[str] = Field(default_factory=list)
    wallet_address: str | None = None
    spending_cap: float = 0.1
    total_spent: float = 0.0
    is_active: bool = True
    created_at: datetime | str | None = None
    updated_at: datetime | str | None = None


class AgentFundResponse(BaseModel):
    id: str
    wallet_address: str
