"""
Chat API — POST /api/chat and GET /api/chat/stream (SSE).
"""
from __future__ import annotations
import json
from datetime import datetime, timezone
from typing import AsyncGenerator
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from app.auth.dependencies import get_current_user
from app.auth.models import UserInDB
from app.database import chat_sessions_collection, messages_collection, analytics_collection
from app.pipeline_bridge import get_pipeline_bridge

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    query: str
    direct_rag: bool = False
    session_id: str | None = None


class ChatResponse(BaseModel):
    session_id: str
    query: str
    answer: str
    sources: list[str]
    confidence_score: float
    answer_source: str
    validation_reasoning: str
    iterations: int
    latency_ms: int
    timestamp: str


async def _log_message(session_id: str, user_id: str, query: str, result_data: dict):
    """Persist chat message to MongoDB."""
    await messages_collection().insert_one({
        "session_id": session_id,
        "user_id": user_id,
        "query": query,
        "answer": result_data.get("answer", ""),
        "sources": result_data.get("sources", []),
        "confidence_score": result_data.get("confidence_score", 0),
        "answer_source": result_data.get("answer_source", ""),
        "latency_ms": result_data.get("latency_ms", 0),
        "iterations": result_data.get("iterations", 1),
        "timestamp": datetime.now(timezone.utc),
    })
    await analytics_collection().insert_one({
        "event": "query",
        "user_id": user_id,
        "query": query,
        "answer_source": result_data.get("answer_source", ""),
        "confidence_score": result_data.get("confidence_score", 0),
        "latency_ms": result_data.get("latency_ms", 0),
        "timestamp": datetime.now(timezone.utc),
    })


@router.post("", response_model=ChatResponse)
async def chat(body: ChatRequest, current_user: UserInDB = Depends(get_current_user)):
    bridge = get_pipeline_bridge()
    result = bridge.run(query=body.query, direct_rag=body.direct_rag)

    # Ensure / create session
    session_id = body.session_id
    if not session_id:
        sess = await chat_sessions_collection().insert_one({
            "user_id": str(current_user.id),
            "created_at": datetime.now(timezone.utc),
        })
        session_id = str(sess.inserted_id)

    result_data = {
        "answer": result.answer,
        "sources": result.sources,
        "confidence_score": result.confidence_score,
        "answer_source": result.answer_source,
        "latency_ms": result.latency_ms,
        "iterations": result.iterations,
    }
    await _log_message(session_id, str(current_user.id), body.query, result_data)

    return ChatResponse(
        session_id=session_id,
        query=body.query,
        answer=result.answer,
        sources=result.sources,
        confidence_score=result.confidence_score,
        answer_source=result.answer_source,
        validation_reasoning=result.validation_reasoning,
        iterations=result.iterations,
        latency_ms=result.latency_ms,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


async def _sse_generator(query: str, direct_rag: bool, user_id: str, session_id: str) -> AsyncGenerator[str, None]:
    bridge = get_pipeline_bridge()
    result_data = {}
    try:
        for event in bridge.run_stream(query=query, direct_rag=direct_rag):
            if event["type"] == "result":
                r = event["data"]
                result_data = {
                    "answer": r.answer,
                    "sources": r.sources,
                    "confidence_score": r.confidence_score,
                    "answer_source": r.answer_source,
                    "latency_ms": r.latency_ms,
                    "iterations": r.iterations,
                }
                payload = json.dumps({
                    "type": "result",
                    "session_id": session_id,
                    "answer": r.answer,
                    "sources": r.sources,
                    "confidence_score": r.confidence_score,
                    "confidence_badge": r.confidence_badge,
                    "answer_source": r.answer_source,
                    "answer_source_label": r.answer_source_label,
                    "validation_reasoning": r.validation_reasoning,
                    "iterations": r.iterations,
                    "latency_ms": r.latency_ms,
                })
            else:
                payload = json.dumps(event)
            yield f"data: {payload}\n\n"
    except Exception as exc:
        yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"
    finally:
        if result_data:
            await _log_message(session_id, user_id, query, result_data)


@router.get("/stream")
async def chat_stream(
    query: str = Query(..., min_length=1),
    direct_rag: bool = Query(False),
    session_id: str | None = Query(None),
    current_user: UserInDB = Depends(get_current_user),
):
    sid = session_id
    if not sid:
        sess = await chat_sessions_collection().insert_one({
            "user_id": str(current_user.id),
            "created_at": datetime.now(timezone.utc),
        })
        sid = str(sess.inserted_id)

    return StreamingResponse(
        _sse_generator(query, direct_rag, str(current_user.id), sid),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.get("/history")
async def chat_history(
    limit: int = Query(50, le=200),
    current_user: UserInDB = Depends(get_current_user),
):
    """Return recent messages for the current user."""
    cursor = messages_collection().find(
        {"user_id": str(current_user.id)},
        {"_id": 0},
    ).sort("timestamp", -1).limit(limit)
    messages = await cursor.to_list(length=limit)
    return {"messages": messages}


@router.get("/sessions")
async def list_sessions(current_user: UserInDB = Depends(get_current_user)):
    cursor = chat_sessions_collection().find(
        {"user_id": str(current_user.id)}, {"_id": 1, "created_at": 1}
    ).sort("created_at", -1).limit(20)
    sessions = await cursor.to_list(length=20)
    for s in sessions:
        s["_id"] = str(s["_id"])
    return {"sessions": sessions}
