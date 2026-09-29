"""Punto de entrada del esqueleto de SGE-API.

Esta versión monta SOLO el endpoint de salud y no abre conexión con la base de
datos, para que el servicio arranque sin PostgreSQL levantado. Es a propósito:
el primer día lo que hace falta es comprobar que el entorno funciona, no que
todo el sistema funciona.

El `main.py` del módulo 1 —con `lifespan`, CORS, manejadores de error y los
cuatro routers— es hacia donde este archivo evoluciona. Sustitúyalo cuando
esas piezas existan: hacerlo antes produce un `ImportError` en el arranque.
"""
from fastapi import FastAPI

from app.core.config import get_settings
from app.routers import health

settings = get_settings()


def create_app() -> FastAPI:
    """Fábrica de la aplicación. Las pruebas construyen su propia instancia."""
    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        docs_url="/docs",
        openapi_url="/openapi.json",
    )
    app.include_router(health.router)
    return app


app = create_app()
