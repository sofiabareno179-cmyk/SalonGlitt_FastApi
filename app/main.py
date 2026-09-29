"""Punto de entrada de la API de Salon Glitt.

El engine se configura de forma perezosa para que `/health` siga respondiendo
sin que PostgreSQL tenga que estar disponible durante el arranque.
"""
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.database import engine
from app.routers import appointments, auth, catalog, communications, health, inventory, users

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Libera el pool al apagar; el engine conecta de forma perezosa."""
    yield
    await engine.dispose()


def create_app() -> FastAPI:
    """Fábrica de la aplicación. Las pruebas construyen su propia instancia."""
    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        docs_url="/docs",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    for api_router in (
        auth.router,
        users.router,
        appointments.router,
        catalog.router,
        inventory.router,
        communications.router,
    ):
        app.include_router(api_router, prefix=settings.api_prefix)
    return app


app = create_app()
