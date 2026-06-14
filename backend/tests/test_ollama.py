import io
import json

from langchain_core.messages import HumanMessage, SystemMessage

from app.services import ollama
from app.services.ollama import OllamaChatModel, OllamaEmbeddings


class FakeResponse:
    def __init__(self, payload: dict) -> None:
        self.body = io.BytesIO(json.dumps(payload).encode("utf-8"))

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        return None

    def read(self) -> bytes:
        return self.body.read()


def test_ollama_embeddings_support_batch_input(monkeypatch) -> None:
    captured = {}

    def fake_urlopen(request, timeout):
        captured["payload"] = json.loads(request.data)
        captured["timeout"] = timeout
        return FakeResponse({"embeddings": [[1.0, 0.0], [0.0, 1.0]]})

    monkeypatch.setattr(ollama, "urlopen", fake_urlopen)
    embeddings = OllamaEmbeddings("http://localhost:11434", "nomic", timeout=12)

    assert embeddings.embed_documents(["one", "two"]) == [
        [1.0, 0.0],
        [0.0, 1.0],
    ]
    assert captured["payload"] == {"model": "nomic", "input": ["one", "two"]}
    assert captured["timeout"] == 12


def test_ollama_chat_maps_langchain_messages(monkeypatch) -> None:
    captured = {}

    def fake_urlopen(request, timeout):
        captured["payload"] = json.loads(request.data)
        return FakeResponse({"message": {"content": "Grounded answer [S1]."}})

    monkeypatch.setattr(ollama, "urlopen", fake_urlopen)
    model = OllamaChatModel("http://localhost:11434", "llama3.2")
    response = model.invoke(
        [SystemMessage(content="System"), HumanMessage(content="Question")]
    )

    assert response.content == "Grounded answer [S1]."
    assert captured["payload"]["stream"] is False
    assert captured["payload"]["think"] is False
    assert captured["payload"]["messages"] == [
        {"role": "system", "content": "System"},
        {"role": "user", "content": "Question"},
    ]
