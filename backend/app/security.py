import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from passlib.context import CryptContext

from app.config import settings

password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return password_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return password_context.verify(password, password_hash)


def create_token(subject: str, tenant_id: str, role: str, ttl_seconds: int, token_type: str) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "tenant_id": tenant_id,
        "role": role,
        "type": token_type,
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": now + timedelta(seconds=ttl_seconds),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
