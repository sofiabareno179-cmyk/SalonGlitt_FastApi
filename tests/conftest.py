"""Configuracion de entorno aislado para las pruebas."""
import os

os.environ.setdefault("SGE_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("SGE_DATABASE_URL", "sqlite+aiosqlite:///:memory:")

# A partir de aqui se importa la aplicacion: las variables anteriores ya estan
# fijadas, que es la unica razon por la que este archivo no tiene mas codigo
# antes de los imports.
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.main import create_app, create_cors_app
from app.models import Base

# Credenciales del usuario de prueba. La contrasena cumple el minimo de 8
# caracteres que exige `UsuarioCreate`; el resto de pruebas la reutilizan.
EMAIL_PRUEBA = "ana@salon.test"
PASSWORD_PRUEBA = "Contrasena1"


@pytest_asyncio.fixture
async def motor() -> AsyncIterator[AsyncEngine]:
    """Engine sobre una base SQLite en memoria, con el esquema ya creado.

    `StaticPool` es obligatorio aqui: sin el, cada sesion abriria su propia
    conexion y cada conexion de SQLite en memoria tiene una base DISTINTA, de
    modo que las tablas creadas en un test desaparecerian a mitad del camino.
    """
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )

    # SQLite ignora las claves foraneas salvo que se pida explicitamente.
    # Sin este pragma, una cita apuntando a un usuario inexistente se
    # guardaria sin quejarse y las pruebas darian un falso OK donde
    # PostgreSQL habria dado un error.
    @event.listens_for(engine.sync_engine, "connect")
    def _activar_claves_foraneas(dbapi_connection: object, _record: object) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as conexion:
        await conexion.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def sesion(motor: AsyncEngine) -> AsyncIterator[AsyncSession]:
    """Sesion para hablar con la base directamente, sin pasar por la API."""
    factory = async_sessionmaker(motor, expire_on_commit=False)
    async with factory() as s:
        yield s


@pytest_asyncio.fixture
async def cliente(motor: AsyncEngine) -> AsyncIterator[AsyncClient]:
    """Cliente HTTP contra la app, con `get_db` apuntando a la base de prueba.

    Se sustituye la dependencia en vez de tocar `app.core.database.engine` a
    proposito: asi el engine global --el que usaria el servidor real-- nunca
    se abre contra la base de pruebas.
    """
    app = create_app()
    factory = async_sessionmaker(motor, expire_on_commit=False)

    async def _get_db_de_prueba() -> AsyncIterator[AsyncSession]:
        async with factory() as s:
            yield s

    app.dependency_overrides[get_db] = _get_db_de_prueba
    transporte = ASGITransport(app=create_cors_app(app))
    async with AsyncClient(transport=transporte, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def email() -> str:
    """Correo del usuario de prueba."""
    return EMAIL_PRUEBA


@pytest.fixture
def password() -> str:
    """Contrasena del usuario de prueba."""
    return PASSWORD_PRUEBA


@pytest.fixture
def registro(email: str, password: str) -> dict[str, str]:
    """Cuerpo valido para `POST /api/v1/auth/register`."""
    return {
        "nombreuser": "ana",
        "email": email,
        "password": password,
        "rol": "cliente",
    }


@pytest_asyncio.fixture
async def token(cliente: AsyncClient, registro: dict[str, str]) -> str:
    """Token valido de un usuario ya registrado, listo para el header Bearer."""
    await cliente.post("/api/v1/auth/register", json=registro)
    respuesta = await cliente.post(
        "/api/v1/auth/login",
        json={"email": registro["email"], "password": registro["password"]},
    )
    return respuesta.json()["access_token"]


@pytest.fixture
def auth(token: str) -> dict[str, str]:
    """Cabecera `Authorization` lista para pasar a `cliente.get(...)`."""
    return {"Authorization": f"Bearer {token}"}