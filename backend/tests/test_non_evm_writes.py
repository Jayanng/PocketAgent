"""Unit tests for non-EVM write tools (token transfers + contract_call dispatch).

Tests cover:
  * Part 1 — the 6 new token-transfer tools (TRC-20, SPL, IBC, CW20, SUI, NEP-141)
  * Part 2 — contract_call protocol dispatch (Solana, Cosmos, SUI, NEAR, Tron)
  * Tool count verification (should increase from 45 to 51)

All tests use mock RPC clients and patched service functions — no live broadcasts.
"""

import unittest
from unittest.mock import AsyncMock, patch

from backend.tools.registry import TOOL_REGISTRY, ToolContext, execute_tool
from backend.tools.token_transfer_tools import (
    send_cw20_token,
    send_ibc_token,
    send_nep141_token,
    send_spl_token,
    send_sui_token,
    send_trc20_token,
)
from backend.tools.transaction_tools import contract_call

# Shared test keys / addresses.
TRON_PRIVATE_KEY = "4f3edf983ac636a65a842ce7c78d9aa706d3b113bce9c46f30d7d21715b23b1d"
SOLANA_PRIVATE_KEY_SEED = TRON_PRIVATE_KEY
COSMOS_PRIVATE_KEY = TRON_PRIVATE_KEY
NEAR_PRIVATE_KEY = "ed25519:3D4YudUqre6Rpf8uDzZtk7aXPtyXJ9F8Kj3YqYqYqYqYq"
NEAR_ACCOUNT_ID = "a" * 64
SUI_KEYSTRING = "AHsDz816o1j59XMM7OhxABaFVI2d7ttDNh1iMt/ItGfF"


