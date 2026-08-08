"""
Admin API — user management, audit logs (Admin only).
"""
from __future__ import annotations
from datetime import datetime, timezone
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from app.auth.dependencies import require_admin
from app.auth.models import UserInDB, UserPublic, UserUpdateRequest
from app.database import users_collection, analytics_collection

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/users")
async def list_users(current_user: UserInDB = Depends(require_admin)):
    cursor = users_collection().find({}, {"hashed_password": 0}).sort("created_at", -1)
    users = await cursor.to_list(length=500)
    for u in users:
        u["_id"] = str(u["_id"])
    return {"users": users}


@router.patch("/users/{user_id}")
async def update_user(
    user_id: str,
    body: UserUpdateRequest,
    current_user: UserInDB = Depends(require_admin),
):
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    result = await users_collection().update_one(
        {"_id": ObjectId(user_id)},
        {"$set": updates},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User updated"}


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    current_user: UserInDB = Depends(require_admin),
):
    if str(current_user.id) == user_id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    result = await users_collection().delete_one({"_id": ObjectId(user_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User deleted"}


@router.get("/audit-logs")
async def audit_logs(
    limit: int = 100,
    current_user: UserInDB = Depends(require_admin),
):
    cursor = analytics_collection().find({}, {"_id": 0}).sort("timestamp", -1).limit(limit)
    logs = await cursor.to_list(length=limit)
    return {"logs": logs}
