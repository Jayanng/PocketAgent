import unittest
from unittest.mock import AsyncMock, patch

from backend.tools.registry import ToolContext, execute_tool
from backend.tools.transaction_tools import send_transaction


COSMOS_PRIVATE_KEY = "4f3edf983ac636a65a842ce7c78d9aa706d3b113bce9c46f30d7d21715b23b1d"
NEAR_PRIVATE_KEY = "ed25519:3D4YudUqre6Rpf8uDzZtk7aXPtyXJ9F8Kj3YqYqYqYqYq"
NEAR_ACCOUNT_ID = "a" * 64


class _MultichainFakeRPC:
    def __init__(self) -> None:
        self.settings = type("S", (), {"notional_pokt_per_relay": 0.00089})()

    def get_protocol(self, chain: str) -> str:
        return {
            "osmosis": "cosmos",
            "near": "near",
            "sui": "sui",
        }[chain]

    async def get_balance(self, chain: str, address: str) -> dict:
        symbols = {"osmosis": "OSMO", "near": "NEAR", "sui": "SUI"}
        # Enough for 1 native unit on each protocol (NEAR needs 10^24 yocto).
        return {
            "wei": 10**30,
            "raw": 10**30,
            "symbol": symbols.get(chain, "TOKEN"),
        }


def _context(chains: list[str]) -> ToolContext:
    return ToolContext(
        agent={
            "id": "agent-multichain",
            "chains": chains,
            "encrypted_wallets": {
                "cosmos": "encrypted-cosmos",
                "near": "encrypted-near",
                "sui": "encrypted-sui",
            },
            "wallet_addresses": {
                "cosmos": "cosmos1example",
                "near": NEAR_ACCOUNT_ID,
                "sui": "0x9f2eee3323919729963640cb311686093fcee80c2b4c9d80a421c8fffc4fdd56",
            },
            "spending_cap": 10.0,
            "total_spent_by_chain": {},
        },
        rpc_client=_MultichainFakeRPC(),
        relay_tracker=None,
        db=None,
    )


def _decrypt_side_effect(encrypted: str) -> str:
    return {
        "encrypted-cosmos": COSMOS_PRIVATE_KEY,
        "encrypted-near": NEAR_PRIVATE_KEY,
        "encrypted-sui": "AHsDz816o1j59XMM7OhxABaFVI2d7ttDNh1iMt/ItGfF",
    }[encrypted]


class CosmosWriteTransactionTestCase(unittest.IsolatedAsyncioTestCase):
    @patch("backend.tools.transaction_tools.decrypt_private_key", side_effect=_decrypt_side_effect)
    @patch("backend.tools.transaction_tools.update_agent", new=AsyncMock())
    @patch(
        "backend.services.cosmos_transfer.cosmos_address_from_private_key",
        return_value="osmo1sender",
    )
    @patch(
        "backend.services.cosmos_transfer.execute_cosmos_native_transfer",
        return_value={
            "from": "osmo1sender",
            "tx_hash": "cosmos-tx-hash-abc",
            "amount_base": 1_000_000,
            "denom": "uosmo",
            "chain_id": "osmosis-1",
        },
    )
    async def test_send_transaction_signs_and_broadcasts_cosmos(
        self, mock_execute, _mock_address, _mock_decrypt
    ) -> None:
        result = await send_transaction(
            _context(["osmosis"]),
            {
                "chain": "osmosis",
                "to_address": "osmo1recipient",
                "amount": "1",
            },
        )

        self.assertEqual(result["protocol"], "cosmos")
        self.assertEqual(result["tx_hash"], "cosmos-tx-hash-abc")
        self.assertEqual(result["amount_base"], 1_000_000)
        mock_execute.assert_called_once()

    @patch("backend.tools.transaction_tools.decrypt_private_key", side_effect=_decrypt_side_effect)
    async def test_spending_cap_blocks_cosmos_transfer(self, _mock_decrypt) -> None:
        ctx = _context(["osmosis"])
        ctx.agent["spending_cap"] = 0.5
        ctx.agent["total_spent_by_chain"] = {"osmosis": 0.5}

        with self.assertRaises(PermissionError):
            await send_transaction(
                ctx,
                {
                    "chain": "osmosis",
                    "to_address": "osmo1recipient",
                    "amount": "1",
                },
            )

    @patch("backend.tools.transaction_tools.decrypt_private_key", side_effect=_decrypt_side_effect)
    @patch(
        "backend.services.cosmos_transfer.cosmos_address_from_private_key",
        return_value="osmo1sender",
    )
    @patch(
        "backend.services.cosmos_transfer.execute_cosmos_native_transfer",
        side_effect=RuntimeError("Pocket RPC request failed after retries"),
    )
    async def test_unreachable_cosmos_rpc_returns_structured_error(self, _mock_execute, _mock_address, _mock_decrypt) -> None:
        result = await execute_tool(
            "send_transaction",
            _context(["osmosis"]),
            {
                "chain": "osmosis",
                "to_address": "osmo1recipient",
                "amount": "1",
            },
        )

        self.assertFalse(result.get("available"))
        self.assertIn("RuntimeError", result.get("error", ""))


