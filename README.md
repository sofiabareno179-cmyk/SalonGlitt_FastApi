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

## Con Docker

Si prefiere no instalar PostgreSQL ni el entorno virtual en el sistema:

```bash
copy .env.example .env         # y rellene SGE_SECRET_KEY
docker compose up --build
```

Se levantan dos servicios: PostgreSQL 16 y la API. La API espera a que la base
pase su healthcheck antes de arrancar, de modo que no se connects contra un
servidor que todavía no acepta conexiones. La base queda en el puerto 5434 del
host (dentro de la red de Compose va al 5432).

```bash
docker compose logs -f api     # ver la salida
docker compose down            # parar; conserva los datos
docker compose down -v         # parar y borrar también el volumen
```

> Ojo: `requirements.txt` no crea tablas. Levantar el contenedor deja la API
> responding en `/health`, pero cualquier ruta que consulte la base fallará con
> «no such table» hasta que se creen las tablas.

## Qué trae ya, y qué falta

| Pieza | Estado | Se construye en |
|---|---|---|
| Estructura de paquetes | ✅ lista | — |
| `requirements.txt` con versiones fijas | ✅ lista | — |
| `pyproject.toml` (ruff, mypy, bandit) | ✅ lista | — |
| `.env.example` y `.gitignore` | ✅ listos | — |
| `Dockerfile`, `docker-compose.yml`, `.dockerignore` | ✅ listos | — |
| `app/core/config.py` | ✅ listo | M1 |
| `app/routers/health.py` | ✅ listo | M1 |
| `app/schemas/common.py` | ✅ mínimo | M2 lo amplía con `Page` |
| Integración continua | ✅ lista | M9 la explica |
| `app/schemas/entities.py` | ✅ esquemas de entrada/salida | — |
| `app/core/database.py`, `app/models.py` | ✅ SQLAlchemy async | — |
| `app/routers/*` | ✅ CRUD, autenticación y usuarios | — |
| `app/services/*` | ❌ falta | Lógica de negocio posterior |
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

## Routers disponibles

Las rutas CRUD se montan bajo `/api/v1` y requieren `Authorization: Bearer <token>`.
El registro y el login son públicos; el token JWT se obtiene en `POST /api/v1/auth/login`.

| Router | Recursos |
|---|---|
| `auth` y `users` | registro, login, usuario, perfiles |
| `appointments` | citas, agenda, slots bloqueados |
| `catalog` | servicios, catálogo de precios, galería |
| `inventory` | productos, proveedores, inventario y relaciones |
| `communications` | notificaciones, recordatorios |

Cada recurso incluye `GET` de lista y detalle, `POST`, `PATCH` parcial y `DELETE`.
`/health` permanece público y no consulta la base de datos.

## Credenciales

No hay ninguna en este paquete, y no debe haberla. Las de desarrollo van en
`.env`, que está en `.gitignore`. Si algún día `.env` aparece en `git status`,
deténgase antes de hacer commit.
