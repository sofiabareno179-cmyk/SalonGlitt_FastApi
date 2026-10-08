"""Liveness endpoint. The mobile app calls it before showing the login form."""
import logging

from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.schemas.common import HealthResponse

router = APIRouter(tags=["health"])
settings = get_settings()
logger = logging.getLogger(__name__)


@router.get("/health", response_model=HealthResponse, summary="Service liveness")
async def health() -> HealthResponse:
    """Return 200 when the process is alive.

    Deliberately does NOT hit the database: this endpoint answers
    "is the server up?", not "is everything working?". Mixing both
    makes a slow query look like a dead server to the mobile client.
    """
    return HealthResponse(status="ok", service=settings.app_name, version="1.0.0")


@router.get("/health/ready", summary="Check database readiness")
async def readiness() -> dict[str, object]:
    """Check the registration table without writing data or exposing credentials."""
    try:
        async with SessionLocal() as db:
            await db.execute(
                text(
                    "SELECT idusuario, nombreuser, email, password_hash, telefono, rol "
                    "FROM usuario LIMIT 0"
                )
            )
    except Exception as error:
        logger.exception("Readiness check failed while opening or querying the database")
        raise HTTPException(
            status_code=503,
            detail={
                "status": "not_ready",
                "check": "database_or_usuario_schema",
                "error_type": type(error).__name__,
                "message": (
                    "No se pudo consultar la tabla usuario con las columnas "
                    "esperadas por el registro."
                ),
            },
        ) from None

    return {
        "status": "ready",
        "service": settings.app_name,
        "checks": {"database": "ok", "usuario_schema": "ok"},
    }