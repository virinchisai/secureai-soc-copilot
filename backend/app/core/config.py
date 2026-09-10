from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "SecureAI SOC Copilot"
    app_version: str = "2.0.0"
    api_prefix: str = "/api"

    jwt_secret_key: str = Field(default="dev-only-change-me", min_length=16)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    demo_username: str = "analyst"
    demo_password: str = "change-me"

    embedding_provider: str = "ollama"
    openai_api_key: str = ""
    openai_embedding_model: str = "text-embedding-3-small"
    ollama_base_url: str = "http://localhost:11434"
    ollama_embedding_model: str = "nomic-embed-text"
    ollama_chat_model: str = "deepseek-r1:1.5b"

    llm_provider: str = "ollama"
    openai_chat_model: str = "gpt-4o-mini"
    anthropic_api_key: str = ""
    anthropic_chat_model: str = "claude-haiku-4-5"
    llm_max_tokens: int = 120
    llm_timeout_seconds: int = 180

    data_dir: Path = Path("./data")
    max_upload_mb: int = 10
    chunk_size: int = 1000
    chunk_overlap: int = 150
    retrieval_k: int = 2
    model_context_chars_per_source: int = 500

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def database_path(self) -> Path:
        return self.data_dir / "soc_copilot.db"

    @property
    def faiss_dir(self) -> Path:
        return self.data_dir / "faiss"

    @property
    def uploads_dir(self) -> Path:
        return self.data_dir / "uploads"

    def validate_runtime(self) -> None:
        if not self.demo_username.strip() or not self.demo_password:
            raise RuntimeError("DEMO_USERNAME and DEMO_PASSWORD cannot be empty.")
        if self.access_token_expire_minutes <= 0:
            raise RuntimeError("ACCESS_TOKEN_EXPIRE_MINUTES must be positive.")
        if self.max_upload_mb <= 0:
            raise RuntimeError("MAX_UPLOAD_MB must be positive.")
        if self.chunk_size <= 0:
            raise RuntimeError("CHUNK_SIZE must be positive.")
        if self.chunk_overlap < 0:
            raise RuntimeError("CHUNK_OVERLAP cannot be negative.")
        if self.retrieval_k <= 0:
            raise RuntimeError("RETRIEVAL_K must be positive.")
        if self.model_context_chars_per_source <= 0:
            raise RuntimeError(
                "MODEL_CONTEXT_CHARS_PER_SOURCE must be positive."
            )
        if self.llm_max_tokens <= 0 or self.llm_timeout_seconds <= 0:
            raise RuntimeError(
                "LLM_MAX_TOKENS and LLM_TIMEOUT_SECONDS must be positive."
            )

        embedding_provider = self.embedding_provider.lower()
        if embedding_provider not in {"ollama", "openai"}:
            raise RuntimeError(
                "EMBEDDING_PROVIDER must be 'ollama' or 'openai'."
            )
        if embedding_provider == "openai" and not self.openai_api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is required when EMBEDDING_PROVIDER=openai."
            )
        provider = self.llm_provider.lower()
        if provider not in {"ollama", "openai", "anthropic"}:
            raise RuntimeError(
                "LLM_PROVIDER must be 'ollama', 'openai', or 'anthropic'."
            )
        if provider == "openai" and not self.openai_api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is required when LLM_PROVIDER=openai."
            )
        if provider == "anthropic" and not self.anthropic_api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is required when LLM_PROVIDER=anthropic."
            )
        if self.chunk_overlap >= self.chunk_size:
            raise RuntimeError("CHUNK_OVERLAP must be smaller than CHUNK_SIZE.")


@lru_cache
def get_settings() -> Settings:
    return Settings()
