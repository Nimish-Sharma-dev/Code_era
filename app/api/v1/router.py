"""Central API v1 router — mounts all sub-routers."""

from fastapi import APIRouter

from app.api.v1.routes.auth import router as auth_router
from app.api.v1.routes.users import router as users_router
from app.api.v1.routes.financial import router as financial_router
from app.api.v1.routes.market import router as market_router
from app.api.v1.routes.recommendations import router as recommendations_router
from app.api.v1.routes.chatbot import router as chatbot_router
from app.api.v1.routes.dashboard import router as dashboard_router
from app.api.v1.routes.admin import router as admin_router
from app.api.v1.routes.health import router as health_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(financial_router)
api_router.include_router(market_router)
api_router.include_router(recommendations_router)
api_router.include_router(chatbot_router)
api_router.include_router(dashboard_router)
api_router.include_router(admin_router)

from app.api.v1.routes.notifications import router as notifications_router
api_router.include_router(notifications_router)
