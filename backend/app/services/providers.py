from typing import Protocol

from langchain_anthropic import ChatAnthropic
from langchain_core.embeddings import Embeddings
from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from app.core.config import Settings
from app.services.ollama import OllamaChatModel, OllamaEmbeddings


class ChatModel(Protocol):
    def invoke(self, messages: list[BaseMessage]) -> object: ...


def build_embeddings(settings: Settings) -> Embeddings:
    provider = settings.embedding_provider.lower()
    if provider == "ollama":
        return OllamaEmbeddings(
            base_url=settings.ollama_base_url,
            model=settings.ollama_embedding_model,
            timeout=settings.llm_timeout_seconds,
        )
    if provider == "openai":
        return OpenAIEmbeddings(
            api_key=settings.openai_api_key,
            model=settings.openai_embedding_model,
        )
    raise ValueError(
        f"Unsupported embedding provider: {settings.embedding_provider}"
    )


def build_chat_model(settings: Settings) -> tuple[ChatModel, str, str]:
    provider = settings.llm_provider.lower()
    if provider == "ollama":
        model = OllamaChatModel(
            base_url=settings.ollama_base_url,
            model=settings.ollama_chat_model,
            timeout=settings.llm_timeout_seconds,
            max_tokens=settings.llm_max_tokens,
        )
        return model, provider, settings.ollama_chat_model

    if provider == "openai":
        model = ChatOpenAI(
            api_key=settings.openai_api_key,
            model=settings.openai_chat_model,
            temperature=0,
            max_tokens=settings.llm_max_tokens,
            timeout=settings.llm_timeout_seconds,
            max_retries=2,
        )
        return model, provider, settings.openai_chat_model

    if provider == "anthropic":
        model = ChatAnthropic(
            api_key=settings.anthropic_api_key,
            model_name=settings.anthropic_chat_model,
            temperature=0,
            max_tokens=settings.llm_max_tokens,
            timeout=settings.llm_timeout_seconds,
            max_retries=2,
        )
        return model, provider, settings.anthropic_chat_model

    raise ValueError(f"Unsupported LLM provider: {settings.llm_provider}")
