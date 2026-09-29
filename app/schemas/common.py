"""Envolturas de respuesta compartidas.

De momento solo la de salud. En el módulo 2 se añade aquí `Page[T]`, la
envoltura paginada que devuelven todos los listados y de la que depende el
scroll infinito de la app móvil.
"""
from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Lo que devuelve GET /health."""

    status: str
    service: str
    version: str
