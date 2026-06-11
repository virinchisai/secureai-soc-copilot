import hashlib

from app.services.storage import UploadStorage


def test_upload_storage_persists_and_deletes_file(tmp_path) -> None:
    storage = UploadStorage(tmp_path / "uploads")
    content = b"failed login src_ip=192.0.2.44"

    stored = storage.save(
        user_id="analyst",
        document_id="document-123",
        filename="../../alerts.log",
        content=content,
    )

    assert stored.path.read_bytes() == content
    assert stored.path.name == "alerts.log"
    assert stored.relative_path == "analyst/document-123/alerts.log"
    assert stored.size_bytes == len(content)
    assert stored.sha256 == hashlib.sha256(content).hexdigest()

    storage.delete_document("analyst", "document-123")
    assert not stored.path.exists()
