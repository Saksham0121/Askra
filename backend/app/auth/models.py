"""
Auth Models — User, Role, Token schemas.
"""
from __future__ import annotations
from datetime import datetime
from enum import str, auto
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class Role(str):
    EMPLOYEE = "employee"
    MANAGER = "manager"
    ADMIN = "admin"


# ── DB Models ──────────────────────────────────────────────────────────────
class UserInDB(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    email: EmailStr
    full_name: str
    hashed_password: str
    role: str = Role.EMPLOYEE
    department: str = "general"
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None

    model_config = {"populate_by_name": True}


class UserPublic(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    email: str
    full_name: str
    role: str
    department: str
    is_active: bool
    created_at: datetime

    model_config = {"populate_by_name": True}


# ── Request / Response Schemas ─────────────────────────────────────────────
class RegisterRequest(BaseModel):
    email: EmailStr
    full_name: str
    password: str = Field(min_length=6)
    department: str = "general"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserPublic


class TokenData(BaseModel):
    user_id: str
    email: str
    role: str


class UserUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    role: Optional[str] = None
    department: Optional[str] = None
    is_active: Optional[bool] = None
