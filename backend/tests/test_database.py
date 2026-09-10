import sqlite3

from app.core.database import Database


def test_initialize_migrates_existing_audit_table(tmp_path) -> None:
    path = tmp_path / "legacy.db"
    connection = sqlite3.connect(path)
    connection.execute(
        """
        CREATE TABLE audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            question TEXT NOT NULL,
            status TEXT NOT NULL,
            source_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        )
        """
    )
    connection.commit()
    connection.close()

    database = Database(path)
    database.initialize()
    database.add_audit_log(
        user_id="analyst",
        question="What happened?",
        status="answered",
        uploaded_files=["incident.log"],
        response_summary="A login was followed by privilege escalation.",
    )

    record = database.list_audit_logs("analyst")[0]
    assert record["username"] == "analyst"
    assert record["uploaded_files"] == ["incident.log"]
    assert record["response_summary"].startswith("A login")


def test_document_stats_are_scoped_to_user(tmp_path) -> None:
    database = Database(tmp_path / "stats.db")
    database.initialize()
    database.add_document(
        document_id="doc-1",
        user_id="analyst",
        filename="one.log",
        chunk_count=3,
        size_bytes=120,
        sha256="one",
        stored_path="analyst/doc-1/one.log",
    )
    database.add_document(
        document_id="doc-2",
        user_id="analyst",
        filename="two.log",
        chunk_count=4,
        size_bytes=80,
        sha256="two",
        stored_path="analyst/doc-2/two.log",
    )
    database.add_document(
        document_id="other",
        user_id="other-user",
        filename="private.log",
        chunk_count=99,
        size_bytes=999,
        sha256="other",
        stored_path="other-user/other/private.log",
    )

    assert database.document_stats("analyst") == {
        "total_documents": 2,
        "total_chunks": 7,
        "total_bytes": 200,
    }
