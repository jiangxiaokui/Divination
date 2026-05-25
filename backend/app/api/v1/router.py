from fastapi import APIRouter

from app.api.v1.users import router as users_router
from app.api.v1.readings import router as readings_router
from app.api.v1.lots import router as lots_router
from app.api.v1.history import router as history_router
from app.api.v1.admin import router as admin_router
from app.api.v1.kb import router as kb_router
from app.api.v1.site_gate import router as site_gate_router

router = APIRouter(prefix="/api/v1")
router.include_router(site_gate_router)
router.include_router(users_router)
router.include_router(readings_router)
router.include_router(lots_router)
router.include_router(history_router)
router.include_router(admin_router)
router.include_router(kb_router)
