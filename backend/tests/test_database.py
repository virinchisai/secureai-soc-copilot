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
