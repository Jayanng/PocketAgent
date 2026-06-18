from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o"
    gmi_api_key: str = ""
    # Pocket Network RPC Endpoints (Shannon, post June 2025)
    # Format: https://{chain-slug}.api.pocket.network
    pocket_rpc_url: str = "https://eth.api.pocket.network"  # backwards-compatible alias for ethereum
    pocket_rpc_ethereum: str = "https://eth.api.pocket.network"
    pocket_rpc_polygon: str = "https://poly.api.pocket.network"
    pocket_rpc_arbitrum: str = "https://arb-one.api.pocket.network"
    pocket_rpc_bsc: str = "https://bsc.api.pocket.network"
    pocket_rpc_optimism: str = "https://op.api.pocket.network"
    pocket_rpc_avalanche: str = "https://avax.api.pocket.network"
    pocket_rpc_fantom: str = "https://fantom.api.pocket.network"
    pocket_rpc_gnosis: str = "https://gnosis.api.pocket.network"
    pocket_rpc_base: str = "https://base.api.pocket.network"
    pocket_rpc_berachain: str = "https://bera.api.pocket.network"
    pocket_rpc_blast: str = "https://blast.api.pocket.network"
    pocket_rpc_celo: str = "https://celo.api.pocket.network"
    pocket_rpc_linea: str = "https://linea.api.pocket.network"
    pocket_rpc_mantle: str = "https://mantle.api.pocket.network"
    pocket_rpc_scroll: str = "https://scroll.api.pocket.network"
    pocket_rpc_zksync_era: str = "https://zksync-era.api.pocket.network"
    pocket_rpc_sonic: str = "https://sonic.api.pocket.network"
    pocket_rpc_polygon_zkevm: str = "https://poly-zkevm.api.pocket.network"
    encryption_key: str = ""
    jwt_secret: str = ""
    database_path: str = "./pocketagent.db"
    coingecko_api_url: str = "https://api.coingecko.com/api/v3"
    coingecko_api_key: str = ""
    cache_ttl_balance: int = 300
    cache_ttl_gas: int = 30
    cache_ttl_blocks: int = 0
    pocket_api_base: str = "api.pocket.network"
    notional_pokt_per_relay: float = 0.00089

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
