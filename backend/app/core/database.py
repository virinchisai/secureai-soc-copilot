import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    chunk_count INTEGER NOT NULL,
                    size_bytes INTEGER NOT NULL DEFAULT 0,
                    sha256 TEXT NOT NULL DEFAULT '',
                    stored_path TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_documents_user
                ON documents(user_id, created_at DESC);

                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    question TEXT NOT NULL,
                    status TEXT NOT NULL,
                    source_count INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_audit_user
                ON audit_logs(user_id, created_at DESC);
                """
            )
            self._add_column_if_missing(
                connection,
                "documents",
                "size_bytes",
                "INTEGER NOT NULL DEFAULT 0",
            )
            self._add_column_if_missing(
                connection,
                "documents",
                "sha256",
                "TEXT NOT NULL DEFAULT ''",
            )
            self._add_column_if_missing(
                connection,
                "documents",
                "stored_path",
                "TEXT NOT NULL DEFAULT ''",
            )

    @staticmethod
    def _add_column_if_missing(
        connection: sqlite3.Connection,
        table: str,
        column: str,
        definition: str,
    ) -> None:
        existing_columns = {
            row["name"]
            for row in connection.execute(f"PRAGMA table_info({table})").fetchall()
        }
        if column not in existing_columns:
            connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def add_document(
        self,
        document_id: str,
        user_id: str,
        filename: str,
        chunk_count: int,
        size_bytes: int,
        sha256: str,
        stored_path: str,
    ) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO documents (
                    id, user_id, filename, chunk_count, size_bytes, sha256,
                    stored_path, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    document_id,
                    user_id,
                    filename,
                    chunk_count,
                    size_bytes,
                    sha256,
                    stored_path,
                    utc_now(),
                ),
            )

    def list_documents(self, user_id: str) -> list[dict]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT id, filename, chunk_count, size_bytes, sha256, created_at
                FROM documents
                WHERE user_id = ?
                ORDER BY created_at DESC
                """,
                (user_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def add_audit_log(
        self,
        user_id: str,
        question: str,
        status: str,
        source_count: int = 0,
    ) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO audit_logs
                    (user_id, question, status, source_count, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, question, status, source_count, utc_now()),
            )

    def list_audit_logs(self, user_id: str, limit: int = 100) -> list[dict]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT id, question, status, source_count, created_at
                FROM audit_logs
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()
        return [dict(row) for row in rows]
