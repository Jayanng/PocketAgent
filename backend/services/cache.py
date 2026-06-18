import hashlib
import json
from typing import Any

from cachetools import TTLCache

try:
    from ..config import get_settings
except ImportError:
    from config import get_settings


class ResponseCache:
    """Two-tier cache for Pocket RPC responses with relay-savings stats."""

    def __init__(
        self,
        ttl_balance: int = 300,
        ttl_gas: int = 30,
        ttl_health: int = 60,
        pokt_per_relay: float | None = None,
    ):
        settings = get_settings()
        self.immutable_cache: dict[str, Any] = {}
        self.balance_cache = TTLCache(maxsize=20_000, ttl=ttl_balance)
        self.gas_cache = TTLCache(maxsize=5_000, ttl=ttl_gas)
        self.health_cache = TTLCache(maxsize=5_000, ttl=ttl_health)
        self.pokt_per_relay = pokt_per_relay if pokt_per_relay is not None else settings.notional_pokt_per_relay
        self.hits = 0
        self.misses = 0

    @staticmethod
    def cache_key(chain: str, method: str, params: list[Any] | None) -> str:
        payload = {"chain": chain, "method": method, "params": params or []}
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

    def _is_immutable(self, method: str, params: list[Any] | None) -> bool:
        if method in {
            "eth_chainId",
            "eth_getTransactionByHash",
            "eth_getTransactionReceipt",
            "getTransaction",
            "getBlock",
            "sui_getTransactionBlock",
            "tx",
            "wallet/gettransactioninfobyid",
        }:
            return True
        if method == "eth_getBlockByNumber" and params:
            block_ref = str(params[0]).lower()
            return block_ref not in {"latest", "pending", "safe", "finalized"}
        return method in {"eth_blockNumber", "getGenesisHash", "sui_getChainIdentifier", "status", "wallet/getchainparameters"}

    @staticmethod
    def _is_balance(method: str) -> bool:
        return method in {"eth_getBalance", "getBalance", "suix_getBalance", "query_balance", "wallet/getaccount"}

    @staticmethod
    def _is_gas(method: str) -> bool:
        return method in {"eth_gasPrice", "eth_feeHistory", "suix_getReferenceGasPrice", "gas_price"}

    def get(self, chain: str, method: str, params: list[Any] | None) -> Any | None:
        key = self.cache_key(chain, method, params)
        if self._is_immutable(method, params):
            if key in self.immutable_cache:
                self.hits += 1
                return self.immutable_cache[key]
            self.misses += 1
            return None
        target = self.health_cache
        if self._is_balance(method):
            target = self.balance_cache
        elif self._is_gas(method):
            target = self.gas_cache
        value = target.get(key)
        if value is None:
            self.misses += 1
            return None
        self.hits += 1
        return value

    def set(self, chain: str, method: str, params: list[Any] | None, value: Any) -> None:
        key = self.cache_key(chain, method, params)
        if self._is_immutable(method, params):
            self.immutable_cache[key] = value
            return
        if self._is_balance(method):
            self.balance_cache[key] = value
            return
        if self._is_gas(method):
            self.gas_cache[key] = value
            return
        self.health_cache[key] = value

    def get_cache_stats(self) -> dict[str, float | int]:
        relays_saved = self.hits
        return {
            "hits": self.hits,
            "misses": self.misses,
            "relays_saved": relays_saved,
            "pokt_saved": round(relays_saved * self.pokt_per_relay, 6),
        }
