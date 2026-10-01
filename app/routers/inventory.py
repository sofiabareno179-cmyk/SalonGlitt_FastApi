"""CRUD de productos, proveedores y movimientos de inventario."""
from fastapi import APIRouter

from app.models import (
    Inventario,
    ProductoProveedores,
    Productos,
    Proveedores,
    ServicioProductos,
)
from app.routers.crud import build_crud_router
from app.schemas.entities import (
    InventarioCreate,
    InventarioRead,
    ProductoProveedoresCreate,
    ProductoProveedoresRead,
    ProductosCreate,
    ProductosRead,
    ProveedoresCreate,
    ProveedoresRead,
    ServicioProductosCreate,
    ServicioProductosRead,
)

router = APIRouter()
router.include_router(
    build_crud_router(
        Productos,
        ProductosCreate,
        ProductosRead,
        prefix="/productos",
        tags=["productos"],
    )
)
router.include_router(
    build_crud_router(
        Proveedores,
        ProveedoresCreate,
        ProveedoresRead,
        prefix="/proveedores",
        tags=["proveedores"],
    )
)
router.include_router(
    build_crud_router(
        Inventario,
        InventarioCreate,
        InventarioRead,
        prefix="/inventario",
        tags=["inventario"],
    )
)
router.include_router(
    build_crud_router(
        ProductoProveedores,
        ProductoProveedoresCreate,
        ProductoProveedoresRead,
        prefix="/producto-proveedores",
        tags=["producto-proveedores"],
    )
)
router.include_router(
    build_crud_router(
        ServicioProductos,
        ServicioProductosCreate,
        ServicioProductosRead,
        prefix="/servicio-productos",
        tags=["servicio-productos"],
    )
)