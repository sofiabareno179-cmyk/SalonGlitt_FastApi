"""La primera prueba, y la que debe pasar antes de escribir nada más.

Comprueba dos cosas a la vez: que la aplicación se construye sin errores de
importación y que el endpoint de salud responde con la forma declarada. Si esta
prueba falla, el problema es del entorno, no del código que venga después.
"""
from collections.abc import AsyncIterator
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.main import create_app, create_cors_app


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


async def test_readiness_confirma_la_base_y_el_esquema_de_usuario(
    cliente: AsyncClient,
) -> None:
    """El diagnóstico de solo lectura valida las columnas usadas al registrar."""
    respuesta = await cliente.get("/health/ready")

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "status": "ready",
        "service": get_settings().app_name,
        "checks": {"database": "ok", "usuario_schema": "ok"},
    }


async def test_readiness_devuelve_diagnostico_si_falla_la_consulta() -> None:
    """Un fallo de DB produce 503 con diagnóstico, no un 500 genérico."""
    app = create_app()

    sesion_rota = AsyncMock(spec=AsyncSession)
    sesion_rota.execute.side_effect = SQLAlchemyError("error de base de datos")

    async def _db_rota() -> AsyncIterator[AsyncSession]:
        yield sesion_rota

    app.dependency_overrides[get_db] = _db_rota
    transporte = ASGITransport(app=create_cors_app(app))
    async with AsyncClient(transport=transporte, base_url="http://test") as cliente:
        respuesta = await cliente.get("/health/ready")

    assert respuesta.status_code == 503
    assert respuesta.json()["detail"] == {
        "status": "not_ready",
        "check": "database_or_usuario_schema",
        "error_type": "SQLAlchemyError",
        "message": (
            "No se pudo consultar la tabla usuario con las columnas "
            "esperadas por el registro."
        ),
    }


async def test_openapi_documenta_los_routers(cliente: AsyncClient) -> None:
    """El esquema generado incluye las rutas de auth y las de la API v1."""
    respuesta = await cliente.get("/openapi.json")

    assert respuesta.status_code == 200
    rutas = respuesta.json()["paths"]
    assert "/health" in rutas
    assert "/health/ready" in rutas
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


@pytest.mark.parametrize(
    "origen",
    ["http://localhost:58061", "http://127.0.0.1:58061"],
)
async def test_cors_permite_puertos_dinamicos_de_flutter_web(
    cliente: AsyncClient, origen: str
) -> None:
    """Flutter Web puede usar un puerto local distinto en cada ejecución."""
    respuesta = await cliente.get("/health", headers={"Origin": origen})

    assert respuesta.headers["access-control-allow-origin"] == origen


async def test_cors_preflight_permite_flutter_web(cliente: AsyncClient) -> None:
    """El login JSON de Flutter Web pasa el preflight desde un puerto dinámico."""
    origen = "http://localhost:58061"
    respuesta = await cliente.options(
        "/api/v1/auth/login",
        headers={
            "Origin": origen,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,authorization",
        },
    )

    assert respuesta.status_code == 200
    assert respuesta.headers["access-control-allow-origin"] == origen


async def test_cors_se_incluye_en_errores_500() -> None:
    """El navegador debe poder leer errores internos, no ocultarlos como CORS."""
    app = create_app()

    @app.get("/error-prueba")
    async def error_prueba() -> None:
        raise RuntimeError("fallo interno de prueba")

    transporte = ASGITransport(
        app=create_cors_app(app),
        raise_app_exceptions=False,
    )
    async with AsyncClient(transport=transporte, base_url="http://test") as cliente:
        respuesta = await cliente.get(
            "/error-prueba",
            headers={"Origin": "http://localhost:59794"},
        )

    assert respuesta.status_code == 500
    assert respuesta.headers["access-control-allow-origin"] == "http://localhost:59794"


async def test_cors_no_refleja_un_origen_desconocido(cliente: AsyncClient) -> None:
    """Un origen fuera de la lista no recibe permiso de CORS."""
    respuesta = await cliente.get("/health", headers={"Origin": "https://sitio-malicioso.test"})

    assert "access-control-allow-origin" not in respuesta.headers


async def test_ruta_inexistente_es_404(cliente: AsyncClient) -> None:
    """Una ruta no registrada responde 404 con el detalle estándar de FastAPI."""
    respuesta = await cliente.get("/api/v1/no-existe")

    assert respuesta.status_code == 404


async def test_raiz_responde_200(cliente: AsyncClient) -> None:
    """GET / responde 200 con la ubicación de la documentación.

    No puede ser una redirección: el chequeo de salud del proxy de Coolify se
    hace contra la raíz y no sigue redirecciones, así que un 307 lo tomaba por
    servicio caído y el dominio acababa sirviendo la página de 404 del proxy.
    """
    respuesta = await cliente.get("/")

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["docs"] == "/docs"
    assert cuerpo["health"] == "/health"


async def test_raiz_no_requiere_autenticacion(cliente: AsyncClient) -> None:
    """La raíz es pública, igual que /health."""
    respuesta = await cliente.get("/", headers={"Authorization": ""})

    assert respuesta.status_code == 200