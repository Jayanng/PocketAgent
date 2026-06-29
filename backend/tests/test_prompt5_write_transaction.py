import unittest
from unittest.mock import AsyncMock, patch

from eth_account import Account
from solders.keypair import Keypair

from backend.tools.registry import ToolContext
from backend.tools.transaction_tools import contract_call, send_erc20, send_transaction


EVM_PRIVATE_KEY = "0x4f3edf983ac636a65a842ce7c78d9aa706d3b113bce9c46f30d7d21715b23b1d"
SOLANA_PRIVATE_KEY = Keypair.from_seed(bytes.fromhex(EVM_PRIVATE_KEY.removeprefix("0x"))).to_bytes().hex()
TRON_PRIVATE_KEY = EVM_PRIVATE_KEY.removeprefix("0x")


class _WriteFakeRPC:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, list]] = []
        self.sent_raw: list[tuple[str, str]] = []
        self.settings = type("S", (), {"notional_pokt_per_relay": 0.00089})()

    def get_protocol(self, chain: str) -> str:
        return {
            "ethereum": "evm",
            "solana": "solana",
            "tron": "tron",
            "sui": "sui",
            "near": "near",
            "osmosis": "cosmos",
        }[chain]

    async def get_balance(self, chain: str, address: str) -> dict:
        symbols = {
            "ethereum": "ETH",
            "solana": "SOL",
            "tron": "TRX",
            "sui": "SUI",
            "near": "NEAR",
            "osmosis": "OSMO",
        }
        return {
            "wei": 10**30,
            "raw": 10**30,
            "symbol": symbols.get(chain, "TOKEN"),
        }

    async def call(self, chain: str, method: str, params: list | None = None) -> object:
        params = params or []
        self.calls.append((chain, method, params))
        if chain == "ethereum" and method == "eth_gasPrice":
            return hex(1_000_000_000)
        if chain == "ethereum" and method == "eth_estimateGas":
            return hex(21_000)
        if chain == "ethereum" and method == "eth_call":
            return "0x"
        if chain == "solana" and method == "getLatestBlockhash":
            return {"value": {"blockhash": "EETubP5AKHgjPAhzPAFcb8BAY1hMH6tbJyDPwWXfPbe9"}}
        if chain == "solana" and method == "sendTransaction":
            return "solana-signature-456"
        if chain == "tron" and method == "wallet/createtransaction":
            return {
                "txID": "00" * 32,
                "raw_data": {"contract": []},
                "raw_data_hex": "0a02",
            }
        if chain == "tron" and method == "wallet/broadcasttransaction":
            return {"result": True, "txid": "tron-tx-hash-123"}
        raise AssertionError(f"unexpected RPC call: {chain}.{method} {params}")

    async def send_raw_transaction(self, chain: str, raw_tx: str) -> str:
        self.sent_raw.append((chain, raw_tx))
        return "0xtransactionhash"

    async def get_chain_id(self, chain: str) -> int:
        return 1

    async def get_transaction_count(self, chain: str, address: str) -> int:
        return 0


def _context(chains: list[str]) -> tuple[ToolContext, _WriteFakeRPC]:
    rpc = _WriteFakeRPC()
    account = Account.from_key(EVM_PRIVATE_KEY)
    agent = {
        "id": "agent-write",
        "chains": chains,
        "encrypted_private_key": "encrypted-blob",
        "encrypted_wallets": {
            "evm": "encrypted-blob",
            "solana": "encrypted-solana",
            "tron": "encrypted-tron",
            "sui": "encrypted-sui",
        },
        "wallet_address": account.address,
        "wallet_addresses": {
            "evm": account.address,
            "solana": str(Keypair.from_bytes(bytes.fromhex(SOLANA_PRIVATE_KEY)).pubkey()),
        },
        "spending_cap": 10.0,
        "total_spent": 0.0,
        "total_spent_by_chain": {},
    }
    return ToolContext(agent=agent, rpc_client=rpc, relay_tracker=None, db=None), rpc


def _decrypt_side_effect(encrypted: str) -> str:
    return {
        "encrypted-blob": EVM_PRIVATE_KEY,
        "encrypted-solana": SOLANA_PRIVATE_KEY,
        "encrypted-tron": TRON_PRIVATE_KEY,
        "encrypted-sui": "AHsDz816o1j59XMM7OhxABaFVI2d7ttDNh1iMt/ItGfF",
        "encrypted-near": "ed25519:3D4YudUqre6Rpf8uDzZtk7aXPtyXJ9F8Kj3YqYqYqYqYq",
        "encrypted-cosmos": EVM_PRIVATE_KEY.removeprefix("0x"),
    }[encrypted]


class EVMWriteTransactionTestCase(unittest.IsolatedAsyncioTestCase):
    @patch("backend.tools.transaction_tools.decrypt_private_key", return_value=EVM_PRIVATE_KEY)
    @patch("backend.tools.transaction_tools.update_agent", new=AsyncMock())
    async def test_send_transaction_signs_and_broadcasts_evm(self, mock_decrypt) -> None:
        ctx, rpc = _context(["ethereum"])

        result = await send_transaction(
            ctx,
            {
                "chain": "ethereum",
                "to_address": "0x000000000000000000000000000000000000dEaD",
                "amount": "0.01",
            },
        )

        self.assertEqual(result["protocol"], "evm")
        self.assertEqual(result["tx_hash"], "0xtransactionhash")
        self.assertEqual(len(rpc.sent_raw), 1)
        self.assertEqual(rpc.sent_raw[0][0], "ethereum")
        int(rpc.sent_raw[0][1].removeprefix("0x"), 16)
        self.assertEqual(result["cap_spend_native"], "0.010021")
        self.assertEqual(ctx.agent["total_spent_by_chain"]["ethereum"], 0.010021)

    @patch("backend.tools.transaction_tools.decrypt_private_key", return_value=EVM_PRIVATE_KEY)
    async def test_spending_cap_is_tracked_per_chain(self, mock_decrypt) -> None:
        ctx, rpc = _context(["ethereum", "solana"])
        ctx.agent["spending_cap"] = 1
        ctx.agent["total_spent"] = 0.9
        ctx.agent["total_spent_by_chain"] = {"solana": 0.9}

        result = await send_transaction(
            ctx,
            {
                "chain": "ethereum",
                "to_address": "0x000000000000000000000000000000000000dEaD",
                "amount": "0.2",
            },
        )

        self.assertEqual(result["tx_hash"], "0xtransactionhash")
        self.assertEqual(ctx.agent["total_spent_by_chain"]["solana"], 0.9)
        self.assertEqual(ctx.agent["total_spent_by_chain"]["ethereum"], 0.200021)

    @patch("backend.tools.transaction_tools.decrypt_private_key", return_value=EVM_PRIVATE_KEY)
    async def test_spending_cap_blocks_current_chain_only(self, mock_decrypt) -> None:
        ctx, rpc = _context(["ethereum"])
        ctx.agent["spending_cap"] = 1
        ctx.agent["total_spent_by_chain"] = {"ethereum": 0.995}

        with self.assertRaises(PermissionError):
            await send_transaction(
                ctx,
                {
                    "chain": "ethereum",
                    "to_address": "0x000000000000000000000000000000000000dEaD",
                    "amount": "0.01",
                },
            )

        self.assertEqual(rpc.sent_raw, [])

    @patch("backend.tools.transaction_tools.decrypt_private_key", return_value=EVM_PRIVATE_KEY)
    async def test_erc20_write_requires_spending_cap_for_gas(self, mock_decrypt) -> None:
        ctx, rpc = _context(["ethereum"])
        ctx.agent["spending_cap"] = 0

        with self.assertRaises(PermissionError):
            await send_erc20(
                ctx,
                {
                    "chain": "ethereum",
                    "token_address": "0x0000000000000000000000000000000000000001",
                    "to_address": "0x000000000000000000000000000000000000dEaD",
                    "amount": "1",
                },
            )

        self.assertEqual(rpc.sent_raw, [])

    @patch("backend.tools.transaction_tools.decrypt_private_key", return_value=EVM_PRIVATE_KEY)
    async def test_zero_value_contract_write_requires_spending_cap_for_gas(self, mock_decrypt) -> None:
        ctx, rpc = _context(["ethereum"])
        ctx.agent["spending_cap"] = 0

        with self.assertRaises(PermissionError):
            await contract_call(
                ctx,
                {
                    "chain": "ethereum",
                    "contract_address": "0x000000000000000000000000000000000000dEaD",
                    "abi_function": "approve(address,uint256)",
                    "args": ["0x000000000000000000000000000000000000dEaD", "1"],
                    "write": True,
                },
            )

        self.assertEqual(rpc.sent_raw, [])

    async def test_evm_read_contract_call_does_not_require_signing(self) -> None:
        ctx, rpc = _context(["ethereum"])

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
        self.assertEqual(rpc.sent_raw, [])
        self.assertEqual(rpc.calls[0][1], "eth_call")
        self.assertTrue(rpc.calls[0][2][0]["data"].startswith("0x70a08231"))


class NonEVMWriteTransactionTestCase(unittest.IsolatedAsyncioTestCase):
    @patch("backend.tools.transaction_tools.decrypt_private_key", side_effect=_decrypt_side_effect)
    @patch("backend.tools.transaction_tools.update_agent", new=AsyncMock())
    async def test_send_transaction_signs_and_broadcasts_solana(self, mock_decrypt) -> None:
        ctx, rpc = _context(["solana"])

        result = await send_transaction(
            ctx,
            {
                "chain": "solana",
                "to_address": "11111111111111111111111111111112",
                "amount": "0.000001",
            },
        )

        self.assertEqual(result["protocol"], "solana")
        self.assertEqual(result["tx_hash"], "solana-signature-456")
        self.assertEqual(result["lamports"], 1000)
        self.assertTrue(any(call[1] == "sendTransaction" for call in rpc.calls))
        self.assertEqual(rpc.sent_raw, [])

    @patch("backend.tools.transaction_tools.decrypt_private_key", side_effect=_decrypt_side_effect)
    @patch("backend.tools.transaction_tools.update_agent", new=AsyncMock())
    @patch(
        "backend.services.sui_transfer.execute_sui_native_transfer",
        return_value={
            "from": "0x9f2eee3323919729963640cb311686093fcee80c2b4c9d80a421c8fffc4fdd56",
            "tx_hash": "sui-digest-789",
            "amount_mist": 1_000_000_000,
        },
    )
    async def test_send_transaction_signs_and_broadcasts_sui(self, mock_execute, mock_decrypt) -> None:
        ctx, rpc = _context(["sui"])

        result = await send_transaction(
            ctx,
            {
                "chain": "sui",
                "to_address": "0x00000000000000000000000000000000000000000000000000000000000000dEaD",
                "amount": "1",
            },
        )

        self.assertEqual(result["protocol"], "sui")
        self.assertEqual(result["tx_hash"], "sui-digest-789")
        self.assertEqual(result["amount_mist"], 1_000_000_000)
        mock_execute.assert_called_once()
        self.assertEqual(rpc.calls, [])
        self.assertEqual(rpc.sent_raw, [])

    @patch("backend.tools.transaction_tools.decrypt_private_key", side_effect=_decrypt_side_effect)
    @patch("backend.tools.transaction_tools.update_agent", new=AsyncMock())
    @patch(
        "backend.services.near_transfer.execute_near_native_transfer",
        return_value={
            "from": "a" * 64,
            "tx_hash": "near-tx-hash-456",
            "amount_yocto": 1_000_000_000_000_000_000_000_000,
        },
    )
    async def test_send_transaction_signs_and_broadcasts_near(self, mock_execute, mock_decrypt) -> None:
        ctx, rpc = _context(["near"])
        ctx.agent["wallet_addresses"]["near"] = "a" * 64
        ctx.agent["encrypted_wallets"]["near"] = "encrypted-near"

        result = await send_transaction(
            ctx,
            {
                "chain": "near",
                "to_address": "bob.near",
                "amount": "1",
            },
        )

        self.assertEqual(result["protocol"], "near")
        self.assertEqual(result["tx_hash"], "near-tx-hash-456")
        self.assertEqual(rpc.calls, [])
        self.assertEqual(rpc.sent_raw, [])

    @patch("backend.tools.transaction_tools.decrypt_private_key", side_effect=_decrypt_side_effect)
    @patch("backend.tools.transaction_tools.update_agent", new=AsyncMock())
    async def test_send_transaction_signs_and_broadcasts_tron(self, mock_decrypt) -> None:
        ctx, rpc = _context(["tron"])

        result = await send_transaction(
            ctx,
            {
                "chain": "tron",
                "to_address": "TPBkHycN1Hmr2bFcfjvp2fjkca1hfPbPka",
                "amount": "1",
            },
        )

        self.assertEqual(result["protocol"], "tron")
        self.assertEqual(result["tx_hash"], "tron-tx-hash-123")
        self.assertTrue(any(call[1] == "wallet/createtransaction" for call in rpc.calls))
        self.assertTrue(any(call[1] == "wallet/broadcasttransaction" for call in rpc.calls))
        self.assertEqual(rpc.sent_raw, [])

    @patch("backend.tools.transaction_tools.decrypt_private_key", side_effect=_decrypt_side_effect)
    @patch("backend.tools.transaction_tools.update_agent", new=AsyncMock())
    @patch(
        "backend.services.cosmos_transfer.execute_cosmos_native_transfer",
        return_value={
            "from": "osmo1sender",
            "tx_hash": "cosmos-tx-hash-123",
            "amount_base": 1_000_000,
            "denom": "uosmo",
            "chain_id": "osmosis-1",
        },
    )
    @patch(
        "backend.services.cosmos_transfer.cosmos_address_from_private_key",
        return_value="osmo1sender",
    )
    async def test_send_transaction_signs_and_broadcasts_cosmos(
        self, _mock_address, mock_execute, _mock_decrypt
    ) -> None:
        ctx, rpc = _context(["osmosis"])
        ctx.agent["encrypted_wallets"]["cosmos"] = "encrypted-cosmos"

        result = await send_transaction(
            ctx,
            {
                "chain": "osmosis",
                "to_address": "osmo1recipient",
                "amount": "1",
            },
        )

        self.assertEqual(result["protocol"], "cosmos")
        self.assertEqual(result["tx_hash"], "cosmos-tx-hash-123")
        self.assertEqual(rpc.calls, [])
        self.assertEqual(rpc.sent_raw, [])

    async def test_non_evm_token_and_contract_writes_defer_without_broadcast(self) -> None:
        ctx, rpc = _context(["solana", "tron"])

        token_result = await send_erc20(
            ctx,
            {
                "chain": "solana",
                "token_address": "TokenMint",
                "to_address": "Recipient",
                "amount": "1",
            },
        )
        contract_result = await contract_call(
            ctx,
            {
                "chain": "tron",
                "contract_address": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",
                "abi_function": "transfer",
                "args": [],
                "data": "a9059cbb",
                "value": "1",
            },
        )

        self.assertEqual(token_result["status"], "deferred")
        self.assertEqual(contract_result["status"], "deferred")
        self.assertEqual(rpc.calls, [])
        self.assertEqual(rpc.sent_raw, [])


if __name__ == "__main__":
    unittest.main()
