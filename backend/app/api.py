"""Mounts the website and AI gateway routers under /api/v1."""
from fastapi import APIRouter

from app.ai_gateway import router as ai
from app.web.routers import admin, members, prices, products, search, stats, stores

router = APIRouter(prefix="/api/v1")

router.include_router(stores.router)
router.include_router(members.router)
router.include_router(admin.router)
router.include_router(products.router)
router.include_router(prices.router)
router.include_router(stats.router)
router.include_router(search.router)
router.include_router(ai.router)
