import unittest

from backend.tools.registry import ToolContext
from backend.tools.simulation_tools import simulate_transaction


class _SimFakeRPC:
    """Fake RPC client for simulate_transaction: dispatches by protocol and
    records which simulation RPC methods were invoked."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, list]] = []

    def get_protocol(self, chain: str) -> str:
        return {"ethereum": "evm", "solana": "solana", "tron": "tron"}[chain]

    async def call(self, chain: str, method: str, params: list | None = None) -> object:
        self.calls.append((chain, method, params or []))
        if chain == "solana" and method == "simulateTransaction":
            return {"value": {"err": None, "unitsConsumed": 5000, "logs": ["Program log: success"]}}
        if chain == "tron" and method == "wallet/triggerconstantcontract":
            return {"result": True, "energy_used": 13645}
        if chain == "ethereum" and method == "eth_estimateGas":
            return "0x5208"
        if chain == "ethereum" and method == "eth_call":
            return "0x"
        raise AssertionError(f"unexpected call: {chain}.{method}")

    async def estimate_gas(self, chain: str, tx: dict) -> dict:
        # Delegate through call() so eth_estimateGas is recorded, mirroring the
        # real PocketRPCClient.estimate_gas implementation.
        gas_hex = await self.call(chain, "eth_estimateGas", [tx])
        gas_units = int(gas_hex, 16) if isinstance(gas_hex, str) else int(gas_hex)
        return {"gas_units": gas_units, "gas_price_gwei": 12.0, "total_cost_usd": "$0.30", "chain": chain}


def _context(chains: list[str]) -> tuple[ToolContext, _SimFakeRPC]:
    rpc = _SimFakeRPC()
    ctx = ToolContext(agent={"id": "agent-1", "chains": chains}, rpc_client=rpc, relay_tracker=None, db=None)
    return ctx, rpc


class SimulateTransactionMultiProtocolTestCase(unittest.IsolatedAsyncioTestCase):
    """Prompt 5 simulate_transaction must support EVM (eth_estimateGas/eth_call),
    Solana (simulateTransaction), and Tron (triggerconstantcontract) — not just EVM."""

    async def test_solana_uses_simulate_transaction(self) -> None:
        ctx, rpc = _context(["solana"])
        result = await simulate_transaction(
            ctx,
            {"chain": "solana", "operation_type": "native_transfer", "to_address": "RecipientBase58"},
        )

        self.assertEqual(result["protocol"], "solana")
        self.assertNotEqual(result.get("success"), None, "Solana must not return a deferred status")
        self.assertTrue(result["success"])
        methods = [c[1] for c in rpc.calls]
        self.assertIn("simulateTransaction", methods)
        self.assertEqual(result["estimate"]["unitsConsumed"], 5000)

    async def test_tron_uses_triggerconstantcontract(self) -> None:
        ctx, rpc = _context(["tron"])
        result = await simulate_transaction(
            ctx,
            {"chain": "tron", "operation_type": "contract_call", "to_address": "TRx...", "contract_address": "TRc..."},
        )

        self.assertEqual(result["protocol"], "tron")
        self.assertNotEqual(result.get("success"), None, "Tron must not return a deferred status")
        self.assertTrue(result["success"])
        methods = [c[1] for c in rpc.calls]
        self.assertIn("wallet/triggerconstantcontract", methods)
        self.assertEqual(result["estimate"]["energy_used"], 13645)

    async def test_evm_still_uses_estimate_gas(self) -> None:
        ctx, rpc = _context(["ethereum"])
        result = await simulate_transaction(
            ctx,
            {"chain": "ethereum", "operation_type": "native_transfer", "to_address": "0xabc"},
        )

        self.assertEqual(result["protocol"], "evm")
        self.assertTrue(result["success"])
        methods = [c[1] for c in rpc.calls]
        self.assertIn("eth_estimateGas", methods)

    async def test_solana_failure_reports_success_false_with_error(self) -> None:
        rpc = _SimFakeRPC()

        async def boom(chain, method, params=None):
            raise RuntimeError("insufficient funds")
        rpc.call = boom  # type: ignore[assignment]

        ctx = ToolContext(agent={"id": "a", "chains": ["solana"]}, rpc_client=rpc, relay_tracker=None, db=None)
        result = await simulate_transaction(
            ctx, {"chain": "solana", "operation_type": "native_transfer", "to_address": "X"},
        )
        self.assertFalse(result["success"])
        self.assertIn("insufficient funds", result["error"])


if __name__ == "__main__":
    unittest.main()
