from datetime import datetime, timedelta, timezone
from uuid import uuid4

import bcrypt
import jwt

from app.core.config import get_settings

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(*, user_id: str, role: str, remember: bool = False) -> tuple[str, str, datetime]:
    settings = get_settings()
    minutes = settings.jwt_remember_minutes if remember else settings.jwt_access_token_expire_minutes
    expire = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    jti = str(uuid4())
    payload = {
        "sub": user_id,
        "role": role,
        "jti": jti,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=ALGORITHM)
    return token, jti, expire


def decode_token(token: str) -> dict:
    settings = get_settings()
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[ALGORITHM])
