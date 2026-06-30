import json
import uuid
from collections.abc import AsyncGenerator
from datetime import datetime, timezone

import aiosqlite

try:
    from .config import ensure_database_directory, get_settings
except ImportError:
    from config import ensure_database_directory, get_settings


async def get_db() -> AsyncGenerator[aiosqlite.Connection, None]:
    settings = get_settings()
    ensure_database_directory(settings.database_path)
    db = await aiosqlite.connect(settings.database_path)
    await db.execute("PRAGMA foreign_keys = ON;")
    db.row_factory = aiosqlite.Row
    try:
        yield db
    finally:
        await db.close()


async def init_db() -> None:
    settings = get_settings()
    ensure_database_directory(settings.database_path)
    async with aiosqlite.connect(settings.database_path) as db:
        await db.execute("PRAGMA foreign_keys = ON;")

        # 1. agents table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS agents (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                chains TEXT,
                capabilities TEXT,
                encrypted_private_key TEXT NOT NULL,
                wallet_address TEXT,
                encrypted_wallets TEXT,
                wallet_addresses TEXT,
                access_token_hash TEXT,
                spending_cap REAL DEFAULT 0.1,
                total_spent REAL DEFAULT 0.0,
                total_spent_by_chain TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TEXT,
                updated_at TEXT
            )
        """)
        await _ensure_column(db, "agents", "encrypted_wallets", "TEXT")
        await _ensure_column(db, "agents", "wallet_addresses", "TEXT")
        await _ensure_column(db, "agents", "access_token_hash", "TEXT")
        await _ensure_column(db, "agents", "total_spent_by_chain", "TEXT")
        await _ensure_column(db, "agents", "sui_tracked_coins", "TEXT")
        await _ensure_column(db, "agents", "access_token_created_at", "TEXT")
        await _ensure_column(db, "agents", "access_token_revoked_at", "TEXT")

        # 2. conversations table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                agent_id TEXT,
                title TEXT,
                created_at TEXT,
                FOREIGN KEY (agent_id) REFERENCES agents(id)
            )
        """)

        # 3. messages table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                conversation_id TEXT,
                role TEXT CHECK(role IN ('user', 'assistant')),
                content TEXT,
                chain_calls TEXT,
                tokens_used INTEGER,
                created_at TEXT,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
            )
        """)
        await _migrate_messages_role_constraint(db)

        # 4. relay_logs table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS relay_logs (
                id TEXT PRIMARY KEY,
                agent_id TEXT,
                chain TEXT,
                method TEXT,
                request_payload TEXT,
                response_status INTEGER,
                latency_ms INTEGER,
                relay_cost_pokt REAL,
                created_at TEXT,
                FOREIGN KEY (agent_id) REFERENCES agents(id)
            )
        """)

        await db.commit()


async def _migrate_messages_role_constraint(db: aiosqlite.Connection) -> None:
    async with db.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'messages'"
    ) as cursor:
        row = await cursor.fetchone()
    table_sql = row[0] if row else ""
    if "CHECK(role IN ('user', 'assistant'))" in table_sql:
        return

    await db.execute("PRAGMA foreign_keys = OFF;")
    await db.execute("ALTER TABLE messages RENAME TO messages_old;")
    await db.execute("""
        CREATE TABLE messages (
            id TEXT PRIMARY KEY,
            conversation_id TEXT,
            role TEXT CHECK(role IN ('user', 'assistant')),
            content TEXT,
            chain_calls TEXT,
            tokens_used INTEGER,
            created_at TEXT,
            FOREIGN KEY (conversation_id) REFERENCES conversations(id)
        )
    """)
    await db.execute("""
        INSERT INTO messages (id, conversation_id, role, content, chain_calls, tokens_used, created_at)
        SELECT
            id,
            conversation_id,
            CASE WHEN role IN ('user', 'assistant') THEN role ELSE 'assistant' END,
            content,
            chain_calls,
            tokens_used,
            created_at
        FROM messages_old
    """)
    await db.execute("DROP TABLE messages_old")
    await db.execute("PRAGMA foreign_keys = ON;")


