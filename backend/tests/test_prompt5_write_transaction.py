import base64
import unittest
from unittest.mock import AsyncMock, patch

from backend.tools.registry import ToolContext
from backend.tools.transaction_tools import contract_call, send_erc20, send_transaction

# Deterministic test keys.
SOLANA_SEED_HEX = "4f3edf983ac636a65a842ce7c78d9aa706d3b113bce9c46f30d7d21715b23b1d"
TRON_PRIV_HEX = "4f3edf983ac636a65a842ce7c78d9aa706d3b113bce9c46f30d7d21715b23b1d"
# Corresponding Solana pubkey derived in the probe:
SOLANA_PUBKEY = "HaWmh8svNQ2CSLc1TQdkhwP6ZthzwkNT5ai5yoVMvyWJ"


class _WriteFakeRPC:
    """Fake RPC client that records Solana sendTransaction and Tron
    wallet/broadcasthex calls, plus supports the read calls needed to build
    transactions (blockhash, account)."""

    def __init__(self) -> None:
        self.broadcasts: list[tuple[str, str, list]] = []
        self.settings = type("S", (), {"notional_pokt_per_relay": 0.00089})()

    def get_protocol(self, chain: str) -> str:
        return {"solana": "solana", "tron": "tron", "ethereum": "evm"}[chain]

    def get_metadata(self, chain: str) -> dict:
        return {
            "solana": {"protocol": "solana", "symbol": "SOL", "decimals": 9, "chain_id": "mainnet-beta"},
            "tron": {"protocol": "tron", "symbol": "TRX", "decimals": 6, "chain_id": "mainnet"},
            "ethereum": {"protocol": "evm", "symbol": "ETH", "decimals": 18, "chain_id": 1},
        }[chain]

    async def call(self, chain: str, method: str, params: list | None = None) -> object:
        params = params or []
        if chain == "solana" and method == "getLatestBlockhash":
            return {"value": {"blockhash": "EETubP5AKHgjPAhzPAFcb8BAY1hMH6tbJyDPwWXfPbe9", "lastValidBlockHeight": 300000000}}
        if chain == "tron" and method == "wallet/broadcasttransaction":
            self.broadcasts.append((chain, method, params))
            return {"result": True, "txid": "tron-tx-hash-123"}
        raise AssertionError(f"unexpected read call: {chain}.{method} {params}")

    async def send_raw_transaction(self, chain: str, raw_tx: str) -> str:
        # Solana path: raw_tx is base64 of the serialized versioned transaction.
        self.broadcasts.append((chain, "send_raw_transaction", [raw_tx]))
        return "solana-signature-456"

    async def get_chain_id(self, chain: str) -> int | str:
        return self.get_metadata(chain)["chain_id"]

    async def get_transaction_count(self, chain: str, address: str) -> int:
        return 0


def _solana_context() -> tuple[ToolContext, _WriteFakeRPC]:
    rpc = _WriteFakeRPC()
    agent = {
        "id": "agent-sol",
        "chains": ["solana"],
        "encrypted_private_key": "encrypted-blob-solana",
        "spending_cap": 1.0,
        "total_spent": 0.0,
    }
    ctx = ToolContext(agent=agent, rpc_client=rpc, relay_tracker=None, db=None)
    return ctx, rpc


def _tron_context() -> tuple[ToolContext, _WriteFakeRPC]:
    rpc = _WriteFakeRPC()
    agent = {
        "id": "agent-tron",
        "chains": ["tron"],
        "encrypted_private_key": "encrypted-blob-tron",
        "spending_cap": 1000.0,
        "total_spent": 0.0,
    }
    ctx = ToolContext(agent=agent, rpc_client=rpc, relay_tracker=None, db=None)
    return ctx, rpc


def _decrypt_side_effect(encrypted: str) -> str:
    if encrypted == "encrypted-blob-solana":
        return SOLANA_SEED_HEX
    if encrypted == "encrypted-blob-tron":
        return TRON_PRIV_HEX
    raise ValueError(f"unexpected encrypted blob: {encrypted}")


class SolanaWriteTransactionTestCase(unittest.IsolatedAsyncioTestCase):
    @patch("backend.tools.transaction_tools.decrypt_private_key")
    @patch("backend.tools.transaction_tools.update_agent", new=AsyncMock())
    async def test_send_transaction_signs_and_broadcasts_solana(self, mock_decrypt) -> None:
        mock_decrypt.side_effect = _decrypt_side_effect
        ctx, rpc = _solana_context()

        result = await send_transaction(ctx, {"chain": "solana", "to_address": "11111111111111111111111111111112", "amount": "0.000001"})

        self.assertNotEqual(result.get("status"), "deferred", "Solana writes must not return a deferred status")
        self.assertEqual(result["protocol"], "solana")
        self.assertEqual(result["tx_hash"], "solana-signature-456")
        # A broadcast must have been recorded.
        self.assertTrue(any(c[0] == "solana" for c in rpc.broadcasts))
        # The serialized tx must be valid base64 decodable bytes (a real signed tx).
        raw = next(c[2][0] for c in rpc.broadcasts if c[0] == "solana")
        decoded = base64.b64decode(raw)
        self.assertGreater(len(decoded), 50, "expected a real serialized Solana transaction")


class TronWriteTransactionTestCase(unittest.IsolatedAsyncioTestCase):
    @patch("backend.tools.transaction_tools.decrypt_private_key")
    @patch("backend.tools.transaction_tools.update_agent", new=AsyncMock())
    async def test_send_transaction_signs_and_broadcasts_tron(self, mock_decrypt) -> None:
        mock_decrypt.side_effect = _decrypt_side_effect
        ctx, rpc = _tron_context()

        result = await send_transaction(ctx, {"chain": "tron", "to_address": "TPBkHycN1Hmr2bFcfjvp2fjkca1hfPbPka", "amount": "1"})

        self.assertNotEqual(result.get("status"), "deferred", "Tron writes must not return a deferred status")
        self.assertEqual(result["protocol"], "tron")
        self.assertEqual(result["tx_hash"], "tron-tx-hash-123")
        self.assertTrue(any(c[0] == "tron" for c in rpc.broadcasts))

    @patch("backend.tools.transaction_tools.decrypt_private_key")
    @patch("backend.tools.transaction_tools.update_agent", new=AsyncMock())
    async def test_contract_call_tron_signs_and_broadcasts(self, mock_decrypt) -> None:
        mock_decrypt.side_effect = _decrypt_side_effect
        ctx, rpc = _tron_context()

        result = await contract_call(
            ctx,
            {
                "chain": "tron",
                "contract_address": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",
                "abi_function": "transfer",
                "args": [],
                "data": "a9059cbb",
            },
        )

        self.assertNotEqual(result.get("status"), "deferred")
        self.assertEqual(result["protocol"], "tron")
        self.assertEqual(result["tx_hash"], "tron-tx-hash-123")


if __name__ == "__main__":
    unittest.main()
