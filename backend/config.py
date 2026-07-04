from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parent


def resolve_database_path(path: str) -> str:
    if not path or path == ":memory:" or path.startswith("file:"):
        return path
    db_path = Path(path)
    if db_path.is_absolute():
        return str(db_path)
    return str((BACKEND_DIR / db_path).resolve())


def ensure_database_directory(path: str) -> None:
    if not path or path == ":memory:" or path.startswith("file:"):
        return
    Path(path).expanduser().parent.mkdir(parents=True, exist_ok=True)


def parse_csv_setting(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


# Known testnet chain names that PocketAgent should reject.
# These are network names users sometimes type into the chat; the AI should
# not attempt to route them through mainnet RPC endpoints.
TESTNET_CHAIN_NAMES: set[str] = {
    # EVM testnets
    "sepolia", "goerli", "holesky", "hoodi", "mumbai", "amoy",
    "fuji", "avalanche-fuji", "chapel", "bsc-testnet",
    "base-sepolia", "optimism-sepolia", "arbitrum-sepolia",
    "polygon-amoy", "linea-sepolia", "scroll-sepolia",
    "zksync-sepolia", "blast-sepolia", "berachain-artio",
    "berachain-bartio", "taiko-hekla", "unichain-sepolia",
    # Solana
    "solana-devnet", "solana-testnet", "devnet",
    # Sui
    "sui-testnet", "sui-devnet",
    # NEAR
    "near-testnet", "near-betanet",
    # Tron
    "tron-shasta", "shasta", "tron-nile", "nile",
    # Cosmos testnets
    "osmo-testnet", "osmo-test-5", "osmo-test-4",
    "cosmos-testnet", "theta-testnet",
}


class Settings(BaseSettings):
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o"
    # Generation tuning — a lower temperature plus a capped max_tokens yields
    # crisper, faster replies. Override via env (OPENAI_TEMPERATURE /
    # OPENAI_MAX_TOKENS) without touching code.
    openai_temperature: float = 0.3
    openai_max_tokens: int = 1024
    # Number of prior messages replayed as context each turn. A smaller window
    # means a smaller prompt → faster time-to-first-token and lower cost.
    chat_history_limit: int = 20
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
    database_path: str = "./data/pocketagent.db"
    coingecko_api_url: str = "https://api.coingecko.com/api/v3"
    coingecko_api_key: str = ""
    cache_ttl_balance: int = 300
    cache_ttl_gas: int = 30
    cache_ttl_blocks: int = 0
    pocket_api_base: str = "api.pocket.network"
    notional_pokt_per_relay: float = 0.00089
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    disable_agent_auth: bool = False


    @property
    def cors_origin_list(self) -> list[str]:
        return parse_csv_setting(self.cors_origins)

    model_config = SettingsConfigDict(env_file=str(BACKEND_DIR / ".env"), env_file_encoding="utf-8")

    @field_validator("database_path")
    @classmethod
    def normalize_database_path(cls, value: str) -> str:
        return resolve_database_path(value)


@lru_cache
def get_settings() -> Settings:
    return Settings()
