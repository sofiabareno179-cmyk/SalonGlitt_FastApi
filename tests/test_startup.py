"""El arranque del servidor en un despliegue real.

Estas pruebas cubren el `lifespan`, que `ASGITransport` no ejecuta. Es
justamente lo que ocurre en Coolify: la aplicacion levanta, `/health` responde y
todo lo demas depende de que este bloque haya creado el esquema.
"""
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

import app.main as main
from app.core.database import engine as engine_global
from app.core.database import get_db
from app.main import create_app


@asynccontextmanager
async def _lifespan_con_engine(motor: AsyncEngine) -> AsyncIterator[None]:
    """Ejecuta el lifespan real apuntando el engine global a la base de prueba.

    Se sustituye `app.main.engine` porque es el objeto que el lifespan usa para
    crear el esquema; tocarlo es la unica forma de probarlo sin abrir una
    conexion a PostgreSQL de verdad.
    """
    main.engine = motor  # type: ignore[assignment]
    try:
        async with main.lifespan(create_app()):
            yield
    finally:
        main.engine = engine_global  # type: ignore[assignment]


@pytest.mark.asyncio
async def test_lifespan_crea_el_esquema(motor: AsyncEngine) -> None:
    """Tras el arranque, las tablas del modelo existen.

    Sin esto, una base recien inicializada en Coolify daria «no such table» en
    todas las rutas de /api/v1 aunque /health respondiera 200.
    """
    async with _lifespan_con_engine(motor):
        async with motor.connect() as conexion:
            nombres = await conexion.run_sync(
                lambda sync_conexion: inspect(sync_conexion).get_table_names()
            )

    assert "usuario" in nombres
    assert "servicios" in nombres


@pytest.mark.asyncio
async def test_lifespan_es_idempotente(motor: AsyncEngine) -> None:
    """Levantar dos veces no falla: es lo que pasa en cada reinicio."""
    async with _lifespan_con_engine(motor):
        pass
    async with _lifespan_con_engine(motor):
        pass


@pytest.mark.asyncio
async def test_arranque_no_falla_si_la_base_no_responde() -> None:
    """Con la base caida la app igual levanta y `/health` responde 200.

    Es lo que evita que el orquestador declare muerto un proceso sano: si el
    arranque abortara aqui, no habria nada que distinguir «la base tarda» de
    «la aplicacion esta rota».
    """

    class _EngineRoto:
        def begin(self) -> None:
            raise RuntimeError("la base no responde")

        async def dispose(self) -> None:
            return None

    main.engine = _EngineRoto()  # type: ignore[assignment]
    try:
        app = create_app()
        async with main.lifespan(app):
            transporte = ASGITransport(app=app)
            async with AsyncClient(transport=transporte, base_url="http://t") as cliente:
                respuesta = await cliente.get("/health")

        assert respuesta.status_code == 200
    finally:
        main.engine = engine_global  # type: ignore[assignment]


@pytest.mark.asyncio
async def test_esquema_creado_sirve_de_verdad(motor: AsyncEngine) -> None:
    """Una ruta real de la API funciona contra el esquema creado en el arranque."""
    app = create_app()
    factory = async_sessionmaker(motor, expire_on_commit=False)

    async def _get_db_de_prueba() -> AsyncIterator[AsyncSession]:
        async with factory() as s:
            yield s

    app.dependency_overrides[get_db] = _get_db_de_prueba
    try:
        async with _lifespan_con_engine(motor):
            transporte = ASGITransport(app=app)
            async with AsyncClient(transport=transporte, base_url="http://t") as cliente:
                # 401 y no 500: el token falta, pero la consulta llego a la base.
                respuesta = await cliente.get("/api/v1/usuarios")
    finally:
        app.dependency_overrides.clear()

    assert respuesta.status_code == 401