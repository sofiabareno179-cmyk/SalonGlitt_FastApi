"""CRUD de servicios, precios y galeria."""
from fastapi import APIRouter

from app.models import CatalogoPrecios, Galeria, Promociones, Servicios
from app.routers.crud import build_crud_router
from app.schemas.entities import (
    CatalogoPreciosCreate,
    CatalogoPreciosRead,
    GaleriaCreate,
    GaleriaRead,
    PromocionesCreate,
    PromocionesRead,
    ServiciosCreate,
    ServiciosRead,
)

router = APIRouter()
router.include_router(
    build_crud_router(
        Servicios,
        ServiciosCreate,
        ServiciosRead,
        prefix="/servicios",
        tags=["servicios"],
    )
)
router.include_router(
    build_crud_router(
        CatalogoPrecios,
        CatalogoPreciosCreate,
        CatalogoPreciosRead,
        prefix="/catalogo-precios",
        tags=["catalogo-precios"],
    )
)
router.include_router(
    build_crud_router(
        Galeria, GaleriaCreate, GaleriaRead, prefix="/galeria", tags=["galeria"]
    )
)
router.include_router(
    build_crud_router(
        Promociones,
        PromocionesCreate,
        PromocionesRead,
        prefix="/promociones",
        tags=["promociones"],
    )
)