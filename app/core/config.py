"""Application settings loaded from environment variables.

Secrets never live in this file: they are read from the process
environment or from a local .env that is git-ignored.
"""
import json
from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


def _origenes_por_defecto() -> list[str]:
    """Orígenes de desarrollo. En producción los declara SGE_CORS_ORIGINS."""
    return [
        "http://localhost:8030",      # React admin panel
        "http://127.0.0.1:8030",
        "http://localhost:3000",      # flutter run -d chrome
    ]


class Settings(BaseSettings):
    """Typed configuration. A missing required value aborts startup."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="SGE_",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "SGE-API"
    api_prefix: str = "/api/v1"
    debug: bool = False

    # Prefijo bajo el que se publica la API, sin barra final.
    #
    # Vacío en el caso normal: Coolify enruta el dominio entero al contenedor
    # y las rutas reales ya son /health y /api/v1/... Sin embargo, si el proxy
    # publica la API bajo un prefijo (por ejemplo https://salon.example.com/api),
    # hay que declararlo aquí o Swagger genera URLs sin ese prefijo y el
    # botón "Try it out" devuelve 404 contra el dominio real.
    root_path: str = ""

    # No defaults on purpose: startup must fail loudly when a secret
    # is missing. Both values come from SGE_SECRET_KEY and
    # SGE_DATABASE_URL in the git-ignored .env file.
    secret_key: str
    database_url: str

    @field_validator("secret_key")
    @classmethod
    def _exigir_clave_larga(cls, valor: str) -> str:
        """Rechaza claves demasiado cortas para HS256.

        Sin este chequeo, una clave de cinco caracteres arranca el servicio sin
        quejarse y el problema solo aparece como un `InsecureKeyLengthWarning`
        repetido en cada petición, días después del despliegue y sin relación
        visible con su causa. Fallar aquí es más ruidoso y, por tanto, más útil.
        """
        if len(valor) < 32:
            raise ValueError(
                "SGE_SECRET_KEY debe tener al menos 32 caracteres para HS256; "
                "genere una con: python -c \"import secrets; "
                "print(secrets.token_urlsafe(32))\""
            )
        return valor

    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = Field(default=60, ge=5, le=1440)

    # Origins allowed to call this API from a browser.
    # Native Flutter (Android/iOS) does NOT send Origin, so it is unaffected.
    #
    # Configurable porque la lista fija de desarrollo deja fuera al panel de
    # React servido desde el dominio de producción: el navegador bloquea la
    # respuesta y el panel ve errores de CORS en cada llamada. En Coolify se
    # declara SGE_CORS_ORIGINS como JSON, p. ej. '["https://panel.example.com"]'.
    #
    # `NoDecode` es imprescindible: sin él, pydantic-settings intenta parsear
    # cualquier variable de tipo lista como JSON y lanza SettingsError antes de
    # que el validador vea el valor. Eso convertía "a.com,b.com" en un fallo de
    # arranque, que es justo la forma más fácil de que alguien no entienda qué
    # escribir en la pestaña de Coolify.
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=_origenes_por_defecto
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _normalizar_origenes(cls, valor: object) -> object:
        """Acepta tanto JSON como una lista separada por comas.

        pydantic-settings entrega las variables complejas ya parseadas desde
        JSON, pero alguien escribirá `a.com,b.com` en la pestaña de Coolify
        porque es lo natural. Aceptar las dos formas evita un fallo de arranque
        confuso por un formato de lista.
        """
        if isinstance(valor, str):
            texto = valor.strip()
            if not texto:
                return []
            if texto.startswith("["):
                return json.loads(texto)
            return [origen.strip() for origen in texto.split(",") if origen.strip()]
        return valor

    @field_validator("root_path")
    @classmethod
    def _normalizar_root_path(cls, valor: str) -> str:
        """Quita la barra final: `root_path="/api/"` rompería las URLs."""
        return valor.rstrip("/")


@lru_cache
def get_settings() -> Settings:
    """Cached accessor so the .env file is parsed only once."""
    return Settings()