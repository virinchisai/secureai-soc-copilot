from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.core.database import Database
from app.dependencies import get_current_user, get_database
from app.schemas import DocumentStatsResponse, SystemStatusResponse


router = APIRouter(prefix="/system", tags=["system"])


@router.get("/status", response_model=SystemStatusResponse)
def system_status(
    current_user: str = Depends(get_current_user),
    database: Database = Depends(get_database),
    settings: Settings = Depends(get_settings),
) -> SystemStatusResponse:
    stats = database.document_stats(current_user)
    return SystemStatusResponse(
        app_name=settings.app_name,
        version=settings.app_version,
        username=current_user,
        embedding_provider=settings.embedding_provider,
        embedding_model=_embedding_model_name(settings),
        llm_provider=settings.llm_provider,
        llm_model=_chat_model_name(settings),
        document_stats=DocumentStatsResponse(**stats),
    )


def _embedding_model_name(settings: Settings) -> str:
    if settings.embedding_provider.lower() == "openai":
        return settings.openai_embedding_model
    return settings.ollama_embedding_model


def _chat_model_name(settings: Settings) -> str:
    provider = settings.llm_provider.lower()
    if provider == "openai":
        return settings.openai_chat_model
    if provider == "anthropic":
        return settings.anthropic_chat_model
    return settings.ollama_chat_model
