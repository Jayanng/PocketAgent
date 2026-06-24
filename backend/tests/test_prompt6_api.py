import json
import os
import sqlite3
import tempfile
import unittest
import uuid
from datetime import datetime, timezone
from unittest.mock import patch

from fastapi.testclient import TestClient


class Prompt6APITestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db_path = os.path.join(self.tmp.name, "pocketagent-test.db")
        self.env_patcher = patch.dict(
            os.environ,
            {
                "DATABASE_PATH": self.db_path,
                "ENCRYPTION_KEY": "test-encryption-key",
                "JWT_SECRET": "",
                "OPENAI_API_KEY": "",
                "GMI_API_KEY": "",
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

    def create_agent(self, name: str = "Test Agent", capabilities: list[str] | None = None) -> dict:
        response = self.client.post(
            "/api/agents",
            json={
                "name": name,
                "description": "Prompt 6 test agent",
                "chains": ["ethereum"],
                "capabilities": capabilities or ["read"],
            },
        )
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    @staticmethod
    def auth_headers(agent: dict) -> dict[str, str]:
        return {"X-Agent-Access-Token": agent["access_token"]}

    def seed_conversation(self, agent_id: str, with_messages: bool = False) -> str:
        conversation_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO conversations (id, agent_id, title, created_at) VALUES (?, ?, ?, ?)",
                (conversation_id, agent_id, "Seeded conversation", now),
            )
            if with_messages:
                conn.execute(
                    """
                    INSERT INTO messages
                        (id, conversation_id, role, content, chain_calls, tokens_used, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid.uuid4()),
                        conversation_id,
                        "user",
                        "balance?",
                        json.dumps([]),
                        0,
                        now,
                    ),
                )
                conn.execute(
                    """
                    INSERT INTO messages
                        (id, conversation_id, role, content, chain_calls, tokens_used, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid.uuid4()),
                        conversation_id,
                        "assistant",
                        "1 ETH",
                        json.dumps([{"tool": "evm_get_balance"}]),
                        12,
                        now,
                    ),
                )
        return conversation_id

    def test_agent_crud_fund_and_private_key_redaction(self) -> None:
        created = self.create_agent()
        agent_id = created["id"]
        self.assertTrue(created["wallet_address"].startswith("0x"))
        self.assertTrue(created["wallet_addresses"]["evm"].startswith("0x"))
        self.assertIn("solana", created["wallet_addresses"])
        self.assertIn("tron", created["wallet_addresses"])

        agents = self.client.get("/api/agents")
        self.assertEqual(agents.status_code, 200)
        listed_agent = next(agent for agent in agents.json() if agent["id"] == agent_id)
        self.assertNotIn("wallet_address", listed_agent)
        self.assertNotIn("wallet_addresses", listed_agent)

        detail = self.client.get(f"/api/agents/{agent_id}", headers=self.auth_headers(created))
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.json()["wallet_address"], created["wallet_address"])
        self.assertEqual(detail.json()["wallet_addresses"]["solana"], created["wallet_addresses"]["solana"])
        self.assertNotIn("encrypted_private_key", detail.json())
        self.assertNotIn("access_token_hash", detail.json())

        updated = self.client.put(
            f"/api/agents/{agent_id}",
            json={"name": "Renamed Agent", "spending_cap": 0.25},
            headers=self.auth_headers(created),
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["name"], "Renamed Agent")
        self.assertEqual(updated.json()["spending_cap"], 0.25)

        fund = self.client.post(f"/api/agents/{agent_id}/fund", headers=self.auth_headers(created))
        self.assertEqual(fund.status_code, 200)
        self.assertEqual(fund.json()["wallet_address"], created["wallet_address"])

        solana_fund = self.client.post(f"/api/agents/{agent_id}/fund?chain=solana", headers=self.auth_headers(created))
        self.assertEqual(solana_fund.status_code, 200)
        self.assertEqual(solana_fund.json()["protocol"], "solana")
        self.assertEqual(solana_fund.json()["wallet_address"], created["wallet_addresses"]["solana"])

    def test_agent_balances_endpoint_uses_agent_wallet_and_chains(self) -> None:
        created = self.create_agent()

        class FakePocketRPCClient:
            def get_protocol(self, chain: str) -> str:
                return "evm"

            async def get_balance(self, chain: str, address: str) -> dict:
                self_address = created["wallet_address"]
                assert address == self_address
                assert chain == "ethereum"
                return {
                    "formatted": "0 ETH",
                    "symbol": "ETH",
                    "usd_value": 0,
                }

        with patch("backend.routers.agents.PocketRPCClient", FakePocketRPCClient):
            response = self.client.get(f"/api/agents/{created['id']}/balances", headers=self.auth_headers(created))

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["wallet_address"], created["wallet_address"])
        self.assertEqual(response.json()["balances"]["ethereum"]["formatted"], "0 ETH")

    def test_soft_deleted_agent_is_not_usable(self) -> None:
        created = self.create_agent()
        agent_id = created["id"]

        deleted = self.client.delete(f"/api/agents/{agent_id}", headers=self.auth_headers(created))
        self.assertEqual(deleted.status_code, 204)

        agents = self.client.get("/api/agents")
        self.assertEqual(agents.status_code, 200)
        self.assertNotIn(agent_id, {agent["id"] for agent in agents.json()})
        self.assertEqual(self.client.post(f"/api/agents/{agent_id}/fund", headers=self.auth_headers(created)).status_code, 410)
        self.assertEqual(
            self.client.put(f"/api/agents/{agent_id}", json={"name": "Blocked"}, headers=self.auth_headers(created)).status_code,
            410,
        )
        self.assertEqual(self.client.get(f"/api/conversations?agent_id={agent_id}", headers=self.auth_headers(created)).status_code, 410)
        self.assertEqual(
            self.client.post("/api/chat", json={"agent_id": agent_id, "message": "hello"}, headers=self.auth_headers(created)).status_code,
            410,
        )

    def test_conversation_list_messages_and_delete(self) -> None:
        created = self.create_agent()
        conversation_id = self.seed_conversation(created["id"], with_messages=True)

        conversations = self.client.get(f"/api/conversations?agent_id={created['id']}", headers=self.auth_headers(created))
        self.assertEqual(conversations.status_code, 200)
        self.assertEqual(conversations.json()[0]["id"], conversation_id)

        messages = self.client.get(f"/api/conversations/{conversation_id}/messages", headers=self.auth_headers(created))
        self.assertEqual(messages.status_code, 200)
        self.assertEqual([message["role"] for message in messages.json()], ["user", "assistant"])
        self.assertEqual(messages.json()[1]["chain_calls"], [{"tool": "evm_get_balance"}])

        deleted = self.client.delete(f"/api/conversations/{conversation_id}", headers=self.auth_headers(created))
        self.assertEqual(deleted.status_code, 204)
        self.assertEqual(self.client.get(f"/api/conversations/{conversation_id}/messages", headers=self.auth_headers(created)).status_code, 404)

    def test_chat_success_response_shape_is_stable_without_openai(self) -> None:
        created = self.create_agent()

        class FakeAIAgentService:
            async def chat(self, message: str, agent_id: str, conversation_id: str | None = None) -> dict:
                return {
                    "conversation_id": conversation_id or "generated-conversation",
                    "message": {
                        "content": f"ack: {message}",
                        "chain_calls": [{"tool": "evm_get_balance"}],
                        "tokens_used": 42,
                    },
                }

        with patch("backend.routers.chat.AIAgentService", FakeAIAgentService):
            response = self.client.post(
                "/api/chat",
                json={"agent_id": created["id"], "message": "hello"},
                headers=self.auth_headers(created),
            )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(
            response.json(),
            {
                "response": "ack: hello",
                "conversation_id": "generated-conversation",
                "chain_calls": [{"tool": "evm_get_balance"}],
                "tokens_used": 42,
            },
        )

    def test_chat_guard_rails_before_openai(self) -> None:
        agent_one = self.create_agent("Agent One")
        agent_two = self.create_agent("Agent Two")
        agent_two_conversation = self.seed_conversation(agent_two["id"])

        missing = self.client.post(
            "/api/chat",
            json={
                "agent_id": agent_one["id"],
                "message": "hello",
                "conversation_id": "missing",
            },
            headers=self.auth_headers(agent_one),
        )
        self.assertEqual(missing.status_code, 404)

        wrong_owner = self.client.post(
            "/api/chat",
            json={
                "agent_id": agent_one["id"],
                "message": "hello",
                "conversation_id": agent_two_conversation,
            },
            headers=self.auth_headers(agent_one),
        )
        self.assertEqual(wrong_owner.status_code, 403)

        no_openai = self.client.post(
            "/api/chat",
            json={"agent_id": agent_one["id"], "message": "hello"},
            headers=self.auth_headers(agent_one),
        )
        self.assertEqual(no_openai.status_code, 503)

    def test_agent_access_token_is_required_for_sensitive_routes(self) -> None:
        created = self.create_agent()
        self.assertIn("access_token", created)
        self.assertEqual(self.client.get(f"/api/agents/{created['id']}").status_code, 403)
        self.assertEqual(
            self.client.post("/api/chat", json={"agent_id": created["id"], "message": "hello"}).status_code,
            403,
        )

    def test_agent_creation_requires_configured_encryption_key(self) -> None:
        from backend.config import get_settings

        get_settings.cache_clear()
        with patch.dict(os.environ, {"ENCRYPTION_KEY": "", "JWT_SECRET": ""}, clear=False):
            get_settings.cache_clear()
            response = self.client.post(
                "/api/agents",
                json={"name": "No Key Agent", "chains": ["ethereum"], "capabilities": ["read"]},
            )
        get_settings.cache_clear()

        self.assertEqual(response.status_code, 503)
        self.assertIn("ENCRYPTION_KEY", response.json()["detail"])

    def test_relative_database_path_resolves_from_backend_directory(self) -> None:
        from pathlib import Path

        from backend.config import BACKEND_DIR, get_settings

        get_settings.cache_clear()
        with patch.dict(os.environ, {"DATABASE_PATH": "data/relative-test.db"}, clear=False):
            get_settings.cache_clear()
            settings = get_settings()
        get_settings.cache_clear()

        self.assertEqual(
            Path(settings.database_path),
            (BACKEND_DIR / "data" / "relative-test.db").resolve(),
        )


if __name__ == "__main__":
    unittest.main()
