"""Ajustes de la aplicacion.

`get_settings` esta cacheado con `lru_cache` a proposito, asi que hay que
comprobar que el cache existe (leer el `.env` en cada peticion seria un
problema) sin romperlo para el resto de la suite.
"""
import pytest
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.database import get_db


def test_secret_key_es_obligatoria(monkeypatch: pytest.MonkeyPatch) -> None:
    """Sin SGE_SECRET_KEY la aplicacion no arranca: es un fallo ruidoso y temprano."""
    monkeypatch.delenv("SGE_SECRET_KEY", raising=False)

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_database_url_es_obligatoria(monkeypatch: pytest.MonkeyPatch) -> None:
    """Sin SGE_DATABASE_URL tampoco hay arranque."""
    monkeypatch.delenv("SGE_DATABASE_URL", raising=False)

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_los_secretos_vienen_del_entorno(monkeypatch: pytest.MonkeyPatch) -> None:
    """El prefijo SGE_ es el que conecta .env con el modelo."""
    monkeypatch.setenv("SGE_SECRET_KEY", "clave-de-prueba-de-32-caracteres-minimo")
    monkeypatch.setenv("SGE_DATABASE_URL", "sqlite+aiosqlite:///./prueba.db")
    monkeypatch.setenv("SGE_DEBUG", "true")

    ajustes = Settings(_env_file=None)

    assert ajustes.secret_key == "clave-de-prueba-de-32-caracteres-minimo"
    assert ajustes.database_url == "sqlite+aiosqlite:///./prueba.db"
    assert ajustes.debug is True


def test_clave_de_firma_corta_se_rechaza(monkeypatch: pytest.MonkeyPatch) -> None:
    """Una clave de cinco caracteres no debe poder firmar tokens.

    Sin este chequeo el servicio arrancaba sin avisar y el problema aparecia
    despues como un aviso de PyJWT repetido en cada peticion, sin relacion
    visible con su causa.
    """
    monkeypatch.setenv("SGE_SECRET_KEY", "corta")

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_clave_de_firma_larga_se_acepta(monkeypatch: pytest.MonkeyPatch) -> None:
    """El limite son 32 caracteres, y lo justo debe pasar."""
    monkeypatch.setenv("SGE_SECRET_KEY", "x" * 32)

    assert Settings(_env_file=None).secret_key == "x" * 32


def test_expiracion_del_token_esta_acotada(monkeypatch: pytest.MonkeyPatch) -> None:
    """Un token de 10080 minutos (una semana) es un error de configuracion."""
    monkeypatch.setenv("SGE_ACCESS_TOKEN_EXPIRE_MINUTES", "10080")

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_get_settings_esta_cacheado() -> None:
    """Dos llamadas devuelven la MISMA instancia: el .env se lee una vez."""
    assert get_settings() is get_settings()


def test_valores_por_defecto_del_entorno_de_pruebas() -> None:
    """Defaults que el resto de la suite da por ciertos (prefijo y origenes)."""
    ajustes = get_settings()

    assert ajustes.api_prefix == "/api/v1"
    assert ajustes.jwt_algorithm == "HS256"
    assert "http://localhost:8030" in ajustes.cors_origins


def test_cors_origins_acepta_json(monkeypatch: pytest.MonkeyPatch) -> None:
    """En Coolify se declara como JSON: es la forma que documenta el README."""
    monkeypatch.setenv(
        "SGE_CORS_ORIGINS", '["https://panel.example.com","https://salon.example.com"]'
    )

    ajustes = Settings(_env_file=None)

    assert ajustes.cors_origins == [
        "https://panel.example.com",
        "https://salon.example.com",
    ]


def test_cors_origins_acepta_lista_con_comas(monkeypatch: pytest.MonkeyPatch) -> None:
    """La lista con comas es lo que se escribe uno sin leer la documentación."""
    monkeypatch.setenv("SGE_CORS_ORIGINS", "https://a.example.com, https://b.example.com")

    ajustes = Settings(_env_file=None)

    assert ajustes.cors_origins == ["https://a.example.com", "https://b.example.com"]


def test_cors_origins_vacio_significa_sin_lista(monkeypatch: pytest.MonkeyPatch) -> None:
    """Sin la variable se conservan los orígenes de desarrollo."""
    monkeypatch.delenv("SGE_CORS_ORIGINS", raising=False)

    ajustes = Settings(_env_file=None)

    assert "http://localhost:8030" in ajustes.cors_origins


def test_cors_origins_cadena_vacia_conserva_los_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    """`SGE_CORS_ORIGINS=""` no debe cerrar el CORS.

    docker-compose.yml inyecta la variable vacía cuando nadie la declara en
    Coolify. Con la lista vacía, el panel recibía 403 de origen en cada
    llamada mientras /health seguía verde.
    """
    monkeypatch.setenv("SGE_CORS_ORIGINS", "")

    ajustes = Settings(_env_file=None)

    assert "http://localhost:8030" in ajustes.cors_origins
    assert ajustes.cors_origins != []


def test_root_path_puede_declararse_por_entorno(monkeypatch: pytest.MonkeyPatch) -> None:
    """Publicar la API bajo un prefijo de ruta debe ser configurable."""
    monkeypatch.setenv("SGE_ROOT_PATH", "/api")

    assert Settings(_env_file=None).root_path == "/api"


def test_root_path_no_deja_barra_final(monkeypatch: pytest.MonkeyPatch) -> None:
    """`/api/` generaria URLs con doble barra y las rutas responderian 404."""
    monkeypatch.setenv("SGE_ROOT_PATH", "/api/")

    assert Settings(_env_file=None).root_path == "/api"


async def test_get_db_entrega_una_sesion() -> None:
    """La dependencia real abre y cierra una sesion.

    El resto de la suite la sustituye con `dependency_overrides`, asi que sin
    esta prueba `get_db` --el camino que usa el servidor de verdad-- no lo
    ejecutaria nadie.
    """
    generador = get_db()
    sesion = await anext(generador)
    try:
        assert isinstance(sesion, AsyncSession)
    finally:
        await generador.aclose()