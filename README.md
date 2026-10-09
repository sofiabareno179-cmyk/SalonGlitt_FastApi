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

Compruebe <http://localhost:8025/health>,
<http://localhost:8025/health/ready> y <http://localhost:8025/docs>.
`/health/ready` comprueba la conexion de lectura y que la tabla `usuario`
contenga las columnas requeridas; no crea ni modifica datos.

## Con Docker

Si prefiere no instalar PostgreSQL ni el entorno virtual en el sistema:

```bash
copy .env.example .env         # y rellene SGE_SECRET_KEY y SGE_DATABASE_URL
docker network create coolify  # una sola vez: la red compartida de Coolify
docker compose up --build
```

Se levanta un solo servicio: la API. La base de datos no vive en este compose,
sino que es un recurso administrado por Coolify y se alcanza por la red
compartida `coolify` (declarada como externa en `docker-compose.yml`). El
hostname de la base (`postgres-db-...`) solo resuelve dentro de esa red.

El puerto se publica solo en desarrollo local, y lo hace
`docker-compose.override.yml`: la API en `http://localhost:8025`. Ese archivo
**no** se aplica en Coolify, porque ahí se invoca
`docker compose -f docker-compose.yml` y con `-f` explícito Compose deja de
cargar los overrides automáticos. En el servidor no se publica ningún puerto: el
proxy llega a la API por la red interna.

```bash
docker compose logs -f api     # ver la salida
docker compose down            # parar
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

Los modelos y esquemas de `app/` corresponden a los nombres físicos que existen
en PostgreSQL. Por ejemplo, el registro de usuario recibe `nombreuser`, las
citas usan `fecha_hora` y `servicio`, y los productos usan `precio` y
`categoria`; no se deben enviar campos de una versión anterior del esquema,
como `apellido` en `usuario`, `fecha_inicio` en `citas` o `stock` en `productos`.

`/` responde 200 con un JSON pequeño (no una redirección). Es a propósito: el
chequeo de salud del proxy consulta la raíz y no sigue redirecciones, así que un
307 ahí hacía que Coolify sirviera su propia página de 404.

| Router | Recursos |
|---|---|
| `auth` y `users` | registro, login, usuario, perfiles |
| `appointments` | citas, agenda, bloqueos |
| `catalog` | servicios, catálogo de precios, galería, promociones |
| `inventory` | productos, proveedores, inventario y relaciones |
| `communications` | notificaciones, recordatorios |

Cada recurso incluye `GET` de lista y detalle, `POST`, `PATCH` parcial y `DELETE`.
Las tablas de relación con clave primaria compuesta reciben ambas claves en la
ruta del detalle, actualización y borrado (por ejemplo,
`/producto-proveedores/{producto_id}/{proveedor_id}`).
`/health` permanece público y no consulta la base de datos.

## Despliegue en Coolify

Resource tipo **Docker Compose**, apuntando a la rama `main`.

**Variables de entorno** (todas obligatorias salvo indicación):

| Variable | Obligatoria | Nota |
|---|---|---|
| `SGE_SECRET_KEY` | sí | mínimo 32 caracteres. `python -c "import secrets; print(secrets.token_urlsafe(32))"` |
| `SGE_DATABASE_URL` | sí | URL interna del recurso de base de datos de Coolify; ver abajo |
| `SGE_CORS_ORIGINS` | en producción | origen del panel React. JSON o lista con comas |
| `SGE_ACCESS_TOKEN_EXPIRE_MINUTES` | no | por defecto 60, entre 5 y 1440 |
| `SGE_ROOT_PATH` | no | vacío salvo que el proxy use un prefijo de ruta |
| `SGE_DEBUG` | no | `false` en producción; `true` expone trazas completas |

> **El `.env` local no viaja a Coolify.** Está en `.gitignore` y
> `docker-compose.yml` no usa `env_file`, así que el contenedor nunca lo lee.
> El `.env` es copia de trabajo de la máquina de desarrollo; el valor real es
> el que se declara en la pestaña *Environment Variables* del recurso, con el
> mismo nombre (`SGE_DATABASE_URL`, no `DATABASE_URL`).

### Conectar la base de datos que ya existe en Coolify

1. **Mismo proyecto.** El recurso de la base y el de la API deben estar en el
   mismo proyecto de Coolify: así comparten red interna y el hostname
   `postgres-db-...` resuelve desde el contenedor de la API.
2. **Copiar los datos de la base.** En el recurso de la base, Coolify muestra
   hostname (o nombre de contenedor), puerto, usuario, contraseña y nombre de
   la base. Ese hostname solo resuelve dentro de la red de Coolify.
3. **Declarar la variable en la API.** Pestaña *Environment Variables* del
   recurso de la API:

   ```
   SGE_DATABASE_URL=postgresql+asyncpg://<usuario>:<clave>@postgres-db-xxxx:5432/<base>
   ```

   Tres cambios respecto a la URL que da Coolify:
   - prefijo `SGE_`, porque la app lee el entorno con ese prefijo
     (`app/core/config.py`); un `DATABASE_URL` a secas se ignora en silencio.
     Tampoco sirve `SGE_DATABASE_URL_COOLIFY` ni ningún otro alias: el nombre
     que lee el código es exactamente `SGE_DATABASE_URL`.
   - driver `postgresql+asyncpg`, no `postgresql`: la URL que da Coolify apunta
     a psycopg2, que es síncrono y no está instalado, así que el engine
     fallaría al construirse.
   - si la contraseña contiene `@`, `:`, `/` o `#`, URL-éncodela
     (`%40`, `%3A`, `%2F`, `%23`), o la URL se interpreta mal.
4. **CORS.** Flutter Web en desarrollo permite `localhost` y `127.0.0.1` con
   cualquier puerto (Flutter puede elegir uno distinto en cada ejecución).
   Para un panel desplegado, declara `SGE_CORS_ORIGINS` con cada origen exacto
   (esquema, dominio y puerto incluidos):
   `SGE_CORS_ORIGINS=["https://panel.tudominio.com"]`.
5. **Dominio de la API:** `api.tudominio.com:8025`. El puerto es obligatorio:
   el contenedor escucha en 8025 y sin el sufijo el proxy busca en 80 y no lo
   encuentra.

`docker-compose.yml` no define ningún servicio `db`: la API se conecta
exclusivamente a la base administrada por Coolify. El compose levanta solo la
API y la une a la red compartida `coolify` (bloque `networks`), que es donde
vive el recurso de la base. En el panel, esto equivale a activar
«Connect To Predefined Network» en *Configuration > Advanced* del recurso.

Para desarrollo local, `docker-compose.override.yml` publica la API en
`127.0.0.1:8025`. Como la red `coolify` se declara externa, créela una vez
antes de `docker compose up`:

```bash
docker network create coolify
```

**Verificación tras el despliegue:**

```bash
curl https://api.tudominio.com/health     # 200, no consulta la base
curl https://api.tudominio.com/docs       # 200
curl https://api.tudominio.com/api/v1/... # una ruta que sí toque la base
```

Si `/health` da 200 pero las rutas de la base fallan, mira los logs del
contenedor: lo normal es que `SGE_DATABASE_URL` no esté declarada, esté mal el
hostname o falte el `+asyncpg`.

**No declare `ports` en la pestaña de dominio.** `docker-compose.yml` ya no
publica ningún puerto; el proxy llega al contenedor por la red interna. Declarar
un puerto ahí reserva un puerto del servidor y es una causa frecuente de
despliegues que no levantan.

Cuatro fallos que cuestan un despliegue, y qué significan:

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
