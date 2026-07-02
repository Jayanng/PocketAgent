"""Tests for reissue-challenge and reissue-token endpoints."""
import json
import os
import tempfile
import time
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient


class ReissueEndpointTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db_path = os.path.join(self.tmp.name, "pocketagent-reissue.db")
        self.env_patcher = patch.dict(
            os.environ,
            {
                "DATABASE_PATH": self.db_path,
                "ENCRYPTION_KEY": "test-encryption-key-for-reissue",
                "JWT_SECRET": "test-jwt-secret",
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

    def _create_agent(self, name: str = "Reissue Test Agent") -> dict:
        resp = self.client.post(
            "/api/agents",
            json={
                "name": name,
                "description": "reissue test",
                "chains": ["ethereum"],
                "capabilities": ["read"],
            },
        )
        self.assertEqual(resp.status_code, 201, resp.text)
        return resp.json()

    # --- Challenge endpoint ---

    def test_challenge_returns_canonical_message(self):
        agent = self._create_agent()
        resp = self.client.get(f"/api/agents/{agent['id']}/reissue-challenge")
        self.assertEqual(resp.status_code, 200, resp.text)
        data = resp.json()
        self.assertTrue(data["message"].startswith("pocketagent:reissue:"))
        self.assertIn(agent["id"], data["message"])
        self.assertLess(abs(data["timestamp"] - int(time.time())), 5)

    def test_challenge_nonexistent_agent_returns_404(self):
        resp = self.client.get("/api/agents/nonexistent-id/reissue-challenge")
        self.assertEqual(resp.status_code, 404)

    # --- Reissue-token endpoint: current_token proof ---

    def test_current_token_proof_succeeds(self):
        agent = self._create_agent()
        old_token = agent["access_token"]
        resp = self.client.post(
            f"/api/agents/{agent['id']}/reissue-token",
            json={"proof": {"type": "current_token", "token": old_token}},
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        new_token = resp.json()["access_token"]
        self.assertNotEqual(new_token, old_token)

        # Old token no longer works
        old_resp = self.client.get(
            f"/api/agents/{agent['id']}",
            headers={"X-Agent-Access-Token": old_token},
        )
        self.assertIn(old_resp.status_code, (401, 403))

        # New token works
        new_resp = self.client.get(
            f"/api/agents/{agent['id']}",
            headers={"X-Agent-Access-Token": new_token},
        )
        self.assertEqual(new_resp.status_code, 200)

    def test_wrong_token_returns_401(self):
        agent = self._create_agent()
        resp = self.client.post(
            f"/api/agents/{agent['id']}/reissue-token",
            json={"proof": {"type": "current_token", "token": "wrong-token"}},
        )
        self.assertEqual(resp.status_code, 401)

    def test_empty_token_returns_401(self):
        agent = self._create_agent()
        resp = self.client.post(
            f"/api/agents/{agent['id']}/reissue-token",
            json={"proof": {"type": "current_token", "token": ""}},
        )
        self.assertEqual(resp.status_code, 401)

    def test_nonexistent_agent_returns_404(self):
        resp = self.client.post(
            "/api/agents/nonexistent-id/reissue-token",
            json={"proof": {"type": "current_token", "token": "anything"}},
        )
        self.assertEqual(resp.status_code, 404)

    # --- Wallet signature proof: EVM (the chain always present) ---

    def _sign_evm(self, message: str, priv_hex: str) -> str:
        from eth_account import Account
        from eth_account.messages import encode_defunct
        acct = Account.from_key(priv_hex)
        msg = encode_defunct(text=message)
        signed = Account.sign_message(msg, acct.key)
        return "0x" + signed.signature.hex()

    def test_wallet_signature_proof_succeeds(self):
        agent = self._create_agent()
        # Fetch challenge
        ch = self.client.get(f"/api/agents/{agent['id']}/reissue-challenge").json()
        # We need the private key that produced wallet_address. The create endpoint
        # uses a randomly generated key, so we can't sign here. Instead, manually
        # compute a valid proof: replace the agent's wallet_address with one we own.
        from eth_account import Account
        from eth_account.messages import encode_defunct
        own = Account.create()
        # Patch the agent's wallet_address via direct DB write
        import sqlite3
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE agents SET wallet_address = ? WHERE id = ?",
                (own.address, agent["id"]),
            )
            conn.commit()

        message = ch["message"]
        msg = encode_defunct(text=message)
        signed = Account.sign_message(msg, own.key)
        sig = "0x" + signed.signature.hex()

        resp = self.client.post(
            f"/api/agents/{agent['id']}/reissue-token",
            json={
                "proof": {
                    "type": "wallet_signature",
                    "chain": "ethereum",
                    "message": message,
                    "signature": sig,
                    "public_key": own.address,
                }
            },
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        new_token = resp.json()["access_token"]
        self.assertTrue(len(new_token) > 20)
        # Verify new token authenticates
        new_resp = self.client.get(
            f"/api/agents/{agent['id']}",
            headers={"X-Agent-Access-Token": new_token},
        )
        self.assertEqual(new_resp.status_code, 200)

    def test_wallet_signature_expired_challenge_returns_422(self):
        agent = self._create_agent()
        expired_ts = int(time.time()) - 600  # 10 min ago
        message = f"pocketagent:reissue:{agent['id']}:{expired_ts}"
        from eth_account import Account
        from eth_account.messages import encode_defunct
        own = Account.create()
        # Patch the agent's wallet_address
        import sqlite3
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE agents SET wallet_address = ? WHERE id = ?",
                (own.address, agent["id"]),
            )
            conn.commit()

        msg = encode_defunct(text=message)
        signed = Account.sign_message(msg, own.key)
        sig = "0x" + signed.signature.hex()

        resp = self.client.post(
            f"/api/agents/{agent['id']}/reissue-token",
            json={
                "proof": {
                    "type": "wallet_signature",
                    "chain": "ethereum",
                    "message": message,
                    "signature": sig,
                    "public_key": own.address,
                }
            },
        )
        self.assertEqual(resp.status_code, 422)

    def test_wallet_signature_wrong_signer_returns_401(self):
        agent = self._create_agent()
        ch = self.client.get(f"/api/agents/{agent['id']}/reissue-challenge").json()
        from eth_account import Account
        from eth_account.messages import encode_defunct
        owner = Account.create()
        attacker = Account.create()
        import sqlite3
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE agents SET wallet_address = ? WHERE id = ?",
                (owner.address, agent["id"]),
            )
            conn.commit()

        # Sign with attacker key
        msg = encode_defunct(text=ch["message"])
        signed = Account.sign_message(msg, attacker.key)
        sig = "0x" + signed.signature.hex()

        resp = self.client.post(
            f"/api/agents/{agent['id']}/reissue-token",
            json={
                "proof": {
                    "type": "wallet_signature",
                    "chain": "ethereum",
                    "message": ch["message"],
                    "signature": sig,
                    "public_key": owner.address,  # claims owner but signs with attacker
                }
            },
        )
        self.assertEqual(resp.status_code, 401)


if __name__ == "__main__":
    unittest.main()
