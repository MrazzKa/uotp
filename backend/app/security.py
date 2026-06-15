import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
import pyotp
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


def token_remaining_ttl(payload: dict[str, Any], now: datetime | None = None) -> int:
    """Seconds left until the token's exp; 0 if already expired or no exp."""
    exp = payload.get("exp")
    if exp is None:
        return 0
    current = now or datetime.now(UTC)
    remaining = int(exp - current.timestamp())
    return max(remaining, 0)


# --- TOTP (2FA) ---------------------------------------------------------------

def generate_totp_secret() -> str:
    return pyotp.random_base32()


def verify_totp(secret: str, code: str) -> bool:
    if not secret or not code:
        return False
    return pyotp.TOTP(secret).verify(code.strip(), valid_window=1)


def totp_provisioning_uri(secret: str, account_name: str, issuer: str = "UOTP") -> str:
    return pyotp.TOTP(secret).provisioning_uri(name=account_name, issuer_name=issuer)
