"""
MongoDB Async Client via Motor.
"""

from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.config import get_settings

_client: AsyncIOMotorClient | None = None


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        settings = get_settings()
        _client = AsyncIOMotorClient(settings.mongodb_uri)
    return _client


def get_db() -> AsyncIOMotorDatabase:
    settings = get_settings()
    return get_client()[settings.mongodb_db_name]


async def close_connection() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None


# Collections helpers
def users_collection():
    return get_db()["users"]


def documents_collection():
    return get_db()["documents"]


def chat_sessions_collection():
    return get_db()["chat_sessions"]


def messages_collection():
    return get_db()["messages"]


def analytics_collection():
    return get_db()["analytics"]
