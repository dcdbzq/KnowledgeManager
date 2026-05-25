from contextlib import contextmanager
import json
import os
import sqlite3
import uuid
from collections.abc import Iterator
from datetime import date

from ..models import KnowledgeMetadata, KnowledgeRecord, now_iso


class DocumentStore:
    def __init__(self, db_path: str):
        self.db_path = db_path
        directory = os.path.dirname(db_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        self._init_db()

    def add(self, text: str, metadata: KnowledgeMetadata, logical_id: str | None = None) -> KnowledgeRecord:
        logical_id = logical_id or str(uuid.uuid4())
        version = self._next_version(logical_id)
        record_id = f"{logical_id}:v{version}"
        now = now_iso()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO knowledge_documents
                (id, logical_id, version, text, metadata_json, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, 'active', ?, ?)
                """,
                (record_id, logical_id, version, text, json.dumps(metadata.to_dict(), ensure_ascii=False), now, now),
            )
        return KnowledgeRecord(record_id, logical_id, version, text, metadata, "active", now, now)

    def update(self, logical_id: str, text: str, metadata: KnowledgeMetadata) -> KnowledgeRecord:
        return self.add(text=text, metadata=metadata, logical_id=logical_id)

    def delete(self, logical_id: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE knowledge_documents SET status = 'deleted', updated_at = ? WHERE logical_id = ?",
                (now_iso(), logical_id),
            )

    def get(self, record_id: str) -> KnowledgeRecord | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM knowledge_documents WHERE id = ?", (record_id,)).fetchone()
        return self._row_to_record(row) if row else None

    def list_active(self, include_expired: bool = False) -> list[KnowledgeRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT d.* FROM knowledge_documents d
                JOIN (
                    SELECT logical_id, MAX(version) AS max_version
                    FROM knowledge_documents
                    WHERE status = 'active'
                    GROUP BY logical_id
                ) latest
                ON d.logical_id = latest.logical_id AND d.version = latest.max_version
                WHERE d.status = 'active'
                ORDER BY d.updated_at DESC
                """
            ).fetchall()
        records = [self._row_to_record(row) for row in rows]
        if include_expired:
            return records
        return [record for record in records if not self._is_expired(record)]

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS knowledge_documents (
                    id TEXT PRIMARY KEY,
                    logical_id TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    text TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_kd_logical ON knowledge_documents(logical_id, version)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_kd_status ON knowledge_documents(status)")

    def _next_version(self, logical_id: str) -> int:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COALESCE(MAX(version), 0) + 1 AS next_version FROM knowledge_documents WHERE logical_id = ?",
                (logical_id,),
            ).fetchone()
        return int(row["next_version"])

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _row_to_record(self, row: sqlite3.Row) -> KnowledgeRecord:
        metadata = KnowledgeMetadata.from_dict(json.loads(row["metadata_json"]))
        return KnowledgeRecord(
            id=row["id"],
            logical_id=row["logical_id"],
            version=int(row["version"]),
            text=row["text"],
            metadata=metadata,
            status=row["status"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def _is_expired(self, record: KnowledgeRecord) -> bool:
        expire_at = record.metadata.expire_at
        if not expire_at:
            return False
        try:
            return date.fromisoformat(expire_at) < date.today()
        except ValueError:
            return False
