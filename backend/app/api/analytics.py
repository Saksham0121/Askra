"""
Analytics API — query trends, pipeline metrics (Manager+ only).
"""
from __future__ import annotations
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, Query
from app.auth.dependencies import require_manager_or_admin
from app.auth.models import UserInDB
from app.database import analytics_collection, messages_collection, documents_collection, users_collection

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/overview")
async def overview(current_user: UserInDB = Depends(require_manager_or_admin)):
    """High-level stats card data."""
    total_queries = await analytics_collection().count_documents({"event": "query"})
    total_docs = await documents_collection().count_documents({})
    total_users = await users_collection().count_documents({})

    pipeline = [
        {"$group": {"_id": None, "avg_latency": {"$avg": "$latency_ms"}, "avg_confidence": {"$avg": "$confidence_score"}}}
    ]
    agg = await analytics_collection().aggregate(pipeline).to_list(1)
    avg_latency = round(agg[0]["avg_latency"], 1) if agg else 0
    avg_confidence = round(agg[0]["avg_confidence"], 2) if agg else 0

    return {
        "total_queries": total_queries,
        "total_documents": total_docs,
        "total_users": total_users,
        "avg_latency_ms": avg_latency,
        "avg_confidence": avg_confidence,
    }


@router.get("/query-trends")
async def query_trends(
    days: int = Query(7, ge=1, le=90),
    current_user: UserInDB = Depends(require_manager_or_admin),
):
    """Daily query volume for the last N days."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    pipeline = [
        {"$match": {"event": "query", "timestamp": {"$gte": since}}},
        {"$group": {
            "_id": {
                "year": {"$year": "$timestamp"},
                "month": {"$month": "$timestamp"},
                "day": {"$dayOfMonth": "$timestamp"},
            },
            "count": {"$sum": 1},
            "avg_confidence": {"$avg": "$confidence_score"},
            "avg_latency": {"$avg": "$latency_ms"},
        }},
        {"$sort": {"_id.year": 1, "_id.month": 1, "_id.day": 1}},
    ]
    rows = await analytics_collection().aggregate(pipeline).to_list(100)
    result = []
    for r in rows:
        d = r["_id"]
        result.append({
            "date": f"{d['year']}-{d['month']:02d}-{d['day']:02d}",
            "queries": r["count"],
            "avg_confidence": round(r["avg_confidence"], 2),
            "avg_latency_ms": round(r["avg_latency"], 1),
        })
    return {"trends": result}


@router.get("/tool-usage")
async def tool_usage(current_user: UserInDB = Depends(require_manager_or_admin)):
    """Breakdown of which pipeline tool answered queries."""
    pipeline = [
        {"$match": {"event": "query"}},
        {"$group": {"_id": "$answer_source", "count": {"$sum": 1}}},
    ]
    rows = await analytics_collection().aggregate(pipeline).to_list(20)
    return {"tool_usage": [{"source": r["_id"], "count": r["count"]} for r in rows]}


@router.get("/pipeline-performance")
async def pipeline_performance(current_user: UserInDB = Depends(require_manager_or_admin)):
    """Latency and confidence distribution buckets."""
    pipeline = [
        {"$match": {"event": "query"}},
        {"$facet": {
            "latency_buckets": [
                {"$bucket": {
                    "groupBy": "$latency_ms",
                    "boundaries": [0, 500, 1000, 2000, 5000, 10000],
                    "default": "10000+",
                    "output": {"count": {"$sum": 1}},
                }}
            ],
            "confidence_buckets": [
                {"$bucket": {
                    "groupBy": "$confidence_score",
                    "boundaries": [0, 3, 5, 7, 9, 10],
                    "default": "other",
                    "output": {"count": {"$sum": 1}},
                }}
            ],
        }},
    ]
    result = await analytics_collection().aggregate(pipeline).to_list(1)
    return result[0] if result else {}
