from typing import Any

import httpx
from cachetools import TTLCache

try:
    from ..config import get_settings
    from .chain_registry import CHAIN_REGISTRY
except ImportError:
    from config import get_settings
    from services.chain_registry import CHAIN_REGISTRY


# Symbol -> CoinGecko id, built from CHAIN_REGISTRY so every supported chain's
# native gas token resolves correctly (Sonic, Harmony, Boba, Ink, Fraxtal, ...).
# First-write-wins: the registry is ordered so the canonical L1 (ethereum, polygon,
# bsc) wins for symbols shared across L2s (ETH on Arbitrum/Base/Linea/..., POL on
# polygon-zkevm, BNB on opbnb).
SYMBOL_TO_COINGECKO_ID: dict[str, str] = {}
for _metadata in CHAIN_REGISTRY.values():
    _coingecko_id = _metadata.get("coingecko_id")
    if not _coingecko_id:
        continue
    _symbol = _metadata["symbol"].upper()
    SYMBOL_TO_COINGECKO_ID.setdefault(_symbol, _coingecko_id)

SYMBOL_ALIASES = {
    "MATIC": "matic-network",  # Polygon legacy symbol, registry now uses POL
    "XDAI": "xdai",  # Gnosis registry already maps xDAI; keep canonical casing
    "BERA": "berachain-bera",  # registry uses berachain; CoinGecko uses berachain-bera
}


def _coingecko_id_for_symbol(token: str) -> str:
    symbol = token.upper()
    alias = SYMBOL_ALIASES.get(symbol)
    if alias:
        return alias
    registry_id = SYMBOL_TO_COINGECKO_ID.get(symbol)
    if registry_id:
        return registry_id
    return token.lower()


class PriceFeedService:
    """CoinGecko client with 60-second TTL cache."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._cache = TTLCache(maxsize=5_000, ttl=60)
        self._timeout = 15.0

    async def get_price(self, token_id: str) -> float | None:
        cached = self._cache.get(token_id)
        if cached is not None:
            return float(cached)
        prices = await self.get_prices([token_id])
        return prices.get(token_id)

    async def get_prices(self, token_ids: list[str]) -> dict[str, float | None]:
        normalized = sorted({token_id.strip().lower() for token_id in token_ids if token_id})
        if not normalized:
            return {}

        missing = [token_id for token_id in normalized if token_id not in self._cache]
        failed = False
        if missing:
            params = {"ids": ",".join(missing), "vs_currencies": "usd"}
            headers = {}
            api_key = getattr(self.settings, "coingecko_api_key", "")
            if api_key:
                headers["x-cg-demo-api-key"] = api_key
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    response = await client.get(
                        f"{self.settings.coingecko_api_url}/simple/price",
                        params=params,
                        headers=headers,
                    )
                    response.raise_for_status()
                    data: dict[str, dict[str, Any]] = response.json()
            except (httpx.HTTPError, ValueError):
                data = {}
                failed = True
            for token_id in missing:
                price = data.get(token_id, {}).get("usd")
                self._cache[token_id] = None if failed or price is None else float(price)

        return {token_id: self._cache.get(token_id) for token_id in normalized}

    async def get_usd_value(self, amount: float, token: str) -> dict[str, float | str | None]:
        token_symbol = token.upper()
        token_id = _coingecko_id_for_symbol(token)
        price = await self.get_price(token_id)
        if price is None:
            return {"amount": float(amount), "token": token_symbol, "usd": None}
        usd_value = float(amount) * price
        return {"amount": float(amount), "token": token_symbol, "usd": round(usd_value, 2)}
