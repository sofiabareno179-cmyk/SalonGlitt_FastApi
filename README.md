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
pase su healthcheck antes de arrancar, de modo que no se conecta contra un
servidor que todavía no acepta conexiones.

Los puertos se publican solo en desarrollo local, y lo hace
`docker-compose.override.yml`: la API en `http://localhost:8025` y la base en
`127.0.0.1:5434` (el 5432 del host suele estar tomado por la instalación local
de PostgreSQL). Ese archivo **no** se aplica en Coolify, porque ahí se invoca
`docker compose -f docker-compose.yml` y con `-f` explícito Compose deja de
cargar los overrides automáticos. En el servidor no se publica ningún puerto: el
proxy llega a la API por la red interna.

```bash
docker compose logs -f api     # ver la salida
docker compose down            # parar; conserva los datos
docker compose down -v         # parar y borrar también el volumen
```

> Ojo: en el despliegue, `docker-compose.yml` no publica puertos. Si el dominio
> responde 404 o «port is already allocated», casi siempre es que un puerto se
> reapareció en el archivo principal por error.

> Las tablas se crean solas al arrancar el proceso (`create_all` en el
> `lifespan`), de forma idempotente. Aun así, `create_all` no altera columnas de
> tablas que ya existen: en cuanto cambie un modelo hace falta una migración real
> (Alembic ya está en `requirements.txt`) y no basta con reiniciar.

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

`/` responde 200 con un JSON pequeño (no una redirección). Es a propósito: el
chequeo de salud del proxy consulta la raíz y no sigue redirecciones, así que un
307 ahí hacía que Coolify sirviera su propia página de 404.

| Router | Recursos |
|---|---|
| `auth` y `users` | registro, login, usuario, perfiles |
| `appointments` | citas, agenda, slots bloqueados |
| `catalog` | servicios, catálogo de precios, galería |
| `inventory` | productos, proveedores, inventario y relaciones |
| `communications` | notificaciones, recordatorios |

Cada recurso incluye `GET` de lista y detalle, `POST`, `PATCH` parcial y `DELETE`.
`/health` permanece público y no consulta la base de datos.

## Despliegue en Coolify

Resource tipo **Docker Compose**, apuntando a la rama `main`.

**Variables de entorno** (todas obligatorias salvo indicación):

| Variable | Obligatoria | Nota |
|---|---|---|
| `SGE_SECRET_KEY` | sí | mínimo 32 caracteres. `python -c "import secrets; print(secrets.token_urlsafe(32))"` |
| `SGE_DATABASE_URL` | con base propia | ver abajo |
| `POSTGRES_PASSWORD` | con base propia | solo si se usa el servicio `db` del compose |
| `SGE_CORS_ORIGINS` | en producción | origen del panel React. JSON o lista con comas |
| `POSTGRES_USER` / `POSTGRES_DB` | no | por defecto `sge` |
| `SGE_ROOT_PATH` | no | vacío salvo que el proxy use un prefijo de ruta |

**Base de datos administrada por Coolify** (la opción recomendada): declare
`SGE_DATABASE_URL` con la URL que muestra el panel, **con dos cambios**:

- prefijo `SGE_`, porque la app lee el entorno con ese prefijo
  (`app/core/config.py`); un `DATABASE_URL` a secas se ignora en silencio
- driver `postgresql+asyncpg`, no `postgresql`: la URL que da Coolify apunta a
  psycopg2, que es síncrono y no está instalado, así que el engine fallaría al
  construirse

```
SGE_DATABASE_URL=postgresql+asyncpg://<usuario>:<clave>@postgres-db-xxxx:5432/<base>
```

Con esa variable declarada, `docker-compose.yml` deja de apuntar a su propio
servicio `db`. Si además quiere quitar ese servicio (la base administrada lo
hace redundante), borre el bloque `db` y el `depends_on` de `api`.

**Dominio:** `api.tudominio.com:8025`. El puerto es obligatorio: el contenedor
escucha en 8025 y sin el sufijo el proxy busca en 80 y no lo encuentra.

**No declare `ports` en la pestaña de dominio.** `docker-compose.yml` ya no
publica ningún puerto; el proxy llega al contenedor por la red interna. Declarar
un puerto ahí reserva un puerto del servidor y es una causa frecuente de
despliegues que no levantan.

Tres fallos que cuestan un despliegue, y qué significan:

| Síntoma | Causa |
|---|---|
| 404 al abrir el dominio | falta `:8025` en el dominio, o se declaró un puerto en la pestaña de dominio |
| «port is already allocated» | un puerto del host ya ocupado; quite el `ports` del servicio |
| 200 en `/health` pero error en `/api/v1` | `SGE_CORS_ORIGINS` sin el origen del panel, o la base sin tablas |
| el contenedor reinicia en bucle | falta `SGE_SECRET_KEY`, o tiene menos de 32 caracteres |

## Credenciales

No hay ninguna en este paquete, y no debe haberla. Las de desarrollo van en
`.env`, que está en `.gitignore`. Si algún día `.env` aparece en `git status`,
deténgase antes de hacer commit.
