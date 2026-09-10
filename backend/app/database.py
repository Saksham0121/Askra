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


async def init_indexes() -> None:
    """
    Ensure all required compound and unique indexes exist on MongoDB collections.
    Prevents full collection scans during frequent conversation queries and RBAC checks.
    """
    from pymongo import ASCENDING, DESCENDING, IndexModel

    db = get_db()

    # 1. messages: (session_id, timestamp) for session history, (user_id, timestamp) for user history
    await db["messages"].create_indexes([
        IndexModel([("session_id", ASCENDING), ("timestamp", DESCENDING)], name="idx_session_timestamp"),
        IndexModel([("user_id", ASCENDING), ("timestamp", DESCENDING)], name="idx_user_timestamp"),
    ])

    # 2. chat_sessions: (user_id, updated_at) for session list sorted by latest activity
    await db["chat_sessions"].create_indexes([
        IndexModel([("user_id", ASCENDING), ("updated_at", DESCENDING)], name="idx_user_updated"),
    ])

    # 3. documents: (department, created_at) for department-scoped RBAC document listing
    await db["documents"].create_indexes([
        IndexModel([("department", ASCENDING), ("created_at", DESCENDING)], name="idx_dept_created"),
    ])

    # 4. users: unique email
    await db["users"].create_indexes([
        IndexModel([("email", ASCENDING)], unique=True, name="idx_user_email_unique"),
    ])

    # 5. analytics: (event, timestamp) for analytics aggregation and query trend charts
    await db["analytics"].create_indexes([
        IndexModel([("event", ASCENDING), ("timestamp", DESCENDING)], name="idx_event_timestamp"),
    ])

