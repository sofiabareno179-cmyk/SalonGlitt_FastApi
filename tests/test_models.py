"""The ORM metadata must match the existing salon database."""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Agenda,
    Base,
    Bloqueos,
    ProductoProveedores,
    Productos,
    Proveedores,
    ServicioProductos,
    Servicios,
    Usuario,
)

TABLAS_ESPERADAS = {
    "agenda": {"idagenda", "diasemana", "horainicio", "horafin", "idusuario"},
    "bloqueos": {
        "idbloqueo",
        "fecha",
        "hora_inicio",
        "hora_fin",
        "motivo",
        "idusuario",
        "created_at",
    },
    "catalogo_precios": {
        "idcatalogo",
        "nombre",
        "descripcion",
        "precio",
        "categoria",
        "fecha_creacion",
    },
    "citas": {"idcitas", "fechahora", "estado", "idusuario", "servicio"},
    "galeria": {
        "idgaleria",
        "titulo",
        "archivo",
        "descripcion",
        "fecha_subida",
        "tipo",
    },
    "inventario": {"idinventario", "stock", "fecha", "idproductos", "tipo"},
    "notificaciones": {
        "idnotificacion",
        "idusuario",
        "titulo",
        "mensaje",
        "leida",
        "fecha_creacion",
    },
    "perfiles": {"id", "nombre", "apellido", "bio", "idusuario"},
    "producto_proveedores": {"producto_id", "proveedor_id"},
    "productos": {"idproductos", "nombre", "descripcion", "precio", "categoria"},
    "promociones": {"idpromocion", "titulo", "descripcion", "activa", "updated_at"},
    "proveedores": {
        "idproveedores",
        "nombre_empresa",
        "contacto_nombre",
        "telefono",
        "email",
        "direccion",
    },
    "recordatorios": {
        "idrecordatorios",
        "titulo",
        "mensaje",
        "fecha_recordatorio",
        "idusuario",
    },
    "servicio_productos": {"servicio_id", "producto_id"},
    "servicios": {
        "idservicio",
        "nombre",
        "precio",
        "duracion",
        "categoria",
        "idcitas",
        "imagen",
        "tip",
    },
    "usuario": {
        "idusuario",
        "nombreuser",
        "email",
        "password_hash",
        "telefono",
        "rol",
    },
}


def test_metadata_cuadra_con_las_tablas_y_columnas_de_postgresql() -> None:
    """Every mapped table and physical column matches the inspected schema."""
    assert set(Base.metadata.tables) == set(TABLAS_ESPERADAS)
    for table_name, columns in TABLAS_ESPERADAS.items():
        assert set(Base.metadata.tables[table_name].columns.keys()) == columns


def test_claves_primarias_compuestas_del_esquema() -> None:
    """Both association tables use their real two-column primary keys."""
    assert [column.name for column in inspect(ProductoProveedores).primary_key] == [
        "producto_id",
        "proveedor_id",
    ]
    assert [column.name for column in inspect(ServicioProductos).primary_key] == [
        "servicio_id",
        "producto_id",
    ]


async def test_servicio_conserva_precio_decimal(sesion: AsyncSession) -> None:
    servicio = Servicios(
        nombre="Corte",
        precio=Decimal("45.50"),
        duracion="30 min",
        categoria="Cabello",
    )
    sesion.add(servicio)
    await sesion.commit()
    await sesion.refresh(servicio)

    assert isinstance(servicio.precio, Decimal)
    assert servicio.precio == Decimal("45.50")


async def test_agenda_conserva_las_horas_como_texto(
    sesion: AsyncSession,
) -> None:
    usuario = Usuario(
        nombreuser="ana",
        email="ana@salon.test",
        password_hash="hash",
        rol="cliente",
    )
    sesion.add(usuario)
    await sesion.flush()
    sesion.add(
        Agenda(
            dia_semana="lunes",
            hora_inicio="09:30",
            hora_fin="18:00",
            usuario_id=usuario.id,
        )
    )
    await sesion.commit()

    agenda = await sesion.scalar(select(Agenda))
    assert agenda is not None
    assert (agenda.dia_semana, agenda.hora_inicio, agenda.hora_fin) == (
        "lunes",
        "09:30",
        "18:00",
    )


async def test_claves_foraneas_reales_impiden_usuarios_inexistentes(
    sesion: AsyncSession,
) -> None:
    sesion.add(
        Bloqueos(
            fecha=date(2026, 1, 1),
            hora_inicio="09:00",
            hora_fin="10:00",
            usuario_id=999,
        )
    )

    with pytest.raises(IntegrityError):
        await sesion.commit()
    await sesion.rollback()


async def test_relaciones_de_proveedores_no_se_replican(
    sesion: AsyncSession,
) -> None:
    producto = Productos(nombre="Shampoo", precio=8.0, categoria="Cuidado")
    proveedor = Proveedores(
        nombre_empresa="Distribuidora",
        contacto_nombre="Ana",
        telefono="555",
    )
    sesion.add_all([producto, proveedor])
    await sesion.flush()
    sesion.add_all(
        [
            ProductoProveedores(
                producto_id=producto.id,
                proveedor_id=proveedor.id,
            ),
            ProductoProveedores(
                producto_id=producto.id,
                proveedor_id=proveedor.id,
            ),
        ]
    )

    with pytest.raises(IntegrityError):
        await sesion.commit()
    await sesion.rollback()
