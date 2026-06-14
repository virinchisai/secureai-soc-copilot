import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from langchain_core.embeddings import Embeddings
from langchain_core.messages import AIMessage, BaseMessage


class OllamaError(RuntimeError):
    pass


def _post_json(base_url: str, endpoint: str, payload: dict, timeout: int) -> dict:
    request = Request(
        f"{base_url.rstrip('/')}{endpoint}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise OllamaError(f"Ollama returned HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        raise OllamaError(
            f"Cannot reach Ollama at {base_url}. Start Ollama and pull the "
            "configured models."
        ) from exc


class OllamaEmbeddings(Embeddings):
    def __init__(self, base_url: str, model: str, timeout: int = 60) -> None:
        self.base_url = base_url
        self.model = model
        self.timeout = timeout

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        response = _post_json(
            self.base_url,
            "/api/embed",
            {"model": self.model, "input": texts},
            self.timeout,
        )
        embeddings = response.get("embeddings")
        if not isinstance(embeddings, list) or len(embeddings) != len(texts):
            raise OllamaError("Ollama returned an invalid embedding response.")
        return embeddings

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]


class OllamaChatModel:
    def __init__(
        self,
        base_url: str,
        model: str,
        timeout: int = 60,
        max_tokens: int = 1000,
    ) -> None:
        self.base_url = base_url
        self.model = model
        self.timeout = timeout
        self.max_tokens = max_tokens

    def invoke(self, messages: list[BaseMessage]) -> AIMessage:
        ollama_messages = [
            {
                "role": _message_role(message),
                "content": str(message.content),
            }
            for message in messages
        ]
        response = _post_json(
            self.base_url,
            "/api/chat",
            {
                "model": self.model,
                "messages": ollama_messages,
                "stream": False,
                "think": False,
                "options": {
                    "temperature": 0,
                    "num_predict": self.max_tokens,
                },
            },
            self.timeout,
        )
        message = response.get("message")
        if not isinstance(message, dict) or not isinstance(
            message.get("content"), str
        ):
            raise OllamaError("Ollama returned an invalid chat response.")
        return AIMessage(content=message["content"])


def _message_role(message: BaseMessage) -> str:
    roles = {
        "system": "system",
        "human": "user",
        "ai": "assistant",
    }
    return roles.get(message.type, "user")