async def _ensure_column(
    db: aiosqlite.Connection,
    table: str,
    column: str,
    column_type: str,
) -> None:
    async with db.execute(f"PRAGMA table_info({table})") as cursor:
        columns = {row[1] for row in await cursor.fetchall()}
    if column not in columns:
        await db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")


# ─── CRUD: Agents ───────────────────────────────────────────────────────────

async def create_agent(
    db: aiosqlite.Connection,
    name: str,
    encrypted_private_key: str,
    description: str | None = None,
    chains: list[str] | None = None,
    capabilities: list[str] | None = None,
    wallet_address: str | None = None,
    encrypted_wallets: dict[str, str] | None = None,
    wallet_addresses: dict[str, str] | None = None,
    access_token_hash: str | None = None,
    spending_cap: float = 0.1,
) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    agent_id = str(uuid.uuid4())
    await db.execute(
        """
        INSERT INTO agents (id, name, description, chains, capabilities,
                            encrypted_private_key, wallet_address,
                            encrypted_wallets, wallet_addresses, access_token_hash,
                            spending_cap, total_spent, total_spent_by_chain, is_active,
                            created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
        """,
        (
            agent_id,
            name,
            description,
            json.dumps(chains or []),
            json.dumps(capabilities or ["read", "transact", "compare"]),
            encrypted_private_key,
            wallet_address,
            json.dumps(encrypted_wallets or {}),
            json.dumps(wallet_addresses or {}),
            access_token_hash,
            spending_cap,
            0.0,
            json.dumps({}),
            now,
            now,
        ),
    )
    await db.commit()
    return await get_agent(db, agent_id)


async def get_agent(db: aiosqlite.Connection, agent_id: str) -> dict | None:
    async with db.execute("SELECT * FROM agents WHERE id = ?", (agent_id,)) as cursor:
        row = await cursor.fetchone()
    if row is None:
        return None
    return _row_to_agent(row)


async def list_agents(db: aiosqlite.Connection) -> list[dict]:
    async with db.execute(
        "SELECT * FROM agents WHERE is_active = 1 ORDER BY created_at DESC"
    ) as cursor:
        rows = await cursor.fetchall()
    return [_row_to_agent(r) for r in rows]


async def update_agent(db: aiosqlite.Connection, agent_id: str, **fields) -> dict | None:
    existing = await get_agent(db, agent_id)
    if existing is None:
        return None
    allowed = {
        "name", "description", "chains", "capabilities",
        "wallet_address", "encrypted_wallets", "wallet_addresses",
        "access_token_hash", "access_token_created_at", "access_token_revoked_at",
        "spending_cap", "total_spent",
        "total_spent_by_chain", "sui_tracked_coins", "is_active",
    }
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return existing
    if "chains" in updates:
        updates["chains"] = json.dumps(updates["chains"])
    if "capabilities" in updates:
        updates["capabilities"] = json.dumps(updates["capabilities"])
    if "encrypted_wallets" in updates:
        updates["encrypted_wallets"] = json.dumps(updates["encrypted_wallets"])
    if "wallet_addresses" in updates:
        updates["wallet_addresses"] = json.dumps(updates["wallet_addresses"])
    if "total_spent_by_chain" in updates:
        updates["total_spent_by_chain"] = json.dumps(updates["total_spent_by_chain"])
    if "sui_tracked_coins" in updates:
        updates["sui_tracked_coins"] = json.dumps(updates["sui_tracked_coins"])
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [agent_id]
    await db.execute(f"UPDATE agents SET {set_clause} WHERE id = ?", values)
    await db.commit()
    return await get_agent(db, agent_id)


async def delete_agent(db: aiosqlite.Connection, agent_id: str) -> bool:
    cursor = await db.execute(
        "UPDATE agents SET is_active = 0, updated_at = ? WHERE id = ?",
        (datetime.now(timezone.utc).isoformat(), agent_id),
    )
    await db.commit()
    return cursor.rowcount > 0


# ─── CRUD: Conversations ────────────────────────────────────────────────────

