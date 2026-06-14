from dataclasses import dataclass

from langchain_core.embeddings import Embeddings
from langchain_core.messages import AIMessage

from app.core.config import Settings
from app.services.rag import (
    RAGService,
    _build_outbound_connection_summary,
    _build_structured_incident_summary,
    _normalize_citations,
    _response_text,
)


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


def test_resume_introduction_uses_fast_extractive_summary(tmp_path) -> None:
    settings = Settings(
        jwt_secret_key="test-secret-that-is-long-enough",
        data_dir=tmp_path,
        retrieval_k=1,
    )
    model = FakeChatModel(AIMessage(content="This should not be called."))
    rag = RAGService(
        settings,
        embeddings=KeywordEmbeddings(),
        chat_model=model,
        provider_name="ollama",
        model_name="test-local",
    )
    rag.ingest(
        "analyst",
        "resume-doc",
        "resume.pdf",
        [
            (
                1,
                "PROFESSIONAL SUMMARY\n"
                "Results-driven AI Engineer with two years of experience. "
                "I build grounded RAG systems for secure applications. "
                "I combine research depth with engineering rigor.\n"
                "CORE COMPETENCIES\nPython, FastAPI, FAISS",
            )
        ],
    )

    answer, sources, provider, model_name = rag.answer(
        "analyst",
        "Tell me about yourself",
    )

    assert answer.startswith("I'm a results-driven AI Engineer")
    assert answer.count("[S1]") == 3
    assert sources[0]["filename"] == "resume.pdf"
    assert len(sources) == 1
    assert provider == "extractive"
    assert model_name == "resume-summary"
    assert model.messages is None


def test_response_text_supports_anthropic_content_blocks() -> None:
    response = AIMessage(
        content=[
            {"type": "text", "text": "First sentence [S1]."},
            {"type": "text", "text": "Second sentence [S2]."},
        ]
    )
    assert _response_text(response) == ("First sentence [S1].\nSecond sentence [S2].")


def test_structured_incident_summary_extracts_grounded_events() -> None:
    sources = [
        {
            "citation": "S1",
            "document_id": "incident-doc",
            "chunk": 1,
            "filename": "incident.log",
            "snippet": (
                "event=login_success user=jsmith src_ip=203.0.113.77"
            ),
        },
        {
            "citation": "S2",
            "document_id": "incident-doc",
            "chunk": 2,
            "filename": "incident.log",
            "snippet": (
                "host=finance-ws-07 event=privilege_escalation user=jsmith "
                'process=powershell.exe command="Add-LocalGroupMember '
                'Administrators jsmith" severity=critical'
            ),
        },
        {
            "citation": "S3",
            "document_id": "incident-doc",
            "chunk": 3,
            "filename": "incident.log",
            "snippet": (
                "host=finance-ws-07 event=endpoint_isolated "
                'reason="suspected account compromise"'
            ),
        },
    ]

    result = _build_structured_incident_summary(
        "Which source IP compromised the account, what privilege escalation "
        "occurred, and how was the host contained?",
        sources,
    )

    assert result is not None
    answer, selected_sources = result
    assert "203.0.113.77" in answer
    assert "Add-LocalGroupMember Administrators jsmith" in answer
    assert "finance-ws-07 was isolated" in answer
    assert len(selected_sources) == 3


def test_outbound_connection_summary_extracts_network_fields() -> None:
    sources = [
        {
            "citation": "S2",
            "document_id": "incident-doc",
            "chunk": 2,
            "filename": "incident.log",
            "snippet": (
                "firewall=egress-fw event=connection_allowed "
                "src_ip=10.20.5.17 dst_ip=198.51.100.42 dst_port=443 "
                "bytes_out=845122 severity=critical"
            ),
        }
    ]

    result = _build_outbound_connection_summary(
        "What suspicious outbound connection occurred, including the source "
        "IP, destination IP, port, and amount of data transferred?",
        sources,
    )

    assert result is not None
    answer, selected_sources = result
    assert "10.20.5.17" in answer
    assert "198.51.100.42" in answer
    assert "port 443" in answer
    assert "845122 bytes" in answer
    assert selected_sources[0]["citation"] == "S1"


def test_normalize_citations_only_keeps_retrieved_labels() -> None:
    sources = [{"citation": "S1"}, {"citation": "S2"}]
    assert _normalize_citations("Finding [S1] and fake [S4].", sources) == (
        "Finding [S1] and fake ."
    )
