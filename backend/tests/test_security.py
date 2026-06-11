from app.core.config import Settings
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_password_hash_round_trip() -> None:
    hashed = hash_password("correct horse battery staple")
    assert verify_password("correct horse battery staple", hashed)
    assert not verify_password("wrong", hashed)


def test_jwt_round_trip(tmp_path) -> None:
    settings = Settings(
        jwt_secret_key="test-secret-that-is-long-enough",
        data_dir=tmp_path,
    )
    token = create_access_token("analyst", settings)
    assert decode_access_token(token, settings) == "analyst"
