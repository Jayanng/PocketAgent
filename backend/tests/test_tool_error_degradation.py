import unittest
from types import SimpleNamespace

from backend.tools.registry import (
    TOOL_REGISTRY,
    ToolContext,
    execute_tool,
    function_schema,
    register_tool,
)


class _BoomRPC:
    """Offline stand-in for PocketRPCClient whose read methods always raise
    RuntimeError, simulating an upstream Pocket RPC endpoint that returns
    500/408 after all retries (e.g. boba/harmony/persistence today)."""

    def __init__(self) -> None:
        self.settings = SimpleNamespace(notional_pokt_per_relay=0.00089)

    def get_protocol(self, chain: str) -> str:
        return "evm"

    async def get_balance(self, chain: str, address: str) -> dict:
        raise RuntimeError("Pocket RPC request failed after retries (status=500)")


class _MixedRPC:
    """multi_chain_balance never raises (it gathers with return_exceptions), so a
    degraded chain surfaces as a per-chain ``{"error": ...}`` entry."""

    def __init__(self) -> None:
        self.settings = SimpleNamespace(notional_pokt_per_relay=0.00089)

    async def multi_chain_balance(self, address: str, chains: list[str]) -> dict:
        return {
            "address": address,
            "balances": {
                "ethereum": {"error": "RuntimeError: Pocket RPC request failed after retries"},
                "polygon": {"formatted": "1.5 POL", "symbol": "POL", "amount_decimal": 1.5},
            },
        }


async def _permission_denied_executor(context: ToolContext, args: dict) -> dict:
    raise PermissionError("spending cap exceeded for this agent")


class ExecuteToolErrorDegradationTestCase(unittest.IsolatedAsyncioTestCase):
    """execute_tool must convert operational RPC failures (RuntimeError) into a
    structured unavailable result so a single degraded chain never aborts the
    whole agent turn, while still letting control-flow signals (PermissionError
    from the spending-cap guard) propagate."""

    def _context(self, chains: list[str] | None = None) -> ToolContext:
        return ToolContext(
            agent={"id": "agent-1", "chains": chains or ["ethereum"]},
            rpc_client=_BoomRPC(),
            relay_tracker=None,
            db=None,
        )

    async def test_runtime_error_returns_unavailable_result(self) -> None:
        ctx = self._context(["ethereum"])
        result = await execute_tool(
            "evm_get_balance", ctx, {"chain": "ethereum", "address": "0xabc"}
        )

        self.assertIsInstance(result, dict)
        self.assertFalse(result.get("available"))
        self.assertIn("RuntimeError", result.get("error", ""))
        self.assertEqual(result.get("tool"), "evm_get_balance")
        self.assertEqual(result.get("chain"), "ethereum")

    async def test_permission_error_still_propagates(self) -> None:
        register_tool(
            function_schema("_tmp_perm", "tmp", {"x": {"type": "string"}}, ["x"]),
            "transact",
            _permission_denied_executor,
        )
        try:
            with self.assertRaises(PermissionError):
                await execute_tool("_tmp_perm", self._context(), {"x": "y"})
        finally:
            TOOL_REGISTRY.pop("_tmp_perm", None)

    async def test_compare_balances_degrades_per_chain_without_raising(self) -> None:
        ctx = ToolContext(
            agent={"id": "agent-1", "chains": ["ethereum", "polygon"]},
            rpc_client=_MixedRPC(),
            relay_tracker=None,
            db=None,
        )
        result = await execute_tool(
            "compare_balances", ctx, {"address": "0xabc", "chains": ["ethereum", "polygon"]}
        )

        self.assertIsInstance(result, dict)
        self.assertIn("balances", result)
        self.assertIn("error", result["balances"]["ethereum"])
        self.assertIn("formatted", result["balances"]["polygon"])


if __name__ == "__main__":
    unittest.main()
