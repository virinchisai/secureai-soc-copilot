from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import chat
from app.core.database import Database
from app.dependencies import get_current_user


class FakeRAGService:
    def answer(self, user_id: str, question: str) -> tuple:
        assert user_id == "analyst"
        assert question == "Which IP failed login?"
        return (
            "The source IP was 192.0.2.44 [S1].",
            [
                {
                    "citation": "S1",
                    "document_id": "auth-doc",
                    "filename": "auth.log",
                    "page": None,
                    "chunk": 1,
                    "snippet": "failed login from 192.0.2.44",
                    "score": 0.1,
                }
            ],
            "anthropic",
            "test-claude",
        )


def test_chat_endpoint_returns_sources_and_writes_audit_log(tmp_path) -> None:
    database = Database(tmp_path / "test.db")
    database.initialize()

    app = FastAPI()
    app.include_router(chat.router, prefix="/api")
    app.state.database = database
    app.state.rag_service = FakeRAGService()
    app.dependency_overrides[get_current_user] = lambda: "analyst"

    with TestClient(app) as client:
        response = client.post(
            "/api/chat/ask",
            json={"question": "Which IP failed login?"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["answer"] == "The source IP was 192.0.2.44 [S1]."
    assert payload["sources"][0]["filename"] == "auth.log"
    assert payload["provider"] == "anthropic"
    assert payload["model"] == "test-claude"

    audit_logs = database.list_audit_logs("analyst")
    assert audit_logs[0]["status"] == "answered"
    assert audit_logs[0]["source_count"] == 1
    assert audit_logs[0]["username"] == "analyst"
    assert audit_logs[0]["uploaded_files"] == ["auth.log"]
    assert audit_logs[0]["response_summary"] == (
        "The source IP was 192.0.2.44 [S1]."
    )
