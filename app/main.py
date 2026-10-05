"""Punto de entrada de la API de Salon Glitt.

El engine se configura de forma perezosa para que `/health` siga respondiendo
sin que PostgreSQL tenga que estar disponible durante el arranque.
"""
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.database import engine
from app.models import Base
from app.routers import appointments, auth, catalog, communications, health, inventory, users

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Crea el esquema al arrancar y libera el pool al apagar.

    `create_all` es idempotente: no toca las tablas que ya existen ni altera sus
    columnas. Es lo que permite que el despliegue en Coolify funcione sin un
    paso manual de migraciones, porque `requirements.txt` por sí solo no crea
    nada y una base recién inicializada no tiene ninguna tabla.

    Va dentro de un try/except a propósito: si la base todavía no acepta
    conexiones, el proceso debe igualmente levantarse y servir `/health`. Si no,
    el orquestador vería el contenedor muerto y no distinguiría "la base tarda"
    de "la aplicación está rota".
    """
    try:
        async with engine.begin() as conexion:
            await conexion.run_sync(Base.metadata.create_all)
    except Exception:  # el arranque no debe depender de que la base responda
        logging.getLogger(__name__).exception(
            "No se pudo crear el esquema; las rutas que consulten la base fallaran"
        )
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
        root_path=settings.root_path,
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

    @app.get("/", include_in_schema=False)
    async def root() -> dict[str, str]:
        """Responde 200 en la raíz, sin redireccionar.

        Antes esto devolvía un 307 hacia /docs y provocaba 404 en Coolify: el
        chequeo de salud del proxy se hace contra la raíz y no sigue
        redirecciones, así que un 307 lo interpretaba como servicio caído y
        terminaba sirviendo la página de 404 del proxy en vez de la API. Con un
        200 en la raíz, tanto el chequeo como quien abra el dominio a mano
        reciben algo útil.
        """
        return {
            "service": settings.app_name,
            "version": "1.0.0",
            "docs": "/docs",
            "health": "/health",
        }

    return app


app = create_app()
