from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer

from app.core.config import Settings, get_settings
from app.core.database import Database
from app.core.security import decode_access_token
from app.services.rag import RAGService
from app.services.storage import UploadStorage


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")


def get_database(request: Request) -> Database:
    return request.app.state.database


def get_rag_service(request: Request) -> RAGService:
    return request.app.state.rag_service


def get_upload_storage(request: Request) -> UploadStorage:
    return request.app.state.upload_storage


def get_current_user(
    token: str = Depends(oauth2_scheme),
    settings: Settings = Depends(get_settings),
) -> str:
    username = decode_access_token(token, settings)
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return username
