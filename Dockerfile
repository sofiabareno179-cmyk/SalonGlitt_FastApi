# SGE-API · imagen de la API.
#
# Python 3.13 y no `latest`: las versiones fijadas en requirements.txt tienen
# ruedas compiladas para 3.13. Con 3.14, pip intentaria compilar `asyncpg` y
# `pydantic-core` desde el codigo fuente y fallaria, porque la imagen no trae
# compilador de C ni de Rust.

FROM python:3.13-slim

# `-B` evita escribir .pyc en el contenedor (no sirve de nada dentro de una
# imagen de un solo uso) y `-u` deja la salida sin búfer para que `docker logs`
# muestre los logs en el momento, no por lotes.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /srv/app

# Capa de dependencias aparte del codigo: mientras requirements.txt no cambie,
# Docker reutiliza esta capa y reconstruir tras editar `app/` tarda segundos.
#
# Ojo: este archivo mezcla dependencias de ejecución y de desarrollo (pytest,
# ruff, mypy, bandit). Se instala entero a proposito — es el mismo archivo que
# usa quien desarrolla, y partirlo en dos seria una occasion mas de que las
# versiones se desincronicen. Cuando la imagen vaya a produccion, partirlo en
# `requirements.txt` y `requirements-dev.txt` es el siguiente paso natural.
COPY requirements.txt ./
RUN python -m venv /opt/venv \
 && /opt/venv/bin/pip install --upgrade pip \
 && /opt/venv/bin/pip install -r requirements.txt

ENV PATH="/opt/venv/bin:$PATH"

# Solo `app/`. Las pruebas no van dentro: se ejecutan en la integración continua
# (ver .github/workflows/ci.yml), no en el contenedor de servicio.
COPY app ./app

# root dentro del contenedor es una puerta abierta de más. Este usuario no
# escribe en el sistema de archivos, así que uid sin privilegios.
RUN useradd --create-home --uid 10001 sge \
 && chown -R sge:sge /srv/app
USER sge

# 8025 y no 8000: es el puerto que documenta el README y el que espera el
# emulador de Android.
EXPOSE 8025

# /health es público y NO consulta la base de datos (ver app/routers/health.py),
# justo por eso sirve como indicador de vida: si la base está lenta, el
# orquestador no debe declarar muerto un proceso que está perfectamente sano.
#
# `curl` no viene en python:slim, así que el chequeo se hace con urllib, que
# es de la biblioteca estándar.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import urllib.request, sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8025/health', timeout=4).status == 200 else 1)"]

# Sin `--reload`: recarga los módulos en caliente en producción y con el pool de
# conexiones abierto puede dejar sesiones colgando.
#
# `--forwarded-allow-ips=*` no es opcional detrás de Coolify. Con `--proxy-headers`
# a secas, uvicorn solo confía en los headers `X-Forwarded-*` que llegan de
# 127.0.0.1; el proxy de Coolify los envía desde otra IP de la red interna, así que
# se ignoran. El síntoma es un `request.url` con esquema http en una app servida
# por https, que rompe la URL del servidor en OpenAPI y las redirecciones de
# OAuth2. El comodín es aceptable porque el contenedor no está expuesto: solo
# alcanza a hablar con él el proxy, que es justamente quien debe firmar esos headers.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8025", "--proxy-headers", "--forwarded-allow-ips=*"]