"""Background scheduled-task loop for PocketAgent.

Disabled by default in practice: no API inserts rows into scheduled_tasks, so
the loop idles with empty ticks until tasks exist. Schema is created at startup
via ensure_schema without modifying database.py.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any

import aiosqlite

try:
    from ..config import ensure_database_directory, get_settings
    from ..services.ai_agent import AIAgentService
except ImportError:
    from config import ensure_database_directory, get_settings
    from services.ai_agent import AIAgentService

logger = logging.getLogger("pocketagent.scheduler")
if not logger.handlers:
    # Uvicorn does not always surface custom loggers; attach a stderr handler
    # so scheduler ticks are visible in the process logs.
    _handler = logging.StreamHandler()
    _handler.setFormatter(
        logging.Formatter("%(levelname)s:     %(name)s %(message)s")
    )
    logger.addHandler(_handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False


async def ensure_schema(db: aiosqlite.Connection | None = None) -> None:
    """Create scheduled_tasks (+ runs) tables if missing.

    When *db* is None, opens a short-lived connection using the same path
    pattern as database.init_db / get_db.
    """
    if db is not None:
        await _create_scheduled_tasks_schema(db)
        await db.commit()
        return

    settings = get_settings()
    ensure_database_directory(settings.database_path)
    async with aiosqlite.connect(settings.database_path) as conn:
        await _create_scheduled_tasks_schema(conn)
        await conn.commit()


async def _create_scheduled_tasks_schema(db: aiosqlite.Connection) -> None:
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS scheduled_tasks (
            id TEXT PRIMARY KEY,
            agent_id TEXT NOT NULL,
            prompt TEXT NOT NULL,
            interval_seconds INTEGER NOT NULL,
            next_run_at INTEGER NOT NULL,
            enabled INTEGER NOT NULL DEFAULT 1,
            last_result TEXT,
            last_error TEXT,
            last_run_at INTEGER,
            run_count INTEGER NOT NULL DEFAULT 0,
            created_at INTEGER NOT NULL
        )
        """
    )
    await db.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_scheduled_tasks_next_run
        ON scheduled_tasks(enabled, next_run_at)
        """
    )
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS scheduled_task_runs (
            id TEXT PRIMARY KEY,
            task_id TEXT NOT NULL,
            started_at INTEGER NOT NULL,
            finished_at INTEGER,
            relay_count INTEGER DEFAULT 0,
            success INTEGER,
            FOREIGN KEY (task_id) REFERENCES scheduled_tasks(id) ON DELETE CASCADE
        )
        """
    )
    await db.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_task_runs_task
        ON scheduled_task_runs(task_id, started_at DESC)
        """
    )


def _unix_to_iso(ts: int) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


async def _begin_task_run(db: aiosqlite.Connection, task_id: str, started_at: int) -> str | None:
    """Insert a run row. Failures are non-fatal (returns None)."""
    try:
        run_id = uuid.uuid4().hex
        await db.execute(
            """
            INSERT INTO scheduled_task_runs (id, task_id, started_at, finished_at, relay_count, success)
            VALUES (?, ?, ?, NULL, 0, NULL)
            """,
            (run_id, task_id, started_at),
        )
        await db.commit()
        return run_id
    except Exception:
        logger.warning("scheduled_task_runs insert failed task_id=%s", task_id, exc_info=True)
        return None


async def _finish_task_run(
    db: aiosqlite.Connection,
    *,
    run_id: str | None,
    agent_id: str,
    started_at: int,
    success: bool,
) -> None:
    """Update run row with finish time + approximate relay_count. Non-fatal."""
    if not run_id:
        return
    try:
        finished_at = int(time.time())
        # Buffer: relays may flush slightly after the chat call returns.
        window_end = max(finished_at, started_at) + 60
        start_iso = _unix_to_iso(started_at)
        end_iso = _unix_to_iso(window_end)
        relay_count = 0
        try:
            async with db.execute(
                """
                SELECT COUNT(*) AS n
                FROM relay_logs
                WHERE agent_id = ?
                  AND created_at >= ?
                  AND created_at <= ?
                """,
                (agent_id, start_iso, end_iso),
            ) as cursor:
                row = await cursor.fetchone()
            if row is not None:
                relay_count = int(row[0] if not hasattr(row, "keys") else row["n"] or 0)
        except Exception:
            logger.warning(
                "relay_logs count failed run_id=%s agent_id=%s",
                run_id,
                agent_id,
                exc_info=True,
            )
            relay_count = 0

        await db.execute(
            """
            UPDATE scheduled_task_runs
            SET finished_at = ?, relay_count = ?, success = ?
            WHERE id = ?
            """,
            (finished_at, relay_count, 1 if success else 0, run_id),
        )
        await db.commit()
    except Exception:
        logger.warning("scheduled_task_runs finish failed run_id=%s", run_id, exc_info=True)


def _result_to_text(result: Any) -> str:
    """Extract a compact string from AIAgentService.chat() return value."""
    if isinstance(result, dict):
        message = result.get("message")
        if isinstance(message, dict) and message.get("content") is not None:
            return str(message["content"])
        try:
            return json.dumps(result, default=str)
        except (TypeError, ValueError):
            return str(result)
    return str(result)


async def _connect_db() -> aiosqlite.Connection:
    settings = get_settings()
    ensure_database_directory(settings.database_path)
    db = await aiosqlite.connect(settings.database_path)
    await db.execute("PRAGMA foreign_keys = ON;")
    db.row_factory = aiosqlite.Row
    return db


async def scheduler_loop(stop_event: asyncio.Event) -> None:
    """Poll due scheduled_tasks and run them via AIAgentService.chat()."""
    logger.info("scheduler loop started")
    # Ensure table exists even if main wiring order changes.
    try:
        await ensure_schema()
    except Exception:
        logger.exception("scheduler ensure_schema failed at loop start")

    while not stop_event.is_set():
        processed = 0
        try:
            now = int(time.time())
            db = await _connect_db()
            try:
                async with db.execute(
                    """
                    SELECT id, agent_id, prompt, interval_seconds
                    FROM scheduled_tasks
                    WHERE enabled = 1 AND next_run_at <= ?
                    """,
                    (now,),
                ) as cursor:
                    rows = await cursor.fetchall()

                for row in rows:
                    task_id = row["id"]
                    agent_id = row["agent_id"]
                    prompt = row["prompt"]
                    interval_seconds = int(row["interval_seconds"])
                    run_now = int(time.time())
                    next_run = run_now + interval_seconds
                    processed += 1

                    run_id: str | None = None
                    try:
                        run_id = await _begin_task_run(db, task_id, run_now)
                    except Exception:
                        logger.warning(
                            "begin task run failed id=%s (continuing)",
                            task_id,
                            exc_info=True,
                        )
                        run_id = None

                    try:
                        service = AIAgentService()
                        try:
                            result = await service.chat(
                                message=prompt,
                                agent_id=agent_id,
                            )
                        finally:
                            close = getattr(service, "close", None)
                            if close is not None:
                                await close()

                        last_result = _result_to_text(result)[:2000]
                        await db.execute(
                            """
                            UPDATE scheduled_tasks
                            SET last_result = ?,
                                last_error = NULL,
                                last_run_at = ?,
                                next_run_at = ?,
                                run_count = run_count + 1
                            WHERE id = ?
                            """,
                            (last_result, run_now, next_run, task_id),
                        )
                        await _finish_task_run(
                            db,
                            run_id=run_id,
                            agent_id=agent_id,
                            started_at=run_now,
                            success=True,
                        )
                    except Exception as exc:
                        last_error = str(exc)[:1000]
                        await db.execute(
                            """
                            UPDATE scheduled_tasks
                            SET last_error = ?,
                                last_run_at = ?,
                                next_run_at = ?,
                                run_count = run_count + 1
                            WHERE id = ?
                            """,
                            (last_error, run_now, next_run, task_id),
                        )
                        await _finish_task_run(
                            db,
                            run_id=run_id,
                            agent_id=agent_id,
                            started_at=run_now,
                            success=False,
                        )
                        logger.exception(
                            "scheduler task failed id=%s agent_id=%s",
                            task_id,
                            agent_id,
                        )

                await db.commit()
            finally:
                await db.close()

            logger.info("scheduler tick: processed %d task(s)", processed)
        except Exception:
            logger.exception("scheduler loop unexpected error (loop continues)")

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=30)
        except TimeoutError:
            pass
        except asyncio.TimeoutError:
            pass

    logger.info("scheduler loop stopped")
