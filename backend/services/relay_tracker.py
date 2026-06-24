from datetime import datetime, timedelta, timezone
from typing import Any

import aiosqlite

try:
    from ..config import ensure_database_directory, get_settings
    from ..database import create_relay_log
except ImportError:
    from config import ensure_database_directory, get_settings
    from database import create_relay_log


class RelayTrackerService:
    """Track Pocket RPC relay usage and provide analytics."""

    def __init__(self) -> None:
        self.settings = get_settings()

    async def _connect(self) -> aiosqlite.Connection:
        ensure_database_directory(self.settings.database_path)
        db = await aiosqlite.connect(self.settings.database_path)
        db.row_factory = aiosqlite.Row
        return db

    async def log_relay(
        self,
        chain: str,
        method: str,
        request_payload: dict[str, Any] | None,
        response_status: int,
        latency_ms: int,
        relay_cost_pokt: float | None = None,
        agent_id: str | None = None,
    ) -> dict[str, Any]:
        db = await self._connect()
        try:
            return await create_relay_log(
                db=db,
                agent_id=agent_id,
                chain=chain,
                method=method,
                request_payload=request_payload or {},
                response_status=response_status,
                latency_ms=latency_ms,
                relay_cost_pokt=(
                    relay_cost_pokt
                    if relay_cost_pokt is not None
                    else self.settings.notional_pokt_per_relay
                ),
            )
        finally:
            await db.close()

    @staticmethod
    def _time_cutoff(timeframe: str) -> str | None:
        now = datetime.now(timezone.utc)
        if timeframe == "day":
            return (now - timedelta(days=1)).isoformat()
        if timeframe == "week":
            return (now - timedelta(days=7)).isoformat()
        return None

    async def get_relay_stats(self, agent_id: str | None = None, timeframe: str = "all") -> dict[str, Any]:
        cutoff = self._time_cutoff(timeframe)
        where = []
        params: list[Any] = []
        if agent_id:
            where.append("agent_id = ?")
            params.append(agent_id)
        if cutoff:
            where.append("created_at >= ?")
            params.append(cutoff)
        where_sql = f"WHERE {' AND '.join(where)}" if where else ""
        query = f"""
            SELECT
                COUNT(*) AS total_relays,
                COALESCE(AVG(latency_ms), 0) AS avg_latency_ms,
                COALESCE(SUM(relay_cost_pokt), 0) AS total_pokt_cost
            FROM relay_logs
            {where_sql}
        """
        db = await self._connect()
        try:
            async with db.execute(query, params) as cursor:
                row = await cursor.fetchone()
        finally:
            await db.close()
        return {
            "total_relays": int(row["total_relays"] or 0),
            "avg_latency_ms": round(float(row["avg_latency_ms"] or 0.0), 2),
            "total_pokt_cost": round(float(row["total_pokt_cost"] or 0.0), 6),
            "timeframe": timeframe,
        }

    async def get_chain_stats(self, agent_id: str | None = None, timeframe: str = "all") -> list[dict[str, Any]]:
        cutoff = self._time_cutoff(timeframe)
        where = []
        params: list[Any] = []
        if agent_id:
            where.append("agent_id = ?")
            params.append(agent_id)
        if cutoff:
            where.append("created_at >= ?")
            params.append(cutoff)
        where_sql = f"WHERE {' AND '.join(where)}" if where else ""
        query = f"""
            SELECT
                chain,
                COUNT(*) AS relays,
                COALESCE(AVG(latency_ms), 0) AS avg_latency_ms,
                COALESCE(SUM(relay_cost_pokt), 0) AS pokt_cost
            FROM relay_logs
            {where_sql}
            GROUP BY chain
            ORDER BY relays DESC
        """
        db = await self._connect()
        try:
            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
        finally:
            await db.close()
        return [
            {
                "chain": row["chain"],
                "relays": int(row["relays"] or 0),
                "avg_latency_ms": round(float(row["avg_latency_ms"] or 0.0), 2),
                "pokt_cost": round(float(row["pokt_cost"] or 0.0), 6),
            }
            for row in rows
        ]

    async def get_success_rate(
        self, agent_id: str | None = None, timeframe: str = "all"
    ) -> dict[str, Any]:
        """Success rate from response_status (2xx == success).

        Success rate is the share of relay_logs whose upstream HTTP status is
        2xx. Empty tables report a perfect rate (1.0) — no relays means no
        failures, and the dashboard shows "100%" rather than a misleading 0%.
        """
        cutoff = self._time_cutoff(timeframe)
        where = []
        params: list[Any] = []
        if agent_id:
            where.append("agent_id = ?")
            params.append(agent_id)
        if cutoff:
            where.append("created_at >= ?")
            params.append(cutoff)
        where_sql = f"WHERE {' AND '.join(where)}" if where else ""
        query = f"""
            SELECT
                SUM(CASE WHEN response_status BETWEEN 200 AND 299 THEN 1 ELSE 0 END) AS successful,
                SUM(CASE WHEN response_status BETWEEN 200 AND 299 THEN 0 ELSE 1 END) AS failed,
                COUNT(*) AS total
            FROM relay_logs
            {where_sql}
        """
        db = await self._connect()
        try:
            async with db.execute(query, params) as cursor:
                row = await cursor.fetchone()
        finally:
            await db.close()
        successful = int(row["successful"] or 0)
        failed = int(row["failed"] or 0)
        total = int(row["total"] or 0)
        return {
            "successful": successful,
            "failed": failed,
            "total": total,
            "success_rate": round(successful / total, 4) if total else 1.0,
        }

    async def get_daily_usage(self, agent_id: str | None = None, days: int = 14) -> list[dict[str, Any]]:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        where = ["created_at >= ?"]
        params: list[Any] = [cutoff]
        if agent_id:
            where.append("agent_id = ?")
            params.append(agent_id)
        where_sql = f"WHERE {' AND '.join(where)}"
        query = f"""
            SELECT
                substr(created_at, 1, 10) AS date,
                COUNT(*) AS relays,
                COALESCE(SUM(relay_cost_pokt), 0) AS pokt_cost
            FROM relay_logs
            {where_sql}
            GROUP BY substr(created_at, 1, 10)
            ORDER BY date DESC
        """
        db = await self._connect()
        try:
            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
        finally:
            await db.close()
        return [
            {"date": row["date"], "relays": int(row["relays"] or 0), "pokt_cost": round(float(row["pokt_cost"] or 0), 6)}
            for row in rows
        ]
