from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import audit, auth, chat, documents
from app.core.config import get_settings
from app.core.database import Database
from app.services.rag import RAGService
from app.services.storage import UploadStorage


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    settings.validate_runtime()
    settings.data_dir.mkdir(parents=True, exist_ok=True)

    database = Database(settings.database_path)
    database.initialize()

    app.state.database = database
    app.state.rag_service = RAGService(settings)
    app.state.upload_storage = UploadStorage(settings.uploads_dir)
    yield


settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Grounded question answering for cybersecurity logs and reports.",
    lifespan=lifespan,
)

app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(documents.router, prefix=settings.api_prefix)
app.include_router(chat.router, prefix=settings.api_prefix)
app.include_router(audit.router, prefix=settings.api_prefix)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}
