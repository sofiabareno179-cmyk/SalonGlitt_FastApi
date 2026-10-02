"""La primera prueba, y la que debe pasar antes de escribir nada más.

Comprueba dos cosas a la vez: que la aplicación se construye sin errores de
importación y que el endpoint de salud responde con la forma declarada. Si esta
prueba falla, el problema es del entorno, no del código que venga después.
"""
import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import get_settings
from app.main import create_app


@pytest.mark.asyncio
async def test_health_responde_ok() -> None:
    """GET /health devuelve 200 con status, service y version."""
    app = create_app()

    # ASGITransport habla con la aplicación en el mismo proceso, sin abrir un
    # puerto: es rápido y determinista. Tiene una consecuencia que conviene
    # saber desde ya: el `lifespan` NO se ejecuta.
    transporte = ASGITransport(app=app)
    async with AsyncClient(transport=transporte, base_url="http://test") as cliente:
        respuesta = await cliente.get("/health")

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["status"] == "ok"
    assert "service" in cuerpo
    assert "version" in cuerpo


async def test_health_no_toca_la_base(cliente: AsyncClient) -> None:
    """/health responde sin token y sin base de datos.

    Es deliberado: la app móvil llama a este endpoint antes de mostrar el
    formulario de login, así que no puede depender de PostgreSQL.
    """
    respuesta = await cliente.get("/health")

    assert respuesta.status_code == 200
    assert respuesta.json()["service"] == get_settings().app_name


async def test_openapi_documenta_los_routers(cliente: AsyncClient) -> None:
    """El esquema generado incluye las rutas de auth y las de la API v1."""
    respuesta = await cliente.get("/openapi.json")

    assert respuesta.status_code == 200
    rutas = respuesta.json()["paths"]
    assert "/health" in rutas
    assert "/api/v1/auth/login" in rutas
    assert "/api/v1/servicios" in rutas
    assert "/api/v1/usuarios" in rutas


async def test_docs_esta_disponible(cliente: AsyncClient) -> None:
    """La interfaz de Swagger se sirve sin autenticacion."""
    respuesta = await cliente.get("/docs")

    assert respuesta.status_code == 200


async def test_cors_permite_el_origen_del_panel(cliente: AsyncClient) -> None:
    """El panel de React en localhost:8030 puede llamar a la API."""
    respuesta = await cliente.get(
        "/health", headers={"Origin": "http://localhost:8030"}
    )

    assert respuesta.headers["access-control-allow-origin"] == "http://localhost:8030"


async def test_cors_no_refleja_un_origen_desconocido(cliente: AsyncClient) -> None:
    """Un origen fuera de la lista no recibe permiso de CORS."""
    respuesta = await cliente.get("/health", headers={"Origin": "https://sitio-malicioso.test"})

    assert "access-control-allow-origin" not in respuesta.headers


async def test_ruta_inexistente_es_404(cliente: AsyncClient) -> None:
    """Una ruta no registrada responde 404 con el detalle estándar de FastAPI."""
    respuesta = await cliente.get("/api/v1/no-existe")

    assert respuesta.status_code == 404


async def test_raiz_redirige_a_docs(cliente: AsyncClient) -> None:
    """GET / redirige a /docs para evitar 404 al abrir la URL base."""
    respuesta = await cliente.get("/", follow_redirects=False)

    assert respuesta.status_code == 307
    assert respuesta.headers["location"] == "/docs"