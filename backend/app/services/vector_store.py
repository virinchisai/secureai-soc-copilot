from pathlib import Path
from threading import Lock

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_openai import OpenAIEmbeddings


class VectorStoreService:
    def __init__(
        self,
        root_dir: Path,
        api_key: str = "",
        embedding_model: str = "text-embedding-3-small",
        embeddings: Embeddings | None = None,
    ) -> None:
        self.root_dir = root_dir
        self.embeddings = embeddings or OpenAIEmbeddings(
            api_key=api_key, model=embedding_model
        )
        self._stores: dict[str, FAISS] = {}
        self._lock = Lock()
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def add_documents(
        self,
        user_id: str,
        documents: list[Document],
        ids: list[str],
    ) -> None:
        if len(documents) != len(ids):
            raise ValueError("Each document chunk must have a vector ID")
        with self._lock:
            store = self._get_store(user_id)
            if store is None:
                store = FAISS.from_documents(documents, self.embeddings, ids=ids)
            else:
                store.add_documents(documents, ids=ids)
            store.save_local(self._user_path(user_id))
            self._stores[user_id] = store

    def delete(self, user_id: str, ids: list[str]) -> None:
        if not ids:
            return
        with self._lock:
            store = self._get_store(user_id)
            if store is None:
                return
            store.delete(ids)
            store.save_local(self._user_path(user_id))

    def search(
        self,
        user_id: str,
        query: str,
        k: int,
    ) -> list[tuple[Document, float]]:
        with self._lock:
            store = self._get_store(user_id)
            if store is None:
                return []
            return store.similarity_search_with_score(query, k=k)

    def _get_store(self, user_id: str) -> FAISS | None:
        if user_id in self._stores:
            return self._stores[user_id]

        path = self._user_path(user_id)
        if not (path / "index.faiss").exists():
            return None

        # The index is generated and owned by this application.
        store = FAISS.load_local(
            path,
            self.embeddings,
            allow_dangerous_deserialization=True,
        )
        self._stores[user_id] = store
        return store

    def index_size(self, user_id: str) -> int:
        with self._lock:
            store = self._get_store(user_id)
            return int(store.index.ntotal) if store is not None else 0

    def _user_path(self, user_id: str) -> Path:
        safe_user_id = "".join(
            character
            for character in user_id
            if character.isalnum() or character in "-_"
        )
        if not safe_user_id:
            raise ValueError("Invalid user identifier")
        return self.root_dir / safe_user_id
