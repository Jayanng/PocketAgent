from pydantic import BaseModel, Field


class NativeCurrency(BaseModel):
    name: str
    symbol: str
    decimals: int = 18


class Chain(BaseModel):
    key: str
    name: str
    chain_id: int
    rpc_url: str
    block_explorer_url: str
    native_currency: NativeCurrency


class ChainListResponse(BaseModel):
    chains: list[Chain] = Field(default_factory=list)

