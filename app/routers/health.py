"""Liveness endpoint. The mobile app calls it before showing the login form."""
from fastapi import APIRouter

from app.core.config import get_settings
from app.schemas.common import HealthResponse

router = APIRouter(tags=["health"])
settings = get_settings()


@router.get("/health", response_model=HealthResponse, summary="Service liveness")
async def health() -> HealthResponse:
    """Return 200 when the process is alive.

    Deliberately does NOT hit the database: this endpoint answers
    "is the server up?", not "is everything working?". Mixing both
    makes a slow query look like a dead server to the mobile client.
    """
    return HealthResponse(status="ok", service=settings.app_name, version="1.0.0")