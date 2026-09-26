"""Small single-node document index using SQLite FTS5."""

from __future__ import annotations

import re
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .settings import settings


def split_chunks(text: str, width: int = 1200, overlap: int = 150) -> list[str]:
    normalized = " ".join(text.split())
    if not normalized:
        return []
    chunks = []
    cursor = 0
    while cursor < len(normalized):
        end = min(len(normalized), cursor + width)
        if end < len(normalized):
            boundary = normalized.rfind(" ", cursor + width // 2, end)
            if boundary > cursor:
                end = boundary
        chunks.append(normalized[cursor:end])
        if end == len(normalized):
            break
        cursor = max(cursor + 1, end - overlap)
    return chunks


class DocumentIndex:
    def __init__(self, path: Path):
        self.path = path

    def connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout=10000")
        connection.execute("PRAGMA journal_mode=WAL")
        return connection

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.execute("CREATE TABLE IF NOT EXISTS documents (id TEXT PRIMARY KEY, name TEXT NOT NULL, created_at TEXT NOT NULL)")
            connection.execute("CREATE VIRTUAL TABLE IF NOT EXISTS chunks USING fts5(document_id UNINDEXED, page UNINDEXED, content)")

    def add_document(self, name: str, pages: list[str]) -> dict:
        document_id = uuid.uuid4().hex
        chunk_count = 0
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO documents VALUES (?, ?, ?)",
                (document_id, name[:200], datetime.now(timezone.utc).isoformat()),
            )
            for page_number, text in enumerate(pages, 1):
                for chunk in split_chunks(text):
                    connection.execute("INSERT INTO chunks (document_id, page, content) VALUES (?, ?, ?)", (document_id, page_number, chunk))
                    chunk_count += 1
        return {"document_id": document_id, "pages": len(pages), "chunks": chunk_count}

    def list_documents(self) -> list[dict]:
        with self.connect() as connection:
            return [dict(row) for row in connection.execute("SELECT * FROM documents ORDER BY created_at DESC")]

    def delete_document(self, document_id: str) -> bool:
        with self.connect() as connection:
            cursor = connection.execute("DELETE FROM documents WHERE id = ?", (document_id,))
            connection.execute("DELETE FROM chunks WHERE document_id = ?", (document_id,))
            return cursor.rowcount > 0

    def search(self, query: str, limit: int = 5) -> list[dict]:
        tokens = re.findall(r"[\w]+", query.lower(), flags=re.UNICODE)[:12]
        if not tokens:
            return []
        fts_query = " OR ".join('"' + token.replace('"', '') + '"' for token in tokens)
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT chunks.document_id, documents.name, chunks.page, chunks.content, bm25(chunks) AS rank "
                "FROM chunks JOIN documents ON documents.id = chunks.document_id "
                "WHERE chunks MATCH ? ORDER BY rank LIMIT ?",
                (fts_query, max(1, min(limit, 10))),
            ).fetchall()
        return [dict(row) for row in rows]


index = DocumentIndex(settings.data_dir / "documents.db")
