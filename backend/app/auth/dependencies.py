"""
FastAPI dependency injectors for auth and RBAC.
"""
from __future__ import annotations
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from app.auth.models import UserInDB, Role
from app.auth.service import decode_token
from app.database import users_collection

_bearer = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> UserInDB:
    token = credentials.credentials
    try:
        token_data = decode_token(token)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_doc = await users_collection().find_one({"_id": token_data.user_id})
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")
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
