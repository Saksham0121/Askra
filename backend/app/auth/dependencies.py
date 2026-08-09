"""
FastAPI dependency injectors for auth and RBAC.
"""
from __future__ import annotations
from fastapi import Depends, HTTPException, status, Query, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from bson import ObjectId
from app.auth.models import UserInDB, Role
from app.auth.service import decode_token
from app.database import users_collection

_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    _token: str | None = Query(None),
) -> UserInDB:
    token = None
    if credentials:
        token = credentials.credentials
    elif _token:
        token = _token

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        token_data = decode_token(token)
    except (JWTError, Exception):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    col = users_collection()
    user_doc = None
    try:
        user_doc = await col.find_one({"_id": ObjectId(token_data.user_id)})
    except Exception:
        pass

    if not user_doc:
        user_doc = await col.find_one({"_id": token_data.user_id})

    if not user_doc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or token invalid",
        )
    if not user_doc.get("is_active", True):
        raise HTTPException(status_code=403, detail="Account deactivated")

    user_doc["_id"] = str(user_doc["_id"])
    return UserInDB(**user_doc)


def require_role(*allowed_roles: str):
    """Factory that returns a dependency requiring one of the given roles."""
    async def _check(current_user: UserInDB = Depends(get_current_user)) -> UserInDB:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {' or '.join(allowed_roles)}",
            )
        return current_user
    return _check


# Convenience shortcuts
require_admin = require_role(Role.ADMIN)
require_manager_or_admin = require_role(Role.MANAGER, Role.ADMIN)
