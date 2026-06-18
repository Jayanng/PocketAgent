from __future__ import annotations

from typing import Any

try:
    from .chain_registry import canonical_chain, get_chain_metadata
    from .price_feed import PriceFeedService
except ImportError:
    from services.chain_registry import canonical_chain, get_chain_metadata
    from services.price_feed import PriceFeedService


class HumanReadableFormatter:
    """Format raw multi-protocol chain values into user-facing data."""

    def __init__(self, price_feed: PriceFeedService | None = None) -> None:
        self.price_feed = price_feed or PriceFeedService()

    @staticmethod
    def _as_int(raw_value: str | int | float) -> int:
        if isinstance(raw_value, str):
            clean = raw_value.strip()
            if clean.startswith("0x"):
                return int(clean, 16)
            return int(clean)
        return int(raw_value)

    @staticmethod
    def _format_usd(usd: float | str | None) -> str:
        if usd is None:
            return "USD unavailable"
        return f"${float(usd):,.2f}"

    async def enrich_amount(
        self,
        raw_value: str | int | float,
        chain: str,
        protocol: str | None = None,
    ) -> dict[str, Any]:
        canonical = canonical_chain(chain)
        metadata = get_chain_metadata(canonical)
        smallest_unit = self._as_int(raw_value)
        decimals = int(metadata["decimals"])
        amount = smallest_unit / (10**decimals)
        symbol = metadata["symbol"]
        usd_value = (await self.price_feed.get_usd_value(amount, symbol))["usd"]
        return {
            "raw": raw_value,
            "wei": smallest_unit,
            "formatted": f"{amount:.6f}",
            "symbol": symbol,
            "usd_value": usd_value,
            "chain": canonical,
            "protocol": protocol or metadata["protocol"],
        }

    async def enrich_balance(self, raw_value: str | int | float, chain: str, protocol: str | None = None) -> dict[str, Any]:
        return await self.enrich_amount(raw_value, chain, protocol)

    async def format_balance(self, raw_value: str | int | float, chain: str, protocol: str | None = None) -> str:
        enriched = await self.enrich_balance(raw_value, chain, protocol)
        return (
            f"{enriched['formatted']} {enriched['symbol']} "
            f"({self._format_usd(enriched['usd_value'])})"
        )

    async def format_gas(self, gas_units: int, gas_price: int | float, chain: str, protocol: str = "evm") -> str:
        metadata = get_chain_metadata(chain)
        symbol = metadata["symbol"]
        if protocol != "evm":
            return f"{gas_units:,} fee units on {metadata['name']}"

        gas_price_wei = self._as_int(gas_price)
        gas_price_gwei = gas_price_wei / 10**9
        total_native = (gas_units * gas_price_wei) / 10**18
        usd = (await self.price_feed.get_usd_value(total_native, symbol))["usd"]
        return (
            f"{gas_units:,} gas x {gas_price_gwei:.2f} GWEI = "
            f"{total_native:.6f} {symbol} ({self._format_usd(usd)})"
        )

    def format_transaction(self, tx_hash: str, chain: str, protocol: str | None = None) -> str:
        metadata = get_chain_metadata(chain)
        explorer = metadata["explorer_url"].rstrip("/")
        short_hash = f"{tx_hash[:10]}...{tx_hash[-6:]}" if len(tx_hash) > 18 else tx_hash
        if not explorer:
            return short_hash
        if protocol in {"solana", "sui", "near", "tron"}:
            return f"{short_hash} -> View on Explorer: {explorer}/tx/{tx_hash}"
        return f"{short_hash} -> View on Explorer: {explorer}/tx/{tx_hash}"

    async def format_cost_breakdown(self, pokt_cost: float, chain: str | None = None) -> str:
        chain_label = f" on {chain}" if chain else ""
        return f"{pokt_cost:.6f} POKT estimated relay cost{chain_label}"
