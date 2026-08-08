from app.api.chat import router as chat_router
from app.api.documents import router as documents_router
from app.api.analytics import router as analytics_router
from app.api.admin import router as admin_router

__all__ = ["chat_router", "documents_router", "analytics_router", "admin_router"]