class _NonEVMFakeRPC:
    """Mock RPC that dispatches by protocol like PocketRPCClient."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, list]] = []
        self.settings = type("S", (), {"notional_pokt_per_relay": 0.00089})()

    def get_protocol(self, chain: str) -> str:
        return {
            "tron": "tron",
            "solana": "solana",
            "sui": "sui",
            "near": "near",
            "osmosis": "cosmos",
            "pocket": "cosmos",
        }.get(chain, "evm")

    async def get_balance(self, chain: str, address: str) -> dict:
        return {"wei": 10**30, "raw": 10**30, "symbol": "TOK"}

    async def call(self, chain: str, method: str, params: list | None = None) -> object:
        params = params or []
        self.calls.append((chain, method, params))
        if chain == "solana" and method == "getLatestBlockhash":
            return {"value": {"blockhash": "EETubP5AKHgjPAhzPAFcb8BAY1hMH6tbJyDPwWXfPbe9"}}
        if chain == "solana" and method == "sendTransaction":
            return "solana-sig-abc"
        if chain == "solana" and method == "simulateTransaction":
            return {"value": {"err": None, "unitsConsumed": 100, "logs": []}}
        if chain == "tron" and method == "wallet/triggersmartcontract":
            return {"transaction": {"txID": "ab" * 32, "raw_data": {"contract": []}}, "result": True}
        if chain == "tron" and method == "wallet/broadcasttransaction":
            return {"result": True, "txid": "tron-tx-abc"}
        if chain == "tron" and method == "wallet/triggerconstantcontract":
            return {"result": True, "constant_result": ["0" * 64]}
        raise AssertionError(f"unexpected RPC call: {chain}.{method} {params}")


def _context(chains: list[str]) -> ToolContext:
    return ToolContext(
        agent={
            "id": "agent-nonevm",
            "chains": chains,
            "encrypted_wallets": {
                "evm": "encrypted-evm",
                "solana": "encrypted-solana",
                "tron": "encrypted-tron",
                "sui": "encrypted-sui",
                "near": "encrypted-near",
                "cosmos": "encrypted-cosmos",
            },
            "wallet_addresses": {
                "evm": "0x0000000000000000000000000000000000000001",
                "solana": "11111111111111111111111111111112",
                "sui": "0x9f2eee3323919729963640cb311686093fcee80c2b4c9d80a421c8fffc4fdd56",
                "near": NEAR_ACCOUNT_ID,
                "cosmos": "osmo1example",
            },
            "spending_cap": 10.0,
            "total_spent": 0.0,
            "total_spent_by_chain": {},
        },
        rpc_client=_NonEVMFakeRPC(),
        relay_tracker=None,
        db=None,
    )


def _decrypt_side_effect(encrypted: str) -> str:
    return {
        "encrypted-evm": "0x" + TRON_PRIVATE_KEY,
        "encrypted-solana": SOLANA_PRIVATE_KEY_SEED,
        "encrypted-tron": TRON_PRIVATE_KEY,
        "encrypted-sui": SUI_KEYSTRING,
        "encrypted-near": NEAR_PRIVATE_KEY,
        "encrypted-cosmos": COSMOS_PRIVATE_KEY,
    }[encrypted]


class ToolCountTestCase(unittest.TestCase):
    """Verify that the 6 new token-transfer tools are registered (45 → 51)."""

    def test_total_tool_count_is_51(self) -> None:
        self.assertEqual(len(TOOL_REGISTRY), 51)

    def test_new_token_transfer_tools_registered(self) -> None:
        expected = {
            "send_trc20_token",
            "send_spl_token",
            "send_ibc_token",
            "send_cw20_token",
            "send_sui_token",
            "send_nep141_token",
        }
        self.assertEqual(expected, expected & set(TOOL_REGISTRY))


class TronTRC20TransferTestCase(unittest.IsolatedAsyncioTestCase):
    @patch("backend.tools.transaction_tools.decrypt_private_key", side_effect=_decrypt_side_effect)
    @patch("backend.tools.token_transfer_tools._record_native_spend", new=AsyncMock())
    async def test_send_trc20_token_broadcasts(self, _mock_decrypt) -> None:
        result = await send_trc20_token(
            _context(["tron"]),
            {
                "chain": "tron",
                "contract_address": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",
                "to_address": "TPBkHycN1Hmr2bFcfjvp2fjkca1hfPbPka",
                "amount": "1",
                "decimals": 6,
            },
        )
        self.assertEqual(result["protocol"], "tron")
        self.assertEqual(result["status"], "broadcast")
        self.assertEqual(result["tx_hash"], "tron-tx-abc")
        self.assertTrue(result["amount_raw"] > 0)

    @patch("backend.tools.transaction_tools.decrypt_private_key", side_effect=_decrypt_side_effect)
    async def test_spending_cap_blocks_trc20(self, _mock_decrypt) -> None:
        ctx = _context(["tron"])
        ctx.agent["spending_cap"] = 0
        with self.assertRaises(PermissionError):
            await send_trc20_token(
                ctx,
                {
                    "chain": "tron",
                    "contract_address": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",
                    "to_address": "TPBkHycN1Hmr2bFcfjvp2fjkca1hfPbPka",
                    "amount": "1",
                },
            )

    async def test_trc20_on_wrong_protocol_returns_deferred(self) -> None:
        result = await send_trc20_token(
            _context(["solana"]),
            {
                "chain": "solana",
                "contract_address": "TokenMint",
                "to_address": "Recipient",
                "amount": "1",
            },
        )
        self.assertEqual(result["status"], "deferred")


class SolanaSPLTransferTestCase(unittest.IsolatedAsyncioTestCase):
    @patch("backend.tools.transaction_tools.decrypt_private_key", side_effect=_decrypt_side_effect)
    @patch("backend.tools.token_transfer_tools._record_native_spend", new=AsyncMock())
    async def test_send_spl_token_broadcasts(self, _mock_decrypt) -> None:
        result = await send_spl_token(
            _context(["solana"]),
            {
                "chain": "solana",
                "token_mint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                "to_owner_address": "11111111111111111111111111111112",
                "amount": "1",
                "decimals": 6,
            },
        )
        self.assertEqual(result["protocol"], "solana")
        self.assertEqual(result["status"], "broadcast")
        self.assertEqual(result["tx_hash"], "solana-sig-abc")
        self.assertTrue(result["amount_raw"] > 0)

    @patch("backend.tools.transaction_tools.decrypt_private_key", side_effect=_decrypt_side_effect)
    async def test_spending_cap_blocks_spl(self, _mock_decrypt) -> None:
        ctx = _context(["solana"])
        ctx.agent["spending_cap"] = 0
        with self.assertRaises(PermissionError):
            await send_spl_token(
                ctx,
                {
                    "chain": "solana",
                    "token_mint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                    "to_owner_address": "11111111111111111111111111111112",
                    "amount": "1",
                },
            )

    async def test_spl_on_wrong_protocol_returns_deferred(self) -> None:
        result = await send_spl_token(
            _context(["tron"]),
            {
                "chain": "tron",
                "token_mint": "TokenMint",
                "to_owner_address": "Recipient",
                "amount": "1",
            },
        )
        self.assertEqual(result["status"], "deferred")


class CosmosTokenTransferTestCase(unittest.IsolatedAsyncioTestCase):
    @patch("backend.tools.transaction_tools.decrypt_private_key", side_effect=_decrypt_side_effect)
    @patch("backend.tools.token_transfer_tools._record_native_spend", new=AsyncMock())
    @patch(
        "backend.services.cosmos_token_transfer.execute_cosmos_ibc_transfer",
        return_value={
            "from": "osmo1sender",
            "tx_hash": "ibc-tx-abc",
            "amount_base": 1_000_000,
            "denom": "ibc/ABCDEF",
            "chain_id": "osmosis-1",
        },
    )
    async def test_send_ibc_token_broadcasts(self, mock_execute, _mock_decrypt) -> None:
        result = await send_ibc_token(
            _context(["osmosis"]),
            {
                "chain": "osmosis",
                "to_address": "osmo1recipient",
                "amount": "1",
                "denom": "ibc/ABCDEF",
            },
        )
        self.assertEqual(result["protocol"], "cosmos")
        self.assertEqual(result["tx_hash"], "ibc-tx-abc")
        self.assertEqual(result["denom"], "ibc/ABCDEF")
        mock_execute.assert_called_once()

    @patch("backend.tools.transaction_tools.decrypt_private_key", side_effect=_decrypt_side_effect)
    @patch("backend.tools.token_transfer_tools._record_native_spend", new=AsyncMock())
    @patch(
        "backend.services.cosmos_token_transfer.execute_cosmos_cw20_transfer",
        return_value={
            "from": "osmo1sender",
            "tx_hash": "cw20-tx-abc",
            "contract_address": "osmo1contract",
            "msg": {"transfer": {}},
            "chain_id": "osmosis-1",
        },
    )
    async def test_send_cw20_token_broadcasts(self, mock_execute, _mock_decrypt) -> None:
        result = await send_cw20_token(
            _context(["osmosis"]),
            {
                "chain": "osmosis",
                "contract_address": "osmo1contract",
                "to_address": "osmo1recipient",
                "amount": "1000000",
            },
        )
        self.assertEqual(result["protocol"], "cosmos")
        self.assertEqual(result["tx_hash"], "cw20-tx-abc")
        self.assertEqual(result["contract_address"], "osmo1contract")
        mock_execute.assert_called_once()

    @patch("backend.tools.transaction_tools.decrypt_private_key", side_effect=_decrypt_side_effect)
    async def test_spending_cap_blocks_ibc(self, _mock_decrypt) -> None:
        ctx = _context(["osmosis"])
        ctx.agent["spending_cap"] = 0
        with self.assertRaises(PermissionError):
            await send_ibc_token(
                ctx,
                {"chain": "osmosis", "to_address": "osmo1r", "amount": "1", "denom": "ibc/X"},
            )


class SuiCoinTransferTestCase(unittest.IsolatedAsyncioTestCase):
    @patch("backend.tools.transaction_tools.decrypt_private_key", side_effect=_decrypt_side_effect)
    @patch("backend.tools.token_transfer_tools._record_native_spend", new=AsyncMock())
    @patch(
        "backend.services.sui_coin_transfer.execute_sui_coin_transfer",
        return_value={
            "from": "0x9f2eee3323919729963640cb311686093fcee80c2b4c9d80a421c8fffc4fdd56",
            "tx_hash": "sui-coin-tx-abc",
            "amount": 1_000_000_000,
            "coin_type": "0x5::usdc::USDC",
            "rpc_url": "https://sui.api.pocket.network",
        },
    )
    async def test_send_sui_token_broadcasts(self, mock_execute, _mock_decrypt) -> None:
        result = await send_sui_token(
            _context(["sui"]),
            {
                "chain": "sui",
                "coin_type": "0x5::usdc::USDC",
                "to_address": "0x00000000000000000000000000000000000000000000000000000000000000dEaD",
                "amount": "1",
            },
        )
        self.assertEqual(result["protocol"], "sui")
        self.assertEqual(result["tx_hash"], "sui-coin-tx-abc")
        self.assertEqual(result["coin_type"], "0x5::usdc::USDC")
        mock_execute.assert_called_once()

    @patch("backend.tools.transaction_tools.decrypt_private_key", side_effect=_decrypt_side_effect)
    async def test_spending_cap_blocks_sui_coin(self, _mock_decrypt) -> None:
        ctx = _context(["sui"])
        ctx.agent["spending_cap"] = 0
        with self.assertRaises(PermissionError):
            await send_sui_token(
                ctx,
                {"chain": "sui", "coin_type": "0x5::usdc::USDC", "to_address": "0xdead", "amount": "1"},
            )


class NearNEP141TransferTestCase(unittest.IsolatedAsyncioTestCase):
    @patch("backend.tools.transaction_tools.decrypt_private_key", side_effect=_decrypt_side_effect)
    @patch("backend.tools.token_transfer_tools._record_native_spend", new=AsyncMock())
    @patch(
        "backend.services.near_nep141_transfer.execute_near_nep141_transfer",
        return_value={
            "from": NEAR_ACCOUNT_ID,
            "tx_hash": "nep141-tx-abc",
            "contract_id": "usdc.near",
            "amount_raw": 1_000_000,
        },
    )
    async def test_send_nep141_token_broadcasts(self, mock_execute, _mock_decrypt) -> None:
        result = await send_nep141_token(
            _context(["near"]),
            {
                "chain": "near",
                "contract_id": "usdc.near",
                "receiver_id": "bob.near",
                "amount": "1",
                "decimals": 6,
            },
        )
        self.assertEqual(result["protocol"], "near")
        self.assertEqual(result["tx_hash"], "nep141-tx-abc")
        self.assertEqual(result["contract_id"], "usdc.near")
        mock_execute.assert_called_once()

    @patch("backend.tools.transaction_tools.decrypt_private_key", side_effect=_decrypt_side_effect)
    async def test_spending_cap_blocks_nep141(self, _mock_decrypt) -> None:
        ctx = _context(["near"])
        ctx.agent["spending_cap"] = 0
        with self.assertRaises(PermissionError):
            await send_nep141_token(
                ctx,
                {"chain": "near", "contract_id": "usdc.near", "receiver_id": "bob.near", "amount": "1"},
            )


class ContractCallDispatchTestCase(unittest.IsolatedAsyncioTestCase):
    """Part 2: contract_call now dispatches to non-EVM protocols."""

    async def test_solana_read_dispatches_to_simulate(self) -> None:
        ctx = _context(["solana"])
        result = await contract_call(
            ctx,
            {
                "chain": "solana",
                "contract_address": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
                "data": "0x01",
                "accounts": [{"pubkey": "11111111111111111111111111111112", "is_signer": True, "is_writable": True}],
            },
        )
        # Read mode returns the simulateTransaction result.
        self.assertIsInstance(result, dict)
        self.assertNotEqual(result.get("status"), "deferred")
        self.assertTrue(any(c[1] == "simulateTransaction" for c in ctx.rpc_client.calls))

    @patch("backend.tools.transaction_tools.decrypt_private_key", side_effect=_decrypt_side_effect)
    @patch(
        "backend.services.cosmos_token_transfer.cosmos_cw20_query",
        return_value={"balance": "1000000"},
    )
    async def test_cosmos_read_dispatches_to_query(self, mock_query, _mock_decrypt) -> None:
        result = await contract_call(
            _context(["osmosis"]),
            {
                "chain": "osmosis",
                "contract_address": "osmo1contract",
                "data": '{"balance": {}}',
            },
        )
        self.assertEqual(result, {"balance": "1000000"})
        mock_query.assert_called_once()

    @patch("backend.tools.transaction_tools.decrypt_private_key", side_effect=_decrypt_side_effect)
    @patch(
        "backend.services.sui_coin_transfer.execute_sui_move_call",
        return_value={"effects": {"status": {"status": "success"}}},
    )
    async def test_sui_read_dispatches_to_inspect(self, mock_move, _mock_decrypt) -> None:
        result = await contract_call(
            _context(["sui"]),
            {
                "chain": "sui",
                "contract_address": "0x2",
                "module": "coin",
                "function": "value",
                "args": ["0xabc"],
            },
        )
        self.assertNotEqual(result, {"status": "deferred"})
        mock_move.assert_called_once()
        # Verify inspect=True was passed for read mode.
        _, kwargs = mock_move.call_args
        self.assertTrue(kwargs.get("inspect"))

    @patch("backend.tools.transaction_tools.decrypt_private_key", side_effect=_decrypt_side_effect)
    async def test_tron_read_dispatches_to_triggerconstant(self, _mock_decrypt) -> None:
        ctx = _context(["tron"])
        result = await contract_call(
            ctx,
            {
                "chain": "tron",
                "contract_address": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",
                "abi_function": "balanceOf(address)",
                "args": ["TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"],
            },
        )
        # Read mode returns the constant_result from triggerconstantcontract.
        self.assertIsInstance(result, dict)
        self.assertNotEqual(result.get("status"), "deferred")
        self.assertTrue(any(c[1] == "wallet/triggerconstantcontract" for c in ctx.rpc_client.calls))

    @patch("backend.tools.transaction_tools.decrypt_private_key", side_effect=_decrypt_side_effect)
    @patch("backend.tools.transaction_tools._contract_call_near", new=AsyncMock(return_value={"protocol": "near", "status": "broadcast", "tx_hash": "near-cc-abc"}))
    async def test_near_dispatches_to_near_handler(self, _mock_near) -> None:
        result = await contract_call(
            _context(["near"]),
            {
                "chain": "near",
                "contract_address": "usdc.near",
                "abi_function": "ft_balance_of",
                "args": {"account_id": "alice.near"},
            },
        )
        self.assertNotEqual(result.get("status"), "deferred")
        self.assertEqual(result["tx_hash"], "near-cc-abc")

    async def test_evm_read_still_works(self) -> None:
        """EVM contract_call read should still use eth_call."""
        from backend.tests.test_prompt5_write_transaction import _context as _evm_context
        ctx, rpc = _evm_context(["ethereum"])
        result = await contract_call(
            ctx,
            {
                "chain": "ethereum",
                "contract_address": "0x000000000000000000000000000000000000dEaD",
                "abi_function": "balanceOf(address)",
                "args": ["0x000000000000000000000000000000000000dEaD"],
            },
        )
        self.assertEqual(result, "0x")


if __name__ == "__main__":
    unittest.main()
