"""Durable, single-worker queue for GitHub PR review events."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone

from .settings import settings


class PRJobs:
    def __init__(self, path):
        self.path = path

    def connect(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout=10000")
        connection.execute("PRAGMA journal_mode=WAL")
        return connection

    def initialize(self):
        with self.connect() as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS jobs (delivery_id TEXT PRIMARY KEY, repository TEXT NOT NULL, "
                "pull_number INTEGER NOT NULL, status TEXT NOT NULL, updated_at TEXT NOT NULL, result TEXT, error TEXT)"
            )

    def enqueue(self, delivery_id: str, repository: str, pull_number: int) -> bool:
        with self.connect() as connection:
            cursor = connection.execute(
                "INSERT OR IGNORE INTO jobs (delivery_id, repository, pull_number, status, updated_at) VALUES (?, ?, ?, 'pending', ?)",
                (delivery_id, repository, pull_number, datetime.now(timezone.utc).isoformat()),
            )
            return cursor.rowcount > 0

    def claim(self) -> dict | None:
        now = datetime.now(timezone.utc)
        stale = (now - timedelta(minutes=10)).isoformat()
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("UPDATE jobs SET status='pending' WHERE status='running' AND updated_at < ?", (stale,))
            row = connection.execute("SELECT * FROM jobs WHERE status='pending' ORDER BY updated_at LIMIT 1").fetchone()
            if row:
                connection.execute("UPDATE jobs SET status='running', updated_at=? WHERE delivery_id=?", (now.isoformat(), row["delivery_id"]))
        return dict(row) if row else None

    def finish(self, delivery_id: str, result: dict | None = None, error: str | None = None):
        with self.connect() as connection:
            connection.execute(
                "UPDATE jobs SET status=?, updated_at=?, result=?, error=? WHERE delivery_id=?",
                ("failed" if error else "completed", datetime.now(timezone.utc).isoformat(), json.dumps(result) if result else None, error, delivery_id),
            )

    def get(self, delivery_id: str) -> dict | None:
        with self.connect() as connection:
            row = connection.execute("SELECT * FROM jobs WHERE delivery_id=?", (delivery_id,)).fetchone()
        if not row:
            return None
        data = dict(row)
        if data["result"]:
            data["result"] = json.loads(data["result"])
        return data


jobs = PRJobs(settings.data_dir / "pr_jobs.db")
