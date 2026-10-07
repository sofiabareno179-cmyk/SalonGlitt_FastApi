"""Liveness endpoint. The mobile app calls it before showing the login form."""
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.models import Usuario
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
async def readiness(db: AsyncSession = Depends(get_db)) -> dict[str, object]:
    """Check the registration table without writing data or exposing credentials."""
    try:
        await db.execute(text("SELECT 1"))
        actual_columns = await db.run_sync(
            lambda session: {
                column["name"]
                for column in inspect(session.connection()).get_columns("usuario")
            }
        )
    except SQLAlchemyError:
        logger.exception("Readiness check failed while checking the database")
        raise HTTPException(
            status_code=503,
            detail={
                "status": "not_ready",
                "check": "database",
                "message": "No se pudo consultar la base de datos.",
            },
        ) from None

    expected_columns = set(Usuario.__table__.columns.keys())
    missing_columns = sorted(expected_columns - actual_columns)
    if missing_columns:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "not_ready",
                "check": "usuario_schema",
                "missing_columns": missing_columns,
            },
        )

    return {
        "status": "ready",
        "service": settings.app_name,
        "checks": {"database": "ok", "usuario_schema": "ok"},
    }