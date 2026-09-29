"""La primera prueba, y la que debe pasar antes de escribir nada más.

Comprueba dos cosas a la vez: que la aplicación se construye sin errores de
importación y que el endpoint de salud responde con la forma declarada. Si esta
prueba falla, el problema es del entorno, no del código que venga después.
"""
import pytest
from httpx import ASGITransport, AsyncClient

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
