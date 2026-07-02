"""End-to-end token reissue lifecycle: create → rotate (current_token) → rotate (wallet_signature)."""
import os
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient


class ReissueFlowTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db_path = os.path.join(self.tmp.name, "pocketagent-flow.db")
        self.env_patcher = patch.dict(
            os.environ,
            {
                "DATABASE_PATH": self.db_path,
                "ENCRYPTION_KEY": "test-encryption-key-for-flow",
                "JWT_SECRET": "test-jwt-secret-flow",
                "OPENAI_API_KEY": "",
                "GMI_API_KEY": "",
                "DISABLE_AGENT_AUTH": "false",
            },
            clear=False,
        )
        self.env_patcher.start()
        from backend.config import get_settings
        from backend.main import app

        get_settings.cache_clear()
        self.client = TestClient(app)
        self.client.__enter__()

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)
        from backend.config import get_settings
        get_settings.cache_clear()
        self.env_patcher.stop()
        self.tmp.cleanup()

    def _create_agent(self) -> tuple[dict, "object"]:
        """Create agent and replace its wallet_address with one whose key we control."""
        from eth_account import Account
        resp = self.client.post(
            "/api/agents",
            json={
                "name": "Lifecycle Agent",
                "description": "full lifecycle",
                "chains": ["ethereum"],
                "capabilities": ["read"],
            },
        )
        self.assertEqual(resp.status_code, 201, resp.text)
        agent = resp.json()
        own = Account.create()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE agents SET wallet_address = ? WHERE id = ?",
                (own.address, agent["id"]),
            )
            conn.commit()
        return agent, own

    def _sign_evm(self, message: str, account) -> str:
        from eth_account.messages import encode_defunct
        msg = encode_defunct(text=message)
        signed = account.sign_message(msg)
        return "0x" + signed.signature.hex()

    def _get(self, agent_id: str, token: str) -> int:
        resp = self.client.get(
            f"/api/agents/{agent_id}",
            headers={"X-Agent-Access-Token": token},
        )
        return resp.status_code

    def test_full_lifecycle_three_rotations(self):
        agent, eth_key = self._create_agent()
        agent_id = agent["id"]
        t1 = agent["access_token"]

        # T1 works
        self.assertEqual(self._get(agent_id, t1), 200)

        # Rotate via current_token
        r1 = self.client.post(
            f"/api/agents/{agent_id}/reissue-token",
            json={"proof": {"type": "current_token", "token": t1}},
        )
        self.assertEqual(r1.status_code, 200, r1.text)
        t2 = r1.json()["access_token"]
        self.assertNotEqual(t1, t2)

        # T1 fails, T2 works
        self.assertIn(self._get(agent_id, t1), (401, 403))
        self.assertEqual(self._get(agent_id, t2), 200)

        # Rotate via wallet signature (EVM)
        challenge = self.client.get(f"/api/agents/{agent_id}/reissue-challenge").json()
        sig = self._sign_evm(challenge["message"], eth_key)
        r2 = self.client.post(
            f"/api/agents/{agent_id}/reissue-token",
            json={
                "proof": {
                    "type": "wallet_signature",
                    "chain": "ethereum",
                    "message": challenge["message"],
                    "signature": sig,
                    "public_key": eth_key.address,
                }
            },
        )
        self.assertEqual(r2.status_code, 200, r2.text)
        t3 = r2.json()["access_token"]
        self.assertNotEqual(t2, t3)

        # T2 fails, T3 works
        self.assertIn(self._get(agent_id, t2), (401, 403))
        self.assertEqual(self._get(agent_id, t3), 200)

        # Rotate again via current_token with t3
        r3 = self.client.post(
            f"/api/agents/{agent_id}/reissue-token",
            json={"proof": {"type": "current_token", "token": t3}},
        )
        self.assertEqual(r3.status_code, 200, r3.text)
        t4 = r3.json()["access_token"]
        self.assertEqual(self._get(agent_id, t4), 200)
        self.assertIn(self._get(agent_id, t3), (401, 403))


if __name__ == "__main__":
    unittest.main()
