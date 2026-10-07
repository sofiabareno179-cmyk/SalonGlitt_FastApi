"""Registro, inicio de sesion y resolucion del usuario autenticado.

Se prueba sobre la API completa (no sobre las funciones internas) porque lo
que importa es el contrato HTTP: codigos de estado, cabecera `WWW-Authenticate`
y que la contrasena nunca viaje de vuelta al cliente.
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession


async def test_registro_crea_la_cuenta(cliente: AsyncClient, registro: dict[str, str]) -> None:
    """POST /auth/register responde 201 y no filtra el hash de la contrasena."""
    respuesta = await cliente.post("/api/v1/auth/register", json=registro)

    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["email"] == registro["email"]
    assert cuerpo["nombreuser"] == registro["nombreuser"]
    assert cuerpo["rol"] == registro["rol"]
    assert cuerpo["id"] > 0
    # Ni `password` ni `password_hash` deben aparecer en la respuesta.
    assert "password" not in cuerpo
    assert "password_hash" not in cuerpo


async def test_registro_rechaza_correo_duplicado(
    cliente: AsyncClient, registro: dict[str, str]
) -> None:
    """El segundo alta con el mismo correo es 409, no 500."""
    await cliente.post("/api/v1/auth/register", json=registro)

    respuesta = await cliente.post("/api/v1/auth/register", json=registro)

    assert respuesta.status_code == 409
    assert respuesta.json()["detail"] == "El correo ya esta registrado"


async def test_registro_valida_el_cuerpo(cliente: AsyncClient, registro: dict[str, str]) -> None:
    """Una contrasena de menos de 8 caracteres se rechaza con 422."""
    respuesta = await cliente.post(
        "/api/v1/auth/register", json={**registro, "password": "corta"}
    )

    assert respuesta.status_code == 422


async def test_login_devuelve_bearer(
    cliente: AsyncClient, registro: dict[str, str], email: str, password: str
) -> None:
    """Credenciales correctas producen un token utilizable."""
    await cliente.post("/api/v1/auth/register", json=registro)

    respuesta = await cliente.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["token_type"] == "bearer"
    assert cuerpo["access_token"]


async def test_login_con_contrasena_incorrecta_es_401(
    cliente: AsyncClient, registro: dict[str, str], email: str
) -> None:
    """No se distingue 'usuario inexistente' de 'contrasena erronea' en el mensaje."""
    await cliente.post("/api/v1/auth/register", json=registro)

    respuesta = await cliente.post(
        "/api/v1/auth/login", json={"email": email, "password": "Contrasena999"}
    )

    assert respuesta.status_code == 401
    assert respuesta.json()["detail"] == "Correo o contrasena incorrectos"
    assert respuesta.headers["WWW-Authenticate"] == "Bearer"


async def test_login_de_usuario_inexistente_es_401(cliente: AsyncClient, password: str) -> None:
    """Mismo 401 que con contrasena erronea: no se filtra que correos existen."""
    respuesta = await cliente.post(
        "/api/v1/auth/login", json={"email": "nadie@salon.test", "password": password}
    )

    assert respuesta.status_code == 401


async def test_me_devuelve_el_usuario_del_token(
    cliente: AsyncClient, auth: dict[str, str], email: str
) -> None:
    """GET /auth/me resuelve la identidad a partir del bearer."""
    respuesta = await cliente.get("/api/v1/auth/me", headers=auth)

    assert respuesta.status_code == 200
    assert respuesta.json()["email"] == email


async def test_me_sin_token_es_401(cliente: AsyncClient) -> None:
    """Sin cabecera Authorization la respuesta es 401 y no 403."""
    respuesta = await cliente.get("/api/v1/auth/me")

    assert respuesta.status_code == 401
    assert respuesta.headers["WWW-Authenticate"] == "Bearer"


async def test_me_con_token_inventado_es_401(cliente: AsyncClient) -> None:
    """Una firma invalida no debe producir un 500 por jwt."""
    respuesta = await cliente.get(
        "/api/v1/auth/me", headers={"Authorization": "Bearer no.es.un.token"}
    )

    assert respuesta.status_code == 401


async def test_me_con_usuario_borrado_es_401(
    cliente: AsyncClient, auth: dict[str, str]
) -> None:
    """El token es valido en firma, pero el usuario ya no existe."""
    usuario_id = (await cliente.get("/api/v1/auth/me", headers=auth)).json()["id"]
    await cliente.delete(f"/api/v1/usuarios/{usuario_id}", headers=auth)

    respuesta = await cliente.get("/api/v1/auth/me", headers=auth)

    assert respuesta.status_code == 401


async def test_registro_con_carrera_de_duplicado_es_409(
    cliente: AsyncClient, registro: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Dos registros simultaneos con el mismo correo: uno gana, el otro 409.

    La comprobacion previa de `_register` no puede cubrir la carrera -- entre
    el SELECT y el INSERT cabe otra peticion --, por eso existe el
    `except IntegrityError`. Aqui se fuerza ese segundo camino.
    """

    async def _commit_roto(self: AsyncSession) -> None:
        raise IntegrityError("INSERT", {}, Exception("UNIQUE"))

    monkeypatch.setattr(AsyncSession, "commit", _commit_roto)

    respuesta = await cliente.post("/api/v1/auth/register", json=registro)

    assert respuesta.status_code == 409
    assert respuesta.json()["detail"] == "El correo ya esta registrado"