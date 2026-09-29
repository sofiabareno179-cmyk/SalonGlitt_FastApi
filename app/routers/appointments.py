"""CRUD de citas, agendas y horarios bloqueados."""
from fastapi import APIRouter

from app.models import Agenda, Citas, SlotsBloqueados
from app.routers.crud import build_crud_router
from app.schemas.entities import (
    AgendaCreate,
    AgendaRead,
    CitasCreate,
    CitasRead,
    SlotsBloqueadosCreate,
    SlotsBloqueadosRead,
)

router = APIRouter()
router.include_router(build_crud_router(Citas, CitasCreate, CitasRead, prefix="/citas", tags=["citas"]))
router.include_router(build_crud_router(Agenda, AgendaCreate, AgendaRead, prefix="/agenda", tags=["agenda"]))
router.include_router(
    build_crud_router(
        SlotsBloqueados,
        SlotsBloqueadosCreate,
        SlotsBloqueadosRead,
        prefix="/slots-bloqueados",
        tags=["slots-bloqueados"],
    )
)