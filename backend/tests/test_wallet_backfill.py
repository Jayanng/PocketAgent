import os
import tempfile
import unittest
from unittest.mock import patch

from backend.database import create_agent, init_db
from backend.services.wallets import ensure_agent_write_wallets, missing_write_protocols


class WalletBackfillTestCase(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db_path = os.path.join(self.tmp.name, "wallet-backfill.db")
        self.env_patcher = patch.dict(
            os.environ,
            {"DATABASE_PATH": self.db_path, "ENCRYPTION_KEY": "test-key"},
            clear=False,
        )
        self.env_patcher.start()
        from backend.config import get_settings

        get_settings.cache_clear()
        await init_db()
        import aiosqlite

        self.db = await aiosqlite.connect(self.db_path)
        self.db.row_factory = aiosqlite.Row

    async def asyncTearDown(self) -> None:
        await self.db.close()
        from backend.config import get_settings

        get_settings.cache_clear()
        self.env_patcher.stop()
        self.tmp.cleanup()

    @patch("backend.services.wallets.create_protocol_wallet")
    async def test_ensure_agent_write_wallets_backfills_missing_protocols(self, mock_create) -> None:
        mock_create.side_effect = lambda protocol: {
            "address": f"{protocol}-wallet",
            "encrypted_private_key": f"encrypted-{protocol}",
        }
        agent = await create_agent(
            self.db,
            name="Legacy Agent",
            encrypted_private_key="legacy-evm",
            wallet_address="0xEVM",
            encrypted_wallets={"evm": "legacy-evm", "solana": "sol", "tron": "tron"},
            wallet_addresses={"evm": "0xEVM", "solana": "So1", "tron": "TX"},
        )
        self.assertEqual(missing_write_protocols(agent), ["cosmos", "near", "sui"])

        updated = await ensure_agent_write_wallets(self.db, agent)

        for protocol in ("cosmos", "near", "sui"):
            self.assertEqual(updated["wallet_addresses"][protocol], f"{protocol}-wallet")
            self.assertEqual(updated["encrypted_wallets"][protocol], f"encrypted-{protocol}")
        self.assertEqual(updated["wallet_addresses"]["evm"], "0xEVM")
        self.assertEqual(mock_create.call_count, 3)
        self.assertEqual(
            [call.args[0] for call in mock_create.call_args_list],
            ["cosmos", "near", "sui"],
        )


if __name__ == "__main__":
    unittest.main()