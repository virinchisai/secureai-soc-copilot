from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import system
from app.core.config import Settings, get_settings
from app.core.database import Database
from app.dependencies import get_current_user


def test_system_status_returns_version_providers_and_document_stats(tmp_path) -> None:
    settings = Settings(
        jwt_secret_key="test-secret-that-is-long-enough",
        data_dir=tmp_path,
        embedding_provider="ollama",
        llm_provider="ollama",
        ollama_embedding_model="nomic-embed-text",
        ollama_chat_model="deepseek-r1:1.5b",
    )
    database = Database(settings.database_path)
    database.initialize()
    database.add_document(
        document_id="doc-1",
        user_id="analyst",
        filename="incident.log",
        chunk_count=5,
        size_bytes=512,
        sha256="checksum",
        stored_path="analyst/doc-1/incident.log",
    )

    app = FastAPI()
    app.include_router(system.router, prefix=settings.api_prefix)
    app.state.database = database
    app.dependency_overrides[get_current_user] = lambda: "analyst"
    app.dependency_overrides[get_settings] = lambda: settings

    with TestClient(app) as client:
        response = client.get("/api/system/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["version"] == "2.0.0"
    assert payload["username"] == "analyst"
    assert payload["embedding_model"] == "nomic-embed-text"
    assert payload["llm_model"] == "deepseek-r1:1.5b"
    assert payload["document_stats"] == {
        "total_documents": 1,
        "total_chunks": 5,
        "total_bytes": 512,
    }
