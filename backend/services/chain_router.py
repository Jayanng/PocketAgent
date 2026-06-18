from __future__ import annotations

import asyncio
import time
from typing import Any

try:
    from .chain_registry import CHAIN_REGISTRY, canonical_chain, get_chain_metadata
    from .pocket_rpc import PocketRPCClient
    from .price_feed import PriceFeedService
except ImportError:
    from services.chain_registry import CHAIN_REGISTRY, canonical_chain, get_chain_metadata
    from services.pocket_rpc import PocketRPCClient
    from services.price_feed import PriceFeedService


CHAIN_METADATA: dict[str, dict[str, Any]] = {
    "ethereum": {"block_time": 12, "finality": "12min", "symbol": "ETH", "protocol": "evm", "coingecko_id": "ethereum"},
    "polygon": {"block_time": 2, "finality": "2s", "symbol": "POL", "protocol": "evm", "coingecko_id": "matic-network"},
    "arbitrum": {"block_time": 0.25, "finality": "10min", "symbol": "ETH", "protocol": "evm", "coingecko_id": "arbitrum"},
    "optimism": {"block_time": 2, "finality": "5min", "symbol": "ETH", "protocol": "evm", "coingecko_id": "optimism"},
    "bsc": {"block_time": 3, "finality": "15s", "symbol": "BNB", "protocol": "evm", "coingecko_id": "binancecoin"},
    "avalanche": {"block_time": 2, "finality": "1s", "symbol": "AVAX", "protocol": "evm", "coingecko_id": "avalanche-2"},
    "fantom": {"block_time": 1, "finality": "1s", "symbol": "FTM", "protocol": "evm", "coingecko_id": "fantom"},
    "gnosis": {"block_time": 5, "finality": "5min", "symbol": "xDAI", "protocol": "evm", "coingecko_id": "xdai"},
    "base": {"block_time": 2, "finality": "5min", "symbol": "ETH", "protocol": "evm", "coingecko_id": "base"},
    "berachain": {"block_time": 2, "finality": "5min", "symbol": "BERA", "protocol": "evm", "coingecko_id": "berachain"},
    "blast": {"block_time": 2, "finality": "5min", "symbol": "ETH", "protocol": "evm", "coingecko_id": "blast"},
    "celo": {"block_time": 5, "finality": "5min", "symbol": "CELO", "protocol": "evm", "coingecko_id": "celo"},
    "linea": {"block_time": 2, "finality": "5min", "symbol": "ETH", "protocol": "evm", "coingecko_id": "linea"},
    "scroll": {"block_time": 3, "finality": "5min", "symbol": "ETH", "protocol": "evm", "coingecko_id": "scroll"},
    "zksync-era": {"block_time": 1, "finality": "5min", "symbol": "ETH", "protocol": "evm", "coingecko_id": "zksync"},
    "sonic": {"block_time": 1, "finality": "1s", "symbol": "S", "protocol": "evm", "coingecko_id": "sonic-3"},
    "polygon-zkevm": {"block_time": 2, "finality": "5min", "symbol": "POL", "protocol": "evm", "coingecko_id": "polygon-ecosystem"},
    "fraxtal": {"block_time": 2, "finality": "5min", "symbol": "FRAX", "protocol": "evm", "coingecko_id": "frax"},
    "opbnb": {"block_time": 3, "finality": "15s", "symbol": "BNB", "protocol": "evm", "coingecko_id": "binancecoin"},
    "kaia": {"block_time": 1, "finality": "12s", "symbol": "KAIA", "protocol": "evm", "coingecko_id": "kaia"},
    "kava": {"block_time": 6, "finality": "6s", "symbol": "KAVA", "protocol": "evm", "coingecko_id": "kava"},
    "moonbeam": {"block_time": 6, "finality": "12s", "symbol": "GLMR", "protocol": "evm", "coingecko_id": "moonbeam"},
    "moonriver": {"block_time": 12, "finality": "12s", "symbol": "MOVR", "protocol": "evm", "coingecko_id": "moonriver"},
    "metis": {"block_time": 2, "finality": "5min", "symbol": "METIS", "protocol": "evm", "coingecko_id": "metis-token"},
    "boba": {"block_time": 2, "finality": "5min", "symbol": "BOBA", "protocol": "evm", "coingecko_id": "boba-network"},
    "fuse": {"block_time": 5, "finality": "5min", "symbol": "FUSE", "protocol": "evm", "coingecko_id": "fuse-network-token"},
    "harmony": {"block_time": 2, "finality": "2s", "symbol": "ONE", "protocol": "evm", "coingecko_id": "harmony"},
    "iotex": {"block_time": 5, "finality": "5s", "symbol": "IOTX", "protocol": "evm", "coingecko_id": "iotex"},
    "oasys": {"block_time": 1, "finality": "1s", "symbol": "OAS", "protocol": "evm", "coingecko_id": "oasys"},
    "sei": {"block_time": 0.5, "finality": "0.4s", "symbol": "SEI", "protocol": "evm", "coingecko_id": "sei-network"},
    "hyperliquid": {"block_time": 0.5, "finality": "0.4s", "symbol": "HYPE", "protocol": "evm", "coingecko_id": "hyperliquid"},
    "ink": {"block_time": 2, "finality": "5min", "symbol": "INK", "protocol": "evm", "coingecko_id": "ink"},
    "taiko": {"block_time": 2, "finality": "5min", "symbol": "ETH", "protocol": "evm", "coingecko_id": "taiko"},
    "unichain": {"block_time": 2, "finality": "5min", "symbol": "ETH", "protocol": "evm", "coingecko_id": "uniswap"},
    "xrplevm": {"block_time": 4, "finality": "4s", "symbol": "XRP", "protocol": "evm", "coingecko_id": "ripple"},
    "zklink-nova": {"block_time": 2, "finality": "5min", "symbol": "ETH", "protocol": "evm", "coingecko_id": "zklink"},
    "solana": {"block_time": 0.4, "finality": "0.4s", "symbol": "SOL", "protocol": "solana", "coingecko_id": "solana"},
    "sui": {"block_time": 0.5, "finality": "0.4s", "symbol": "SUI", "protocol": "sui", "coingecko_id": "sui"},
    "near": {"block_time": 1, "finality": "1s", "symbol": "NEAR", "protocol": "near", "coingecko_id": "near"},
    "tron": {"block_time": 3, "finality": "3s", "symbol": "TRX", "protocol": "tron", "coingecko_id": "tron"},
    "osmosis": {"block_time": 6, "finality": "6s", "symbol": "OSMO", "protocol": "cosmos", "coingecko_id": "osmosis"},
    "pocket": {"block_time": 6, "finality": "6s", "symbol": "POKT", "protocol": "cosmos", "coingecko_id": "pocket-network"},
    "akash": {"block_time": 6, "finality": "6s", "symbol": "AKT", "protocol": "cosmos", "coingecko_id": "akash-network"},
    "juno": {"block_time": 6, "finality": "6s", "symbol": "JUNO", "protocol": "cosmos", "coingecko_id": "juno-network"},
    "seda": {"block_time": 6, "finality": "6s", "symbol": "SEDA", "protocol": "cosmos", "coingecko_id": "seda-2"},
    "persistence": {"block_time": 6, "finality": "6s", "symbol": "XPRT", "protocol": "cosmos", "coingecko_id": "persistence"},
    "fetch": {"block_time": 6, "finality": "6s", "symbol": "FET", "protocol": "cosmos", "coingecko_id": "fetch-ai"},
    "jackal": {"block_time": 6, "finality": "6s", "symbol": "JKL", "protocol": "cosmos", "coingecko_id": "jackal-protocol"},
    "cheqd": {"block_time": 6, "finality": "6s", "symbol": "CHEQ", "protocol": "cosmos", "coingecko_id": "cheqd-network"},
    "chihuahua": {"block_time": 6, "finality": "6s", "symbol": "HUAHUA", "protocol": "cosmos", "coingecko_id": "chihuahua-token"},
    "shentu": {"block_time": 6, "finality": "6s", "symbol": "CTK", "protocol": "cosmos", "coingecko_id": "certik"},
    "atomone": {"block_time": 6, "finality": "6s", "symbol": "ATONE", "protocol": "cosmos", "coingecko_id": "atomone"},
}

