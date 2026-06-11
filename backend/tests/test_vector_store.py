import hashlib

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from app.services.vector_store import VectorStoreService


class DeterministicEmbeddings(Embeddings):
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)

    @staticmethod
    def _embed(text: str) -> list[float]:
        digest = hashlib.sha256(text.encode()).digest()
        return [byte / 255 for byte in digest[:16]]


def test_faiss_index_persists_and_reloads(tmp_path) -> None:
    root_dir = tmp_path / "faiss"
    embeddings = DeterministicEmbeddings()
    service = VectorStoreService(root_dir=root_dir, embeddings=embeddings)
    documents = [
        Document(
            page_content="failed login from 192.0.2.44",
            metadata={
                "document_id": "doc-1",
                "filename": "alerts.log",
                "page": None,
                "chunk": 1,
            },
        )
    ]

    service.add_documents("analyst", documents, ["doc-1:1"])

    assert service.index_size("analyst") == 1
    assert (root_dir / "analyst" / "index.faiss").is_file()
    assert (root_dir / "analyst" / "index.pkl").is_file()

    reloaded = VectorStoreService(root_dir=root_dir, embeddings=embeddings)
    results = reloaded.search("analyst", "failed login", k=1)

    assert reloaded.index_size("analyst") == 1
    assert results[0][0].metadata["document_id"] == "doc-1"
    assert results[0][0].page_content == "failed login from 192.0.2.44"
