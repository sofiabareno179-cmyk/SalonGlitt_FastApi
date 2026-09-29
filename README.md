# SGE-API · paquete de arranque

Esqueleto del microservicio que se construye en la Guía FastAPI. **No es el
proyecto terminado**: arranca, responde `/health` y tiene la configuración de
calidad puesta. El resto se escribe siguiendo los módulos.

## Arranque en tres pasos

```bash
python -m venv .venv
.venv\Scripts\activate        # en Windows;  source .venv/bin/activate en Linux
pip install -r requirements.txt
```

Copie `.env.example` como `.env` y rellene los marcadores. La clave de firma se
genera con:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Y arranque:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8025
```

El `--host 0.0.0.0` no es opcional si va a consumir esta API desde el emulador
de Android en la estación siguiente: con el valor por defecto (`127.0.0.1`) el
servidor solo acepta conexiones del propio computador.

Compruebe <http://localhost:8025/health> y <http://localhost:8025/docs>.

## Qué trae ya, y qué falta

| Pieza | Estado | Se construye en |
|---|---|---|
| Estructura de paquetes | ✅ lista | — |
| `requirements.txt` con versiones fijas | ✅ lista | — |
| `pyproject.toml` (ruff, mypy, bandit) | ✅ lista | — |
| `.env.example` y `.gitignore` | ✅ listos | — |
| `app/core/config.py` | ✅ listo | M1 |
| `app/routers/health.py` | ✅ listo | M1 |
| `app/schemas/common.py` | ✅ mínimo | M2 lo amplía con `Page` |
| Integración continua | ✅ lista | M9 la explica |
| `app/schemas/*` | ❌ falta | **M2** |
| `app/core/database.py`, `app/models/*` | ❌ falta | **M3** |
| `app/routers/*`, `app/services/*` | ❌ falta | **M4** |
| `app/dependencies.py` | ❌ falta | **M5** |
| `app/core/security.py`, `app/routers/auth.py` | ❌ falta | **M6** |
| `app/core/exceptions.py` | ❌ falta | **M7** |
| Paquete de entrega (`docs/`) | ❌ falta | **M8** |
| Suite de pruebas completa | ❌ falta | **Transferencia** |

## Verificación

```bash
pytest                    # la prueba de /health ya pasa
ruff check .
mypy --strict app/
bandit -r app/ -ll
```

Los cuatro deben salir limpios **antes** de añadir código nuevo. Si el
esqueleto ya viene con hallazgos, no se sabrá cuáles introdujo el aprendiz.

## El `main.py` de este esqueleto no es el final

Aquí monta solo `/health` y no toca la base de datos, para que arranque sin
PostgreSQL. El `main.py` del módulo 1 —con `lifespan`, CORS, manejadores de
error y los cuatro routers— es hacia donde este evoluciona. Se sustituye
cuando esas piezas existan; hacerlo antes produce un `ImportError` en el
arranque que despista.

## Credenciales

No hay ninguna en este paquete, y no debe haberla. Las de desarrollo van en
`.env`, que está en `.gitignore`. Si algún día `.env` aparece en `git status`,
deténgase antes de hacer commit.
