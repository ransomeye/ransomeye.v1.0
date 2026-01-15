import asyncio

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from starlette.requests import Request

from rbac.middleware.fastapi_auth import RBACAuth
from services.ui.backend.auth import create_access_token, create_refresh_token


class _PermissionChecker:
    def __init__(self, allowed=True):
        self.allowed = allowed

    def check_permission(self, user_id, permission, resource_type="global", resource_id=None):
        return self.allowed

    def get_user_permissions(self, user_id):
        return {"incident:view_all"}


class _RBACAPI:
    def __init__(self, allowed=True):
        self.permission_checker = _PermissionChecker(allowed=allowed)

    def get_user_by_id(self, user_id):
        return {"user_id": user_id, "username": "user", "is_active": True}


def _request():
    scope = {
        "type": "http",
        "path": "/api/test",
        "headers": [],
        "method": "GET",
        "scheme": "http",
        "server": ("testserver", 80),
        "client": ("127.0.0.1", 1234),
    }
    return Request(scope)


def test_get_current_user_missing_token():
    auth = RBACAuth(_RBACAPI(), "signing-key-1234567890", "issuer", "audience")
    with pytest.raises(HTTPException) as exc:
        asyncio.run(auth.get_current_user(_request(), None))
    assert exc.value.status_code == 401


def test_get_current_user_invalid_token_type():
    auth = RBACAuth(_RBACAPI(), "signing-key-1234567890", "issuer", "audience")
    token, _ = create_refresh_token(
        user_id="user-1",
        token_id="refresh-1",
        signing_key="signing-key-1234567890",
        issuer="issuer",
        audience="audience",
        ttl_seconds=60,
    )
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(auth.get_current_user(_request(), creds))
    assert exc.value.status_code == 401


def test_require_permission_allows_access():
    auth = RBACAuth(_RBACAPI(allowed=True), "signing-key-1234567890", "issuer", "audience")
    token, _ = create_access_token(
        user={"user_id": "user-1", "username": "alice", "role": "ADMIN"},
        signing_key="signing-key-1234567890",
        issuer="issuer",
        audience="audience",
        ttl_seconds=60,
    )
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    request = _request()

    async def handler(request, current_user):
        return "ok"

    wrapper = auth.require_permission("incident:view_all")(handler)
    result = asyncio.run(wrapper(request=request, current_user=asyncio.run(auth.get_current_user(request, creds))))
    assert result == "ok"