OPERATION_GAS_UNITS = {
    "native_transfer": 21_000,
    "erc20_transfer": 65_000,
    "contract_call": 120_000,
    "simulate": 21_000,
}

NON_EVM_FEE_ESTIMATES = {
    "solana": 0.000005,
    "sui": 0.001,
    "near": 0.0001,
    "tron": 1.0,
    "cosmos": 0.005,
}

SYMBOL_PRICE_FALLBACKS = {
    "ETH": "ethereum",
    "POL": "matic-network",
    "BNB": "binancecoin",
    "AVAX": "avalanche-2",
    "SOL": "solana",
    "TRX": "tron",
}


class ChainRouter:
    """Routes blockchain operations to the optimal chain via Pocket Network."""

    def __init__(
        self,
        rpc_client: Any | None = None,
        price_feed: PriceFeedService | None = None,
        default_chains: list[str] | None = None,
        concurrency: int = 8,
    ) -> None:
        self.rpc_client = rpc_client or PocketRPCClient()
        self.price_feed = price_feed or getattr(self.rpc_client, "price_feed", PriceFeedService())
        registry = getattr(self.rpc_client, "chain_registry", CHAIN_REGISTRY)
        self.default_chains = [canonical_chain(chain) for chain in (default_chains or list(registry))]
        self._semaphore = asyncio.Semaphore(concurrency)

    async def recommend_chain(self, operation_type: str) -> dict[str, Any]:
        """Recommend the best chain for a given operation."""
        comparison = await self.get_chain_comparison()
        healthy = [item for item in comparison["chains"].values() if item.get("health") == "green"]

        if not healthy:
            return {
                "operation_type": operation_type,
                "recommended_chain": None,
                "reason": "No healthy chains were available for comparison.",
                "comparison": comparison["chains"],
            }

        ranked = sorted(healthy, key=lambda item: self._score(item, operation_type))
        winner = ranked[0]
        cost = winner.get("est_cost_usd")
        cost_label = self._usd_label(cost) if cost is not None else "USD unavailable"
        reason = (
            f"Lowest blended route score: estimated {operation_type.replace('_', ' ')} cost "
            f"{cost_label}, finality {winner['finality']}, and {winner['rpc_latency_ms']}ms Pocket RPC latency."
        )

        return {
            "operation_type": operation_type,
            "recommended_chain": winner["chain"],
            "reason": reason,
            "comparison": comparison["chains"],
        }

    async def get_chain_comparison(self, chains: list[str] | None = None) -> dict[str, Any]:
        """Compare all chains or specific chains on key routing metrics."""
        selected = self._normalize_chains(chains)
        prices = await self._load_prices(selected)
        snapshots = await asyncio.gather(
            *[self._snapshot_chain(chain, prices.get(chain)) for chain in selected],
            return_exceptions=True,
        )

        comparison: dict[str, dict[str, Any]] = {}
        for chain, snapshot in zip(selected, snapshots, strict=False):
            if isinstance(snapshot, Exception):
                comparison[chain] = {
                    "chain": chain,
                    "health": "red",
                    "error": str(snapshot),
                    **self._static_metadata(chain),
                }
            else:
                comparison[chain] = snapshot

        healthy = [item for item in comparison.values() if item.get("health") == "green"]
        recommended = min(healthy, key=lambda item: self._score(item, "native_transfer"))["chain"] if healthy else None
        return {
            "chains": comparison,
            "recommended_chain": recommended,
            "cache_stats": self.rpc_client.cache.get_cache_stats() if hasattr(self.rpc_client, "cache") else None,
        }

    async def get_cheapest_chain(self) -> dict[str, Any]:
        """Find the chain with the lowest transaction cost right now."""
        comparison = await self.get_chain_comparison()
        candidates = [
            item
            for item in comparison["chains"].values()
            if item.get("health") == "green" and item.get("est_cost_usd") is not None
        ]
        if not candidates:
            return {"chain": None, "reason": "No healthy chains with USD pricing were available.", "comparison": comparison["chains"]}
        cheapest = min(candidates, key=lambda item: float(item["est_cost_usd"]))
        return {"chain": cheapest["chain"], "estimated_cost_usd": cheapest["est_cost_usd"], "comparison": comparison["chains"]}

    async def get_fastest_chain(self) -> dict[str, Any]:
        """Find the chain with the fastest finality."""
        comparison = await self.get_chain_comparison()
        candidates = [item for item in comparison["chains"].values() if item.get("health") == "green"]
        if not candidates:
            return {"chain": None, "reason": "No healthy chains were available.", "comparison": comparison["chains"]}
        fastest = min(candidates, key=lambda item: float(item["block_time_seconds"]))
        return {
            "chain": fastest["chain"],
            "block_time_seconds": fastest["block_time_seconds"],
            "finality": fastest["finality"],
            "comparison": comparison["chains"],
        }

    def _normalize_chains(self, chains: list[str] | None) -> list[str]:
        selected = chains or self.default_chains
        normalized: list[str] = []
        for chain in selected:
            canonical = canonical_chain(chain)
            get_chain_metadata(canonical)
            if canonical not in normalized:
                normalized.append(canonical)
        return normalized

    async def _load_prices(self, chains: list[str]) -> dict[str, float | None]:
        ids_by_chain: dict[str, str] = {}
        fallback_by_chain: dict[str, str] = {}
        for chain in chains:
            metadata = self._static_metadata(chain)
            token_id = SYMBOL_PRICE_FALLBACKS.get(str(metadata.get("symbol"))) or metadata.get("coingecko_id")
            if token_id:
                ids_by_chain[chain] = str(token_id)
            fallback_id = SYMBOL_PRICE_FALLBACKS.get(str(metadata.get("symbol")))
            if fallback_id:
                fallback_by_chain[chain] = fallback_id

        token_ids = sorted(set(ids_by_chain.values()) | set(fallback_by_chain.values()))
        prices = await self.price_feed.get_prices(token_ids)
        resolved: dict[str, float | None] = {}
        for chain, token_id in ids_by_chain.items():
            resolved[chain] = prices.get(token_id.lower())
            if resolved[chain] is None and chain in fallback_by_chain:
                resolved[chain] = prices.get(fallback_by_chain[chain].lower())
        return resolved

    async def _snapshot_chain(self, chain: str, usd_price: float | None) -> dict[str, Any]:
        async with self._semaphore:
            start = time.perf_counter()
            static = self._static_metadata(chain)
            gas_data: dict[str, Any] = {}
            block_number: int | None = None
            error: str | None = None

            try:
                gas_data = await self.rpc_client.get_gas_price(chain)
            except Exception as exc:
                error = str(exc)

            try:
                block_number = await self.rpc_client.get_block_number(chain)
            except Exception as exc:
                if error is None:
                    error = str(exc)

            latency_ms = int((time.perf_counter() - start) * 1000)
            congestion = self._congestion(gas_data, latency_ms)
            health = self._health(error, latency_ms, congestion)
            gas_gwei = gas_data.get("gas_price_gwei")
            est_cost_native = self._estimate_native_cost(static["protocol"], gas_gwei, "native_transfer", gas_data)
            est_cost_usd = round(est_cost_native * usd_price, 6) if usd_price is not None and est_cost_native is not None else None

            return {
                "chain": chain,
                "name": get_chain_metadata(chain)["name"],
                "protocol": static["protocol"],
                "symbol": static["symbol"],
                "gas_gwei": gas_gwei,
                "est_cost_native": round(est_cost_native, 10) if est_cost_native is not None else None,
                "est_cost_usd": est_cost_usd,
                "usd_price": usd_price,
                "latest_block": block_number,
                "block_time_seconds": static["block_time"],
                "average_block_time": f"{static['block_time']}s",
                "finality": static["finality"],
                "rpc_latency_ms": latency_ms,
                "network_congestion": congestion,
                "health": health,
                "error": error,
            }

    def _static_metadata(self, chain: str) -> dict[str, Any]:
        canonical = canonical_chain(chain)
        registry = get_chain_metadata(canonical)
        hints = CHAIN_METADATA.get(canonical, {})
        static = {
            "symbol": hints.get("symbol", registry["symbol"]),
            "protocol": hints.get("protocol", registry["protocol"]),
            "coingecko_id": hints.get("coingecko_id", registry["coingecko_id"]),
        }
        static.update({key: hints[key] for key in ("block_time", "finality") if key in hints})
        static.setdefault("block_time", 6)
        static.setdefault("finality", f"{static['block_time']}s")
        return static

    @staticmethod
    def _estimate_native_cost(
        protocol: str,
        gas_gwei: Any,
        operation_type: str,
        gas_data: dict[str, Any] | None = None,
    ) -> float | None:
        gas_data = gas_data or {}
        normalized_fee = gas_data.get("estimated_native_fee")
        if normalized_fee is not None:
            return float(normalized_fee)
        if protocol == "evm" and gas_gwei is not None:
            gas_units = OPERATION_GAS_UNITS.get(operation_type, OPERATION_GAS_UNITS["native_transfer"])
            return float(gas_gwei) * gas_units / 1_000_000_000
        return NON_EVM_FEE_ESTIMATES.get(protocol)

    @staticmethod
    def _congestion(gas_data: dict[str, Any], latency_ms: int) -> str:
        gas_gwei = gas_data.get("gas_price_gwei")
        if latency_ms > 5000:
            return "high"
        if gas_gwei is None:
            return "medium" if latency_ms > 1500 else "low"
        if float(gas_gwei) > 80:
            return "high"
        if float(gas_gwei) > 20:
            return "medium"
        return "low"

    @staticmethod
    def _health(error: str | None, latency_ms: int, congestion: str) -> str:
        if error and latency_ms > 5000:
            return "red"
        if error or latency_ms > 2500 or congestion == "high":
            return "yellow"
        return "green"

    @staticmethod
    def _score(item: dict[str, Any], operation_type: str) -> float:
        cost = float(item["est_cost_usd"]) if item.get("est_cost_usd") is not None else 999_999.0
        block_time = float(item.get("block_time_seconds") or 999)
        latency = float(item.get("rpc_latency_ms") or 9999) / 1000
        congestion_penalty = {"low": 0.0, "medium": 2.0, "high": 8.0}.get(str(item.get("network_congestion")), 4.0)
        weights = {
            "native_transfer": (0.70, 0.20, 0.10),
            "erc20_transfer": (0.75, 0.15, 0.10),
            "contract_call": (0.65, 0.20, 0.15),
            "simulate": (0.25, 0.50, 0.25),
        }.get(operation_type, (0.70, 0.20, 0.10))
        return cost * weights[0] + block_time * weights[1] + latency * weights[2] + congestion_penalty

    @staticmethod
    def _usd_label(value: Any) -> str:
        return f"${float(value):,.6f}".rstrip("0").rstrip(".")
