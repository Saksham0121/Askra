"""
Auth Router — /auth endpoints.
"""
from __future__ import annotations
from datetime import datetime, timezone
from bson import ObjectId
from fastapi import APIRouter, HTTPException, status, Depends
from jose import JWTError
from app.auth.models import (
    LoginRequest, RegisterRequest, Token, UserPublic, UserUpdateRequest
)
from app.auth.service import (
    hash_password, verify_password,
    create_access_token, create_refresh_token, decode_token,
)
from app.auth.dependencies import get_current_user
from app.database import users_collection
from app.auth.models import UserInDB, Role

router = APIRouter(prefix="/auth", tags=["auth"])


def _to_public(doc: dict) -> UserPublic:
    doc["_id"] = str(doc["_id"])
    return UserPublic(**doc)


@router.post("/register", response_model=UserPublic, status_code=201)
async def register(body: RegisterRequest):
    if len(body.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters long.")
    if len(body.password.encode("utf-8")) > 72:
        raise HTTPException(status_code=400, detail="Password cannot exceed 72 bytes.")

    col = users_collection()
    if await col.find_one({"email": body.email}):
        raise HTTPException(status_code=409, detail="Email already registered")

    allowed_roles = [Role.ADMIN.value, Role.HR.value, Role.MANAGER.value, Role.EMPLOYEE.value]
    user_role = body.role if body.role in allowed_roles else Role.EMPLOYEE.value

    doc = {
        "email": body.email,
        "full_name": body.full_name,
        "hashed_password": hash_password(body.password),
        "role": user_role,
        "department": body.department.lower(),
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
        "last_login": None,
    }
    result = await col.insert_one(doc)
    doc["_id"] = str(result.inserted_id)
    return UserPublic(**doc)


@router.post("/login", response_model=Token)
async def login(body: LoginRequest):
    if not body.password or len(body.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters long.")

    col = users_collection()
    user_doc = await col.find_one({"email": body.email})
    if not user_doc or not verify_password(body.password, user_doc["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    if not user_doc.get("is_active", True):
        raise HTTPException(status_code=403, detail="Account deactivated. Please contact support.")

    user_id = str(user_doc["_id"])
    token_payload = {"sub": user_id, "email": user_doc["email"], "role": user_doc["role"]}

    await col.update_one(
        {"_id": user_doc["_id"]},
        {"$set": {"last_login": datetime.now(timezone.utc)}},
    )

    user_doc["_id"] = user_id
    return Token(
        access_token=create_access_token(token_payload),
        refresh_token=create_refresh_token(token_payload),
        user=UserPublic(**user_doc),
    )


@router.post("/refresh", response_model=Token)
async def refresh(body: dict):
    refresh_token = body.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=400, detail="Refresh token is required")

    try:
        token_data = decode_token(refresh_token)
    except (JWTError, Exception):
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    col = users_collection()
    user_doc = None
    try:
        user_doc = await col.find_one({"_id": ObjectId(token_data.user_id)})
    except Exception:
        pass

    if not user_doc:
        user_doc = await col.find_one({"_id": token_data.user_id})

    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")

    user_id = str(user_doc["_id"])
    token_payload = {"sub": user_id, "email": user_doc["email"], "role": user_doc["role"]}
    user_doc["_id"] = user_id
    return Token(
        access_token=create_access_token(token_payload),
        refresh_token=create_refresh_token(token_payload),
        user=UserPublic(**user_doc),
    )


@router.get("/me", response_model=UserPublic)
async def me(current_user: UserInDB = Depends(get_current_user)):
    return current_user
