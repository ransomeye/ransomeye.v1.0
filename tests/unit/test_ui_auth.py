from datetime import datetime, timezone

from services.ui.backend.auth import (
    create_access_token,
    create_refresh_token,
    create_service_token,
    decode_token,
    hash_token,
)


def test_access_token_round_trip():
    user = {"user_id": "user-1", "username": "alice", "role": "ADMIN"}
    token, exp = create_access_token(
        user=user,
        signing_key="test-signing-key-1234567890",
        issuer="unit-test",
        audience="unit-test",
        ttl_seconds=60,
    )
    payload = decode_token(
        token=token,
        signing_key="test-signing-key-1234567890",
        issuer="unit-test",
        audience="unit-test",
    )
    assert payload["sub"] == "user-1"
    assert payload["token_type"] == "access"
    assert exp > datetime.now(timezone.utc)


def test_refresh_token_round_trip():
    token, _ = create_refresh_token(
        user_id="user-2",
        token_id="token-123",
        signing_key="test-signing-key-1234567890",
        issuer="unit-test",
        audience="unit-test",
        ttl_seconds=120,
    )
    payload = decode_token(
        token=token,
        signing_key="test-signing-key-1234567890",
        issuer="unit-test",
        audience="unit-test",
    )
    assert payload["token_type"] == "refresh"
    assert payload["jti"] == "token-123"


def test_service_token_round_trip():
    token, _ = create_service_token(
        user_id="service-1",
        signing_key="test-signing-key-1234567890",
        issuer="unit-test",
        audience="unit-test",
        ttl_seconds=60,
    )
    payload = decode_token(
        token=token,
        signing_key="test-signing-key-1234567890",
        issuer="unit-test",
        audience="unit-test",
    )
    assert payload["token_type"] == "service"


def test_hash_token_is_deterministic():
    token_hash = hash_token("token-value")
    assert len(token_hash) == 64
    assert token_hash == hash_token("token-value")