class NearWriteTransactionTestCase(unittest.IsolatedAsyncioTestCase):
    @patch("backend.tools.transaction_tools.decrypt_private_key", side_effect=_decrypt_side_effect)
    @patch("backend.tools.transaction_tools.update_agent", new=AsyncMock())
    @patch(
        "backend.services.near_transfer.execute_near_native_transfer",
        return_value={
            "from": NEAR_ACCOUNT_ID,
            "tx_hash": "near-tx-hash-def",
            "amount_yocto": 1_000_000_000_000_000_000_000_000,
        },
    )
    async def test_send_transaction_signs_and_broadcasts_near(self, mock_execute, _mock_decrypt) -> None:
        result = await send_transaction(
            _context(["near"]),
            {
                "chain": "near",
                "to_address": "bob.near",
                "amount": "1",
            },
        )

        self.assertEqual(result["protocol"], "near")
        self.assertEqual(result["tx_hash"], "near-tx-hash-def")
        mock_execute.assert_called_once()

    @patch("backend.tools.transaction_tools.decrypt_private_key", side_effect=_decrypt_side_effect)
    async def test_spending_cap_blocks_near_transfer(self, _mock_decrypt) -> None:
        ctx = _context(["near"])
        ctx.agent["spending_cap"] = 0.1
        ctx.agent["total_spent_by_chain"] = {"near": 0.1}

        with self.assertRaises(PermissionError):
            await send_transaction(
                ctx,
                {
                    "chain": "near",
                    "to_address": "bob.near",
                    "amount": "1",
                },
            )

    @patch("backend.tools.transaction_tools.decrypt_private_key", side_effect=_decrypt_side_effect)
    @patch(
        "backend.services.near_transfer.execute_near_native_transfer",
        side_effect=RuntimeError("NEAR RPC unreachable"),
    )
    async def test_unreachable_near_rpc_returns_structured_error(self, _mock_execute, _mock_decrypt) -> None:
        result = await execute_tool(
            "send_transaction",
            _context(["near"]),
            {
                "chain": "near",
                "to_address": "bob.near",
                "amount": "1",
            },
        )

        self.assertFalse(result.get("available"))
        self.assertIn("RuntimeError", result.get("error", ""))


class SuiWriteTransactionTestCase(unittest.IsolatedAsyncioTestCase):
    @patch("backend.tools.transaction_tools.decrypt_private_key", side_effect=_decrypt_side_effect)
    @patch("backend.tools.transaction_tools.update_agent", new=AsyncMock())
    @patch(
        "backend.services.sui_transfer.execute_sui_native_transfer",
        return_value={
            "from": "0x9f2eee3323919729963640cb311686093fcee80c2b4c9d80a421c8fffc4fdd56",
            "tx_hash": "sui-digest-abc",
            "amount_mist": 1_000_000_000,
            "rpc_url": "https://fullnode.mainnet.sui.io:443",
        },
    )
    async def test_send_transaction_signs_and_broadcasts_sui(self, mock_execute, _mock_decrypt) -> None:
        result = await send_transaction(
            _context(["sui"]),
            {
                "chain": "sui",
                "to_address": "0x00000000000000000000000000000000000000000000000000000000000000dEaD",
                "amount": "1",
            },
        )

        self.assertEqual(result["protocol"], "sui")
        self.assertEqual(result["tx_hash"], "sui-digest-abc")
        self.assertEqual(result["amount_mist"], 1_000_000_000)
        mock_execute.assert_called_once()

    @patch("backend.tools.transaction_tools.decrypt_private_key", side_effect=_decrypt_side_effect)
    async def test_spending_cap_blocks_sui_transfer(self, _mock_decrypt) -> None:
        ctx = _context(["sui"])
        ctx.agent["spending_cap"] = 0.1
        ctx.agent["total_spent_by_chain"] = {"sui": 0.1}

        with self.assertRaises(PermissionError):
            await send_transaction(
                ctx,
                {
                    "chain": "sui",
                    "to_address": "0x00000000000000000000000000000000000000000000000000000000000000dEaD",
                    "amount": "1",
                },
            )

    @patch("backend.tools.transaction_tools.decrypt_private_key", side_effect=_decrypt_side_effect)
    @patch(
        "backend.services.sui_transfer.execute_sui_native_transfer",
        side_effect=RuntimeError("No SUI coin objects found for this wallet."),
    )
    async def test_unreachable_sui_rpc_returns_structured_error(self, _mock_execute, _mock_decrypt) -> None:
        result = await execute_tool(
            "send_transaction",
            _context(["sui"]),
            {
                "chain": "sui",
                "to_address": "0x00000000000000000000000000000000000000000000000000000000000000dEaD",
                "amount": "1",
            },
        )

        self.assertFalse(result.get("available"))
        self.assertIn("RuntimeError", result.get("error", ""))


if __name__ == "__main__":
    unittest.main()