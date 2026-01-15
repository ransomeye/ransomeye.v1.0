#!/usr/bin/env python3
"""
RansomEye v1.0 SOC UI Backend Auth Utilities
AUTHORITATIVE: JWT access/refresh/service token handling
Python 3.10+ only
"""

import hashlib
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Tuple

import jwt


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_access_token(
    user: Dict[str, Any],
    signing_key: str,
    issuer: str,
    audience: str,
    ttl_seconds: int
) -> Tuple[str, datetime]:
    now = utc_now()
    exp = now + timedelta(seconds=ttl_seconds)
    payload = {
        "sub": user["user_id"],
        "username": user.get("username"),
        "role": user.get("role"),
        "token_type": "access",
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "iss": issuer,
        "aud": audience
    }
    token = jwt.encode(payload, signing_key, algorithm="HS256")
    return token, exp


def create_refresh_token(
    user_id: str,
    token_id: str,
    signing_key: str,
    issuer: str,
    audience: str,
    ttl_seconds: int
) -> Tuple[str, datetime]:
    now = utc_now()
    exp = now + timedelta(seconds=ttl_seconds)
    payload = {
        "sub": user_id,
        "jti": token_id,
        "token_type": "refresh",
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "iss": issuer,
        "aud": audience
    }
    token = jwt.encode(payload, signing_key, algorithm="HS256")
    return token, exp


def create_service_token(
    user_id: str,
    signing_key: str,
    issuer: str,
    audience: str,
    ttl_seconds: int
) -> Tuple[str, datetime]:
    now = utc_now()
    exp = now + timedelta(seconds=ttl_seconds)
    payload = {
        "sub": user_id,
        "token_type": "service",
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "iss": issuer,
        "aud": audience
    }
    token = jwt.encode(payload, signing_key, algorithm="HS256")
    return token, exp


def decode_token(
    token: str,
    signing_key: str,
    issuer: str,
    audience: str,
    leeway_seconds: int = 30
) -> Dict[str, Any]:
    return jwt.decode(
        token,
        signing_key,
        algorithms=["HS256"],
        audience=audience,
        issuer=issuer,
        options={
            "require": ["sub", "iat", "exp", "token_type"],
            "verify_signature": True,
            "verify_exp": True,
            "verify_iat": True
        },
        leeway=leeway_seconds
    )
