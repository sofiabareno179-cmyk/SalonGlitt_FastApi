"""CRUD de citas, agendas y horarios bloqueados."""
from fastapi import APIRouter

from app.models import Agenda, Bloqueos, Citas
from app.routers.crud import build_crud_router
from app.schemas.entities import (
    AgendaCreate,
    AgendaRead,
    BloqueosCreate,
    BloqueosRead,
    CitasCreate,
    CitasRead,
)

router = APIRouter()
router.include_router(
    build_crud_router(
        Citas, CitasCreate, CitasRead, prefix="/citas", tags=["citas"]
    )
)
router.include_router(
    build_crud_router(
        Agenda, AgendaCreate, AgendaRead, prefix="/agenda", tags=["agenda"]
    )
)
router.include_router(
    build_crud_router(
        Bloqueos,
        BloqueosCreate,
        BloqueosRead,
        prefix="/bloqueos",
        tags=["bloqueos"],
    )
)