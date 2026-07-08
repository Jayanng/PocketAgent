"""REST API for scheduled tasks (agent-scoped via X-Agent-Access-Token)."""

from __future__ import annotations

import time
import uuid
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel, Field

try:
    from ..database import get_agent, get_db
    from ..services.agent_auth import verify_agent_access_token
except ImportError:
    from database import get_agent, get_db
    from services.agent_auth import verify_agent_access_token

router = APIRouter(prefix="/api/scheduled-tasks", tags=["scheduled-tasks"])


class ScheduledTaskCreate(BaseModel):
    agent_id: str
    prompt: str = Field(..., min_length=1, max_length=2000)
    interval_seconds: int = Field(..., ge=60, le=604800)


class ScheduledTaskUpdate(BaseModel):
    enabled: bool | None = None
    interval_seconds: int | None = Field(default=None, ge=60, le=604800)
    prompt: str | None = Field(default=None, min_length=1, max_length=2000)


class ScheduledTaskResponse(BaseModel):
    id: str
    agent_id: str
    prompt: str
    interval_seconds: int
    next_run_at: int
    enabled: int
    last_result: str | None = None
    last_error: str | None = None
    last_run_at: int | None = None
    run_count: int
    created_at: int


class ScheduledTaskRunStats(BaseModel):
    started_at: int
    finished_at: int | None = None
    relay_count: int
    success: bool | None = None


class ScheduledTaskRelayStatsResponse(BaseModel):
    total_relays_last_10_runs: int
    avg_relays_per_run: float
    runs: list[ScheduledTaskRunStats]


def _require_agent_access(agent: dict[str, Any], access_token: str | None) -> None:
    if not verify_agent_access_token(agent, access_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Valid X-Agent-Access-Token header is required for this agent.",
        )


async def _load_agent_for_access(
    db: Any,
    agent_id: str,
    access_token: str | None,
    *,
    require_active: bool = True,
) -> dict[str, Any]:
    agent = await get_agent(db, agent_id)
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    if require_active and not agent.get("is_active", True):
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Agent is inactive")
    _require_agent_access(agent, access_token)
    return agent


def _row_to_task(row: Any) -> dict[str, Any]:
    d = dict(row)
    # Normalize sqlite Row / mapping to plain ints where present.
    for key in ("interval_seconds", "next_run_at", "enabled", "run_count", "created_at"):
        if d.get(key) is not None:
            d[key] = int(d[key])
    if d.get("last_run_at") is not None:
        d["last_run_at"] = int(d["last_run_at"])
    return d


async def _get_task_row(db: Any, task_id: str) -> dict[str, Any] | None:
    async with db.execute(
        "SELECT * FROM scheduled_tasks WHERE id = ?",
        (task_id,),
    ) as cursor:
        row = await cursor.fetchone()
    if row is None:
        return None
    return _row_to_task(row)


@router.post("", response_model=ScheduledTaskResponse, status_code=status.HTTP_201_CREATED)
async def create_scheduled_task(
    body: ScheduledTaskCreate,
    access_token: str | None = Header(None, alias="X-Agent-Access-Token"),
    db=Depends(get_db),
) -> dict[str, Any]:
    await _load_agent_for_access(db, body.agent_id, access_token)

    task_id = uuid.uuid4().hex
    now = int(time.time())
    next_run_at = now + body.interval_seconds

    await db.execute(
        """
        INSERT INTO scheduled_tasks (
            id, agent_id, prompt, interval_seconds, next_run_at,
            enabled, last_result, last_error, last_run_at, run_count, created_at
        ) VALUES (?, ?, ?, ?, ?, 1, NULL, NULL, NULL, 0, ?)
        """,
        (
            task_id,
            body.agent_id,
            body.prompt,
            body.interval_seconds,
            next_run_at,
            now,
        ),
    )
    await db.commit()

    task = await _get_task_row(db, task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Scheduled task was not persisted",
        )
    return task


@router.get("", response_model=list[ScheduledTaskResponse])
async def list_scheduled_tasks(
    agent_id: str = Query(..., description="Required. Scope tasks to this agent."),
    access_token: str | None = Header(None, alias="X-Agent-Access-Token"),
    db=Depends(get_db),
) -> list[dict[str, Any]]:
    """List tasks for one agent. agent_id is required (ownership = agent access token)."""
    await _load_agent_for_access(db, agent_id, access_token)

    async with db.execute(
        """
        SELECT * FROM scheduled_tasks
        WHERE agent_id = ?
        ORDER BY created_at DESC
        """,
        (agent_id,),
    ) as cursor:
        rows = await cursor.fetchall()
    return [_row_to_task(r) for r in rows]


@router.get("/{task_id}/relay-stats", response_model=ScheduledTaskRelayStatsResponse)
async def get_scheduled_task_relay_stats(
    task_id: str,
    access_token: str | None = Header(None, alias="X-Agent-Access-Token"),
    db=Depends(get_db),
) -> dict[str, Any]:
    """Approximate Pocket relay counts for the last 10 runs of this task.

    Counts use agent_id + time window against relay_logs (Option A). Existing
    pocket_rpc logging often leaves agent_id NULL, so counts may be zero until
    that path is improved — this endpoint never changes core RPC code.
    """
    task = await _get_task_row(db, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scheduled task not found")

    try:
        await _load_agent_for_access(db, task["agent_id"], access_token, require_active=False)
    except HTTPException as exc:
        if exc.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Scheduled task not found",
            ) from exc
        raise

    async with db.execute(
        """
        SELECT started_at, finished_at, relay_count, success
        FROM scheduled_task_runs
        WHERE task_id = ?
        ORDER BY started_at DESC
        LIMIT 10
        """,
        (task_id,),
    ) as cursor:
        rows = await cursor.fetchall()

    runs: list[dict[str, Any]] = []
    total = 0
    for row in rows:
        d = dict(row)
        relay_count = int(d.get("relay_count") or 0)
        total += relay_count
        success_raw = d.get("success")
        success: bool | None
        if success_raw is None:
            success = None
        else:
            success = bool(int(success_raw))
        finished = d.get("finished_at")
        runs.append(
            {
                "started_at": int(d["started_at"]),
                "finished_at": int(finished) if finished is not None else None,
                "relay_count": relay_count,
                "success": success,
            }
        )

    n = len(runs)
    avg = round(total / n, 2) if n else 0.0
    return {
        "total_relays_last_10_runs": total,
        "avg_relays_per_run": avg,
        "runs": runs,
    }


@router.get("/{task_id}", response_model=ScheduledTaskResponse)
async def get_scheduled_task(
    task_id: str,
    access_token: str | None = Header(None, alias="X-Agent-Access-Token"),
    db=Depends(get_db),
) -> dict[str, Any]:
    task = await _get_task_row(db, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scheduled task not found")

    try:
        await _load_agent_for_access(db, task["agent_id"], access_token, require_active=False)
    except HTTPException as exc:
        if exc.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Scheduled task not found",
            ) from exc
        raise

    return task


@router.patch("/{task_id}", response_model=ScheduledTaskResponse)
async def update_scheduled_task(
    task_id: str,
    body: ScheduledTaskUpdate,
    access_token: str | None = Header(None, alias="X-Agent-Access-Token"),
    db=Depends(get_db),
) -> dict[str, Any]:
    task = await _get_task_row(db, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scheduled task not found")

    try:
        await _load_agent_for_access(db, task["agent_id"], access_token)
    except HTTPException as exc:
        if exc.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Scheduled task not found",
            ) from exc
        raise

    updates = body.model_dump(exclude_unset=True)
    if not updates:
        return task

    set_parts: list[str] = []
    values: list[Any] = []

    if "enabled" in updates and updates["enabled"] is not None:
        set_parts.append("enabled = ?")
        values.append(1 if updates["enabled"] else 0)

    if "prompt" in updates and updates["prompt"] is not None:
        set_parts.append("prompt = ?")
        values.append(updates["prompt"])

    if "interval_seconds" in updates and updates["interval_seconds"] is not None:
        new_interval = int(updates["interval_seconds"])
        set_parts.append("interval_seconds = ?")
        values.append(new_interval)
        set_parts.append("next_run_at = ?")
        values.append(int(time.time()) + new_interval)

    if not set_parts:
        return task

    values.append(task_id)
    await db.execute(
        f"UPDATE scheduled_tasks SET {', '.join(set_parts)} WHERE id = ?",
        tuple(values),
    )
    await db.commit()

    updated = await _get_task_row(db, task_id)
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scheduled task not found")
    return updated


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_scheduled_task(
    task_id: str,
    access_token: str | None = Header(None, alias="X-Agent-Access-Token"),
    db=Depends(get_db),
) -> None:
    task = await _get_task_row(db, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scheduled task not found")

    try:
        await _load_agent_for_access(db, task["agent_id"], access_token)
    except HTTPException as exc:
        if exc.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Scheduled task not found",
            ) from exc
        raise

    cursor = await db.execute(
        "DELETE FROM scheduled_tasks WHERE id = ?",
        (task_id,),
    )
    await db.commit()
    if cursor.rowcount == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scheduled task not found")
