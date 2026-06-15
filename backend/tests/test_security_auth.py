from datetime import UTC, datetime, timedelta

import pyotp

from app.security import (
    create_token,
    decode_token,
    generate_totp_secret,
    token_remaining_ttl,
    verify_totp,
)


def test_totp_roundtrip() -> None:
    secret = generate_totp_secret()
    assert verify_totp(secret, pyotp.TOTP(secret).now())
    assert not verify_totp(secret, "000000")
    assert not verify_totp(secret, "")


def test_token_carries_jti_and_type() -> None:
    token = create_token("user-1", "tenant-1", "ADMIN", 900, "access")
    payload = decode_token(token)
    assert payload["type"] == "access"
    assert payload["jti"]
    assert payload["sub"] == "user-1"


def test_token_remaining_ttl() -> None:
    now = datetime.now(UTC)
    payload = {"exp": (now + timedelta(seconds=300)).timestamp()}
    remaining = token_remaining_ttl(payload, now)
    assert 295 <= remaining <= 300
    # Already-expired token yields zero (so it is never re-added to the blocklist).
    assert token_remaining_ttl({"exp": (now - timedelta(seconds=5)).timestamp()}, now) == 0
    assert token_remaining_ttl({}, now) == 0
