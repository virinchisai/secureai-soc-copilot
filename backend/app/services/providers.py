from typing import Protocol

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI

from app.core.config import Settings


class ChatModel(Protocol):
    def invoke(self, messages: list[BaseMessage]) -> object: ...


def build_chat_model(settings: Settings) -> tuple[ChatModel, str, str]:
    provider = settings.llm_provider.lower()
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