async def create_conversation(
    db: aiosqlite.Connection,
    agent_id: str,
    title: str | None = None,
) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    conv_id = str(uuid.uuid4())
    await db.execute(
        "INSERT INTO conversations (id, agent_id, title, created_at) VALUES (?, ?, ?, ?)",
        (conv_id, agent_id, title, now),
    )
    await db.commit()
    return await get_conversation(db, conv_id)


async def get_conversation(db: aiosqlite.Connection, conversation_id: str) -> dict | None:
    async with db.execute(
        "SELECT * FROM conversations WHERE id = ?", (conversation_id,)
    ) as cursor:
        row = await cursor.fetchone()
    if row is None:
        return None
    return dict(row)


async def list_conversations(db: aiosqlite.Connection, agent_id: str) -> list[dict]:
    async with db.execute(
        "SELECT * FROM conversations WHERE agent_id = ? ORDER BY created_at DESC",
        (agent_id,),
    ) as cursor:
        rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def update_conversation(
    db: aiosqlite.Connection,
    conversation_id: str,
    title: str | None = None,
) -> dict | None:
    existing = await get_conversation(db, conversation_id)
    if existing is None:
        return None
    await db.execute(
        "UPDATE conversations SET title = ? WHERE id = ?",
        (title, conversation_id),
    )
    await db.commit()
    return await get_conversation(db, conversation_id)


async def delete_conversation(db: aiosqlite.Connection, conversation_id: str) -> bool:
    await db.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
    cursor = await db.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
    await db.commit()
    return cursor.rowcount > 0


# ─── CRUD: Messages ─────────────────────────────────────────────────────────

async def create_message(
    db: aiosqlite.Connection,
    conversation_id: str,
    role: str,
    content: str,
    chain_calls: list[dict] | None = None,
    tokens_used: int = 0,
) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    msg_id = str(uuid.uuid4())
    await db.execute(
        """
        INSERT INTO messages (id, conversation_id, role, content, chain_calls, tokens_used, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (msg_id, conversation_id, role, content, json.dumps(chain_calls or []), tokens_used, now),
    )
    await db.commit()
    return await get_message(db, msg_id)


async def get_message(db: aiosqlite.Connection, message_id: str) -> dict | None:
    async with db.execute(
        "SELECT * FROM messages WHERE id = ?", (message_id,)
    ) as cursor:
        row = await cursor.fetchone()
    if row is None:
        return None
    return _row_to_message(row)


async def list_messages(
    db: aiosqlite.Connection,
    conversation_id: str,
    limit: int = 50,
) -> list[dict]:
    async with db.execute(
        "SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at ASC LIMIT ?",
        (conversation_id, limit),
    ) as cursor:
        rows = await cursor.fetchall()
    return [_row_to_message(r) for r in rows]


async def update_message(
    db: aiosqlite.Connection,
    message_id: str,
    content: str | None = None,
    chain_calls: list[dict] | None = None,
    tokens_used: int | None = None,
) -> dict | None:
    existing = await get_message(db, message_id)
    if existing is None:
        return None
    updates: dict[str, object] = {}
    if content is not None:
        updates["content"] = content
    if chain_calls is not None:
        updates["chain_calls"] = json.dumps(chain_calls)
    if tokens_used is not None:
        updates["tokens_used"] = tokens_used
    if not updates:
        return existing
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [message_id]
    await db.execute(f"UPDATE messages SET {set_clause} WHERE id = ?", values)
    await db.commit()
    return await get_message(db, message_id)


async def delete_message(db: aiosqlite.Connection, message_id: str) -> bool:
    cursor = await db.execute("DELETE FROM messages WHERE id = ?", (message_id,))
    await db.commit()
    return cursor.rowcount > 0


# ─── CRUD: Relay Logs ───────────────────────────────────────────────────────

async def create_relay_log(
    db: aiosqlite.Connection,
    agent_id: str | None,
    chain: str,
    method: str,
    request_payload: dict | None = None,
    response_status: int = 200,
    latency_ms: int = 0,
    relay_cost_pokt: float = 0.0,
) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    log_id = str(uuid.uuid4())
    await db.execute(
        """
        INSERT INTO relay_logs (id, agent_id, chain, method, request_payload,
                                response_status, latency_ms, relay_cost_pokt, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            log_id, agent_id, chain, method,
            json.dumps(request_payload or {}),
            response_status, latency_ms, relay_cost_pokt, now,
        ),
    )
    await db.commit()
    return await get_relay_log(db, log_id)


