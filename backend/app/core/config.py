from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "SecureAI SOC Copilot"
    api_prefix: str = "/api"

    jwt_secret_key: str = Field(default="dev-only-change-me", min_length=16)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    demo_username: str = "analyst"
    demo_password: str = "change-me"

    openai_api_key: str = ""
    openai_embedding_model: str = "text-embedding-3-small"

    llm_provider: str = "openai"
    openai_chat_model: str = "gpt-4o-mini"
    anthropic_api_key: str = ""
    anthropic_chat_model: str = "claude-haiku-4-5"
    llm_max_tokens: int = 1000
    llm_timeout_seconds: int = 60

    data_dir: Path = Path("./data")
    max_upload_mb: int = 10
    chunk_size: int = 1000
    chunk_overlap: int = 150
    retrieval_k: int = 4

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
        if not self.openai_api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is required for embeddings. "
                "Copy .env.example to .env and set it."
            )
        provider = self.llm_provider.lower()
        if provider not in {"openai", "anthropic"}:
            raise RuntimeError("LLM_PROVIDER must be 'openai' or 'anthropic'.")
        if provider == "anthropic" and not self.anthropic_api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is required when LLM_PROVIDER=anthropic."
            )
        if self.chunk_overlap >= self.chunk_size:
            raise RuntimeError("CHUNK_OVERLAP must be smaller than CHUNK_SIZE.")


@lru_cache
def get_settings() -> Settings:
    return Settings()
