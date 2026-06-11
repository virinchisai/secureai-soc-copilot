from dataclasses import dataclass

from langchain_core.embeddings import Embeddings
from langchain_core.messages import AIMessage

from app.core.config import Settings
from app.services.rag import RAGService, _normalize_citations, _response_text


class KeywordEmbeddings(Embeddings):
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)

    @staticmethod
    def _embed(text: str) -> list[float]:
        lowered = text.lower()
        return [
            float("192.0.2.44" in lowered or "failed login" in lowered),
            float("malware" in lowered or "web-01" in lowered),
            float("db-01" in lowered or "database" in lowered),
        ]


@dataclass
class FakeChatModel:
    response: object
    messages: list | None = None

    def invoke(self, messages: list) -> object:
        self.messages = messages
        return self.response


def test_rag_retrieves_chunks_and_returns_grounded_citations(tmp_path) -> None:
    settings = Settings(
        jwt_secret_key="test-secret-that-is-long-enough",
        openai_api_key="test-key",
        data_dir=tmp_path,
        chunk_size=200,
        chunk_overlap=20,
        retrieval_k=2,
    )
    model = FakeChatModel(
        AIMessage(
            content=(
                "The failed login originated from 192.0.2.44 [S1]. "
                "This invalid citation must be removed [S99]."
            )
        )
    )
    rag = RAGService(
        settings,
        embeddings=KeywordEmbeddings(),
        chat_model=model,
        provider_name="openai",
        model_name="test-chat",
    )
    rag.ingest(
        "analyst",
        "auth-doc",
        "auth.log",
        [(None, "Repeated failed login attempts came from 192.0.2.44.")],
    )
    rag.ingest(
        "analyst",
        "malware-doc",
        "malware.txt",
        [(None, "Malware was detected on host web-01.")],
    )

    answer, sources, provider, model_name = rag.answer(
        "analyst",
        "Which IP generated the failed login attempts?",
    )

    assert sources[0]["filename"] == "auth.log"
    assert sources[0]["snippet"].startswith("Repeated failed login")
    assert "[S1]" in answer
    assert "[S99]" not in answer
    assert provider == "openai"
    assert model_name == "test-chat"
    assert model.messages is not None
    assert "192.0.2.44" in model.messages[1].content
    assert "SOURCE EXCERPTS" in model.messages[1].content


def test_rag_adds_retrieved_citations_when_model_omits_them(tmp_path) -> None:
    settings = Settings(
        jwt_secret_key="test-secret-that-is-long-enough",
        openai_api_key="test-key",
        data_dir=tmp_path,
        retrieval_k=1,
    )
    rag = RAGService(
        settings,
        embeddings=KeywordEmbeddings(),
        chat_model=FakeChatModel(AIMessage(content="The host was web-01.")),
        provider_name="anthropic",
        model_name="test-claude",
    )
    rag.ingest(
        "analyst",
        "malware-doc",
        "malware.txt",
        [(None, "Malware was detected on host web-01.")],
    )

    answer, sources, provider, model_name = rag.answer(
        "analyst",
        "Which host had malware?",
    )

    assert answer.endswith("Sources: [S1]")
    assert sources[0]["citation"] == "S1"
    assert provider == "anthropic"
    assert model_name == "test-claude"


def test_response_text_supports_anthropic_content_blocks() -> None:
    response = AIMessage(
        content=[
            {"type": "text", "text": "First sentence [S1]."},
            {"type": "text", "text": "Second sentence [S2]."},
        ]
    )
    assert _response_text(response) == ("First sentence [S1].\nSecond sentence [S2].")


def test_normalize_citations_only_keeps_retrieved_labels() -> None:
    sources = [{"citation": "S1"}, {"citation": "S2"}]
    assert _normalize_citations("Finding [S1] and fake [S4].", sources) == (
        "Finding [S1] and fake ."
    )
