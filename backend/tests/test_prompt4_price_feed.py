import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch


class PriceFeedCoingeckoIdTestCase(unittest.IsolatedAsyncioTestCase):
    """Prompt 4 price feed must resolve native gas-token symbols via CHAIN_REGISTRY
    coingecko_id instead of a legacy symbol map that drops chains like Sonic/Harmony/Boba."""

    def _make_service(self):
        from backend.services.price_feed import PriceFeedService

        fake_settings = SimpleNamespace(
            coingecko_api_url="https://api.coingecko.com/api/v3",
            coingecko_api_key="",
        )
        with patch("backend.services.price_feed.get_settings", return_value=fake_settings):
            return PriceFeedService()

    async def _resolve(self, token: str) -> str:
        service = self._make_service()
        service.get_price = AsyncMock(return_value=1.0)
        await service.get_usd_value(1.0, token)
        return service.get_price.await_args.args[0]

    async def test_sonic_symbol_resolves_to_registry_coingecko_id(self) -> None:
        self.assertEqual(await self._resolve("S"), "sonic-3")

    async def test_harmony_symbol_resolves_to_registry_coingecko_id(self) -> None:
        self.assertEqual(await self._resolve("ONE"), "harmony")

    async def test_boba_symbol_resolves_to_registry_coingecko_id(self) -> None:
        self.assertEqual(await self._resolve("BOBA"), "boba-network")

    async def test_eth_symbol_still_resolves(self) -> None:
        self.assertEqual(await self._resolve("ETH"), "ethereum")

    async def test_unknown_token_falls_back_to_lowered_symbol(self) -> None:
        self.assertEqual(await self._resolve("USDC"), "usdc")

    async def test_usd_value_uses_resolved_price(self) -> None:
        service = self._make_service()
        service.get_price = AsyncMock(return_value=0.5)
        result = await service.get_usd_value(10.0, "S")
        self.assertEqual(result["usd"], 5.0)


if __name__ == "__main__":
    unittest.main()
