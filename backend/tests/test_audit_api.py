import csv
import io

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import audit
from app.core.database import Database
from app.dependencies import get_current_user


def test_audit_export_returns_csv_for_current_user(tmp_path) -> None:
    database = Database(tmp_path / "audit.db")
    database.initialize()
    database.add_audit_log(
        user_id="analyst",
        question="Which host was isolated?",
        status="answered",
        source_count=1,
        uploaded_files=["incident.log"],
        response_summary="Host web-01 was isolated.",
    )
    database.add_audit_log(
        user_id="other-user",
        question="Private question",
        status="answered",
        source_count=1,
        uploaded_files=["private.log"],
        response_summary="Private answer.",
    )

    app = FastAPI()
    app.include_router(audit.router, prefix="/api")
    app.state.database = database
    app.dependency_overrides[get_current_user] = lambda: "analyst"

    with TestClient(app) as client:
        response = client.get("/api/audit/export")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    rows = list(csv.DictReader(io.StringIO(response.text)))
    assert len(rows) == 1
    assert rows[0]["username"] == "analyst"
    assert rows[0]["uploaded_files"] == "incident.log"
    assert rows[0]["question"] == "Which host was isolated?"
