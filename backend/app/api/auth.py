from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.core.config import Settings, get_settings
from app.core.security import create_access_token, hash_password, verify_password
from app.schemas import TokenResponse


router = APIRouter(prefix="/auth", tags=["auth"])


@lru_cache
def _demo_password_hash(password: str) -> str:
    return hash_password(password)


@router.post("/token", response_model=TokenResponse)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    valid_username = form_data.username == settings.demo_username
    valid_password = verify_password(
        form_data.password,
        _demo_password_hash(settings.demo_password),
    )
    if not (valid_username and valid_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return TokenResponse(access_token=create_access_token(form_data.username, settings))
