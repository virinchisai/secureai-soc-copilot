import pytest
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI

from app.core.config import Settings
from app.services.ollama import OllamaChatModel, OllamaEmbeddings
from app.services.providers import build_chat_model, build_embeddings


def test_builds_ollama_embeddings(tmp_path) -> None:
    settings = Settings(
        jwt_secret_key="test-secret-that-is-long-enough",
        embedding_provider="ollama",
        data_dir=tmp_path,
    )
    embeddings = build_embeddings(settings)
    assert isinstance(embeddings, OllamaEmbeddings)
    assert embeddings.model == settings.ollama_embedding_model


def test_builds_ollama_chat_model(tmp_path) -> None:
    settings = Settings(
        jwt_secret_key="test-secret-that-is-long-enough",
        llm_provider="ollama",
        data_dir=tmp_path,
    )
    model, provider, model_name = build_chat_model(settings)
    assert isinstance(model, OllamaChatModel)
    assert provider == "ollama"
    assert model_name == settings.ollama_chat_model


def test_builds_openai_chat_model(tmp_path) -> None:
    settings = Settings(
        jwt_secret_key="test-secret-that-is-long-enough",
        openai_api_key="test-openai-key",
        embedding_provider="openai",
        llm_provider="openai",
        data_dir=tmp_path,
    )
    model, provider, model_name = build_chat_model(settings)
    assert isinstance(model, ChatOpenAI)
    assert provider == "openai"
    assert model_name == settings.openai_chat_model


def test_builds_anthropic_chat_model(tmp_path) -> None:
    settings = Settings(
        jwt_secret_key="test-secret-that-is-long-enough",
        openai_api_key="test-openai-key",
        anthropic_api_key="test-anthropic-key",
        embedding_provider="openai",
        llm_provider="anthropic",
        data_dir=tmp_path,
    )
    model, provider, model_name = build_chat_model(settings)
    assert isinstance(model, ChatAnthropic)
    assert provider == "anthropic"
    assert model_name == settings.anthropic_chat_model


def test_rejects_unknown_provider(tmp_path) -> None:
    settings = Settings(
        jwt_secret_key="test-secret-that-is-long-enough",
        openai_api_key="test-openai-key",
        llm_provider="unknown",
        data_dir=tmp_path,
    )
    with pytest.raises(ValueError, match="Unsupported LLM provider"):
        build_chat_model(settings)
