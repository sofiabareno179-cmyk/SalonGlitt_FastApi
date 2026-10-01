"""CRUD de notificaciones y recordatorios."""
from fastapi import APIRouter

from app.models import Notificaciones, Recordatorios
from app.routers.crud import build_crud_router
from app.schemas.entities import (
    NotificacionesCreate,
    NotificacionesRead,
    RecordatoriosCreate,
    RecordatoriosRead,
)

router = APIRouter()
router.include_router(
    build_crud_router(
        Notificaciones,
        NotificacionesCreate,
        NotificacionesRead,
        prefix="/notificaciones",
        tags=["notificaciones"],
    )
)
router.include_router(
    build_crud_router(
        Recordatorios,
        RecordatoriosCreate,
        RecordatoriosRead,
        prefix="/recordatorios",
        tags=["recordatorios"],
    )
)