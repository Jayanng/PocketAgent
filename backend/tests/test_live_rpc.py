import os
import unittest

from backend.services.chain_router import ChainRouter
from backend.services.pocket_rpc import PocketRPCClient


LIVE_RPC_ENABLED = os.getenv("LIVE_RPC_TESTS") == "1"


@unittest.skipUnless(LIVE_RPC_ENABLED, "Set LIVE_RPC_TESTS=1 to hit live Pocket RPC endpoints.")
class LiveRPCTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_live_pocket_rpc_chain_comparison_subset(self) -> None:
        router = ChainRouter(PocketRPCClient(), default_chains=["ethereum", "polygon", "solana"], concurrency=3)

        result = await router.get_chain_comparison(["ethereum", "polygon", "solana"])

        self.assertEqual(set(result["chains"]), {"ethereum", "polygon", "solana"})
        live_blocks = [
            chain
            for chain, snapshot in result["chains"].items()
            if snapshot.get("latest_block") and snapshot.get("health") in {"green", "yellow"}
        ]
        self.assertGreaterEqual(len(live_blocks), 1, result)

        for chain, snapshot in result["chains"].items():
            self.assertEqual(snapshot["chain"], chain)
            self.assertIn(snapshot["protocol"], {"evm", "solana"})
            self.assertIn(snapshot["health"], {"green", "yellow", "red"})
            self.assertIsInstance(snapshot["rpc_latency_ms"], int)
            self.assertGreaterEqual(snapshot["rpc_latency_ms"], 0)

    async def test_live_recommend_chain_returns_supported_chain(self) -> None:
        router = ChainRouter(PocketRPCClient(), default_chains=["ethereum", "polygon", "arbitrum"], concurrency=3)

        result = await router.recommend_chain("native_transfer")

        self.assertIn(result["recommended_chain"], {"ethereum", "polygon", "arbitrum", None})
        self.assertIn("comparison", result)
        self.assertEqual(set(result["comparison"]), {"ethereum", "polygon", "arbitrum"})


if __name__ == "__main__":
    unittest.main()
