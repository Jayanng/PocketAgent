import unittest

from backend.services.chain_router import ChainRouter


class FakeCache:
    def get_cache_stats(self) -> dict:
        return {"hits": 1, "misses": 2}


class FakeRPCClient:
    def __init__(self) -> None:
        self.cache = FakeCache()
        self.chain_registry = {"ethereum": {}, "polygon": {}, "arbitrum": {}, "solana": {}}
        self.gas = {
            "ethereum": {"gas_price_gwei": 30, "base_fee_gwei": 28},
            "polygon": {"gas_price_gwei": 35, "base_fee_gwei": 30},
            "arbitrum": {"gas_price_gwei": 0.1, "base_fee_gwei": 0.08},
            "solana": {"estimated_native_fee": 0.000005, "fee_source": "getRecentPrioritizationFees"},
        }
        self.blocks = {"ethereum": 19_000_000, "polygon": 60_000_000, "arbitrum": 180_000_000, "solana": 300_000_000}

    async def get_gas_price(self, chain: str) -> dict:
        return self.gas[chain]

    async def get_block_number(self, chain: str) -> int:
        return self.blocks[chain]


class FakePriceFeed:
    async def get_prices(self, token_ids: list[str]) -> dict[str, float | None]:
        return {
            token_id: {"ethereum": 3000, "matic-network": 0.7, "solana": 150}.get(token_id)
            for token_id in token_ids
        }


class Prompt8ChainRouterTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_chain_comparison_includes_prompt_metrics(self) -> None:
        router = ChainRouter(FakeRPCClient(), FakePriceFeed(), default_chains=["ethereum", "polygon"])

        result = await router.get_chain_comparison(["ethereum", "polygon"])

        self.assertEqual(result["recommended_chain"], "polygon")
        polygon = result["chains"]["polygon"]
        self.assertEqual(polygon["gas_gwei"], 35)
        self.assertEqual(polygon["latest_block"], 60_000_000)
        self.assertEqual(polygon["average_block_time"], "2s")
        self.assertEqual(polygon["finality"], "2s")
        self.assertEqual(polygon["health"], "green")
        self.assertLess(polygon["est_cost_usd"], result["chains"]["ethereum"]["est_cost_usd"])

    async def test_recommend_chain_uses_cost_speed_and_latency_reason(self) -> None:
        router = ChainRouter(FakeRPCClient(), FakePriceFeed(), default_chains=["ethereum", "polygon", "arbitrum"])

        result = await router.recommend_chain("native_transfer")

        self.assertEqual(result["operation_type"], "native_transfer")
        self.assertEqual(result["recommended_chain"], "arbitrum")
        self.assertIn("estimated native transfer cost", result["reason"])
        self.assertIn("arbitrum", result["comparison"])

    async def test_cheapest_and_fastest_helpers(self) -> None:
        router = ChainRouter(FakeRPCClient(), FakePriceFeed(), default_chains=["ethereum", "polygon", "arbitrum"])

        cheapest = await router.get_cheapest_chain()
        fastest = await router.get_fastest_chain()

        self.assertEqual(cheapest["chain"], "polygon")
        self.assertEqual(fastest["chain"], "arbitrum")

    async def test_default_chains_come_from_rpc_registry(self) -> None:
        router = ChainRouter(FakeRPCClient(), FakePriceFeed())

        result = await router.get_chain_comparison()

        self.assertEqual(set(result["chains"]), {"ethereum", "polygon", "arbitrum", "solana"})

    async def test_non_evm_normalized_fee_is_used(self) -> None:
        router = ChainRouter(FakeRPCClient(), FakePriceFeed(), default_chains=["solana"])

        result = await router.get_chain_comparison(["solana"])

        solana = result["chains"]["solana"]
        self.assertEqual(solana["est_cost_native"], 0.000005)
        self.assertEqual(solana["est_cost_usd"], 0.00075)
        self.assertEqual(solana["health"], "green")


if __name__ == "__main__":
    unittest.main()