async def get_relay_log(db: aiosqlite.Connection, log_id: str) -> dict | None:
    async with db.execute(
        "SELECT * FROM relay_logs WHERE id = ?", (log_id,)
    ) as cursor:
        row = await cursor.fetchone()
    if row is None:
        return None
    return _row_to_relay_log(row)


async def list_relay_logs(
    db: aiosqlite.Connection,
    agent_id: str | None = None,
    limit: int = 100,
) -> list[dict]:
    if agent_id:
        query = "SELECT * FROM relay_logs WHERE agent_id = ? ORDER BY created_at DESC LIMIT ?"
        params: tuple = (agent_id, limit)
    else:
        query = "SELECT * FROM relay_logs ORDER BY created_at DESC LIMIT ?"
        params = (limit,)
    async with db.execute(query, params) as cursor:
        rows = await cursor.fetchall()
    return [_row_to_relay_log(r) for r in rows]


async def update_relay_log(
    db: aiosqlite.Connection,
    log_id: str,
    response_status: int | None = None,
    latency_ms: int | None = None,
    relay_cost_pokt: float | None = None,
    request_payload: dict | None = None,
) -> dict | None:
    existing = await get_relay_log(db, log_id)
    if existing is None:
        return None
    updates: dict[str, object] = {}
    if response_status is not None:
        updates["response_status"] = response_status
    if latency_ms is not None:
        updates["latency_ms"] = latency_ms
    if relay_cost_pokt is not None:
        updates["relay_cost_pokt"] = relay_cost_pokt
    if request_payload is not None:
        updates["request_payload"] = json.dumps(request_payload)
    if not updates:
        return existing
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [log_id]
    await db.execute(f"UPDATE relay_logs SET {set_clause} WHERE id = ?", values)
    await db.commit()
    return await get_relay_log(db, log_id)


async def delete_relay_log(db: aiosqlite.Connection, log_id: str) -> bool:
    cursor = await db.execute("DELETE FROM relay_logs WHERE id = ?", (log_id,))
    await db.commit()
    return cursor.rowcount > 0


# ─── Row converters ─────────────────────────────────────────────────────────

def _row_to_agent(row) -> dict:
    d = dict(row)
    dict_fields = {"encrypted_wallets", "wallet_addresses", "total_spent_by_chain"}
    for json_field in (
        "chains",
        "capabilities",
        "encrypted_wallets",
        "wallet_addresses",
        "total_spent_by_chain",
        "sui_tracked_coins",
    ):
        if isinstance(d.get(json_field), str):
            try:
                parsed = json.loads(d[json_field])
                d[json_field] = parsed if parsed is not None else ({} if json_field in dict_fields else [])
            except (json.JSONDecodeError, TypeError):
                d[json_field] = {} if json_field in dict_fields else []
    if d.get("wallet_addresses") is None:
        d["wallet_addresses"] = {}
    if d.get("encrypted_wallets") is None:
        d["encrypted_wallets"] = {}
    if d.get("total_spent_by_chain") is None:
        d["total_spent_by_chain"] = {}
    if d.get("sui_tracked_coins") is None:
        d["sui_tracked_coins"] = []
    if isinstance(d.get("is_active"), int):
        d["is_active"] = bool(d["is_active"])
    return d


def _row_to_message(row) -> dict:
    d = dict(row)
    if isinstance(d.get("chain_calls"), str):
        try:
            d["chain_calls"] = json.loads(d["chain_calls"])
        except (json.JSONDecodeError, TypeError):
            d["chain_calls"] = []
    return d


def _row_to_relay_log(row) -> dict:
    d = dict(row)
    if isinstance(d.get("request_payload"), str):
        try:
            d["request_payload"] = json.loads(d["request_payload"])
        except (json.JSONDecodeError, TypeError):
            d["request_payload"] = {}
    return d
