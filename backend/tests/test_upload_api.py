import hashlib
import io

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from langchain_core.embeddings import Embeddings
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from app.api import documents
from app.core.config import Settings, get_settings
from app.core.database import Database
from app.dependencies import get_current_user
from app.services.rag import RAGService
from app.services.storage import UploadStorage


class DeterministicEmbeddings(Embeddings):
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)

    @staticmethod
    def _embed(text: str) -> list[float]:
        digest = hashlib.sha256(text.encode()).digest()
        return [byte / 255 for byte in digest[:16]]


@pytest.mark.parametrize(
    ("filename", "content"),
    [
        ("events.txt", b"malware detected on host web-01"),
        ("auth.log", b"failed login from 192.0.2.44"),
        ("incident.pdf", None),
    ],
)
def test_upload_persists_file_and_faiss_index(
    tmp_path,
    filename: str,
    content: bytes | None,
) -> None:
    if content is None:
        content = _pdf_with_text("PDF incident on host db-01")

    settings = Settings(
        jwt_secret_key="test-secret-that-is-long-enough",
        openai_api_key="test-key",
        data_dir=tmp_path,
        chunk_size=20,
        chunk_overlap=5,
    )
    database = Database(settings.database_path)
    database.initialize()

    app = FastAPI()
    app.include_router(documents.router, prefix=settings.api_prefix)
    app.state.database = database
    app.state.rag_service = RAGService(
        settings,
        embeddings=DeterministicEmbeddings(),
        chat_model=object(),
    )
    app.state.upload_storage = UploadStorage(settings.uploads_dir)
    app.dependency_overrides[get_current_user] = lambda: "analyst"
    app.dependency_overrides[get_settings] = lambda: settings

    with TestClient(app) as client:
        response = client.post(
            "/api/documents/upload",
            files={"file": (filename, content, "application/octet-stream")},
        )

    assert response.status_code == 201, response.text
    payload = response.json()["document"]
    stored_file = settings.uploads_dir / "analyst" / payload["id"] / filename

    assert stored_file.read_bytes() == content
    assert payload["size_bytes"] == len(content)
    assert payload["sha256"] == hashlib.sha256(content).hexdigest()
    assert payload["chunk_count"] > 1
    assert (settings.faiss_dir / "analyst" / "index.faiss").is_file()
    assert (settings.faiss_dir / "analyst" / "index.pkl").is_file()
    assert (
        app.state.rag_service.vector_store.index_size("analyst")
        == payload["chunk_count"]
    )


def test_delete_removes_file_vectors_and_metadata(tmp_path) -> None:
    settings = Settings(
        jwt_secret_key="test-secret-that-is-long-enough",
        data_dir=tmp_path,
        chunk_size=20,
        chunk_overlap=5,
    )
    database = Database(settings.database_path)
    database.initialize()

    app = FastAPI()
    app.include_router(documents.router, prefix=settings.api_prefix)
    app.state.database = database
    app.state.rag_service = RAGService(
        settings,
        embeddings=DeterministicEmbeddings(),
        chat_model=object(),
    )
    app.state.upload_storage = UploadStorage(settings.uploads_dir)
    app.dependency_overrides[get_current_user] = lambda: "analyst"
    app.dependency_overrides[get_settings] = lambda: settings

    with TestClient(app) as client:
        upload = client.post(
            "/api/documents/upload",
            files={
                "file": (
                    "delete-me.log",
                    b"failed login followed by privilege escalation",
                    "text/plain",
                )
            },
        )
        assert upload.status_code == 201, upload.text
        document = upload.json()["document"]
        stored_file = (
            settings.uploads_dir
            / "analyst"
            / document["id"]
            / "delete-me.log"
        )
        assert stored_file.is_file()

        response = client.delete(f"/api/documents/{document['id']}")

    assert response.status_code == 200, response.text
    assert response.json()["filename"] == "delete-me.log"
    assert not stored_file.exists()
    assert database.list_documents("analyst") == []
    assert app.state.rag_service.vector_store.index_size("analyst") == 0


def test_delete_does_not_expose_another_users_document(tmp_path) -> None:
    database = Database(tmp_path / "test.db")
    database.initialize()
    database.add_document(
        document_id="other-document",
        user_id="other-user",
        filename="private.log",
        chunk_count=1,
        size_bytes=10,
        sha256="checksum",
        stored_path="other-user/other-document/private.log",
    )

    app = FastAPI()
    app.include_router(documents.router, prefix="/api")
    app.state.database = database
    app.state.rag_service = object()
    app.state.upload_storage = UploadStorage(tmp_path / "uploads")
    app.dependency_overrides[get_current_user] = lambda: "analyst"

    with TestClient(app) as client:
        response = client.delete("/api/documents/other-document")

    assert response.status_code == 404
    assert database.get_document("other-document", "other-user") is not None


def _pdf_with_text(text: str) -> bytes:
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    page[NameObject("/Resources")] = DictionaryObject(
        {
            NameObject("/Font"): DictionaryObject(
                {NameObject("/F1"): writer._add_object(font)}
            )
        }
    )
    stream = DecodedStreamObject()
    stream.set_data(f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode())
    page[NameObject("/Contents")] = writer._add_object(stream)
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()
