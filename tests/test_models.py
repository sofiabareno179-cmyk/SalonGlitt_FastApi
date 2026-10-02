"""Modelos SQLAlchemy: tipos, restricciones y relaciones.

Estas pruebas hablan con la base directamente (`sesion`) en lugar de con la
API, porque lo que se verifica aqui es el mapeo: que un `Numeric(10, 2)`
vuelva como `Decimal` y no como `float`, que `Time` no pierda precision, o que
la restricion unica de `usuario.email` exista de verdad en el esquema.
"""
from datetime import date, datetime, time
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models import (
    Agenda,
    CatalogoPrecios,
    Citas,
    Galeria,
    Inventario,
    Notificaciones,
    Perfiles,
    ProductoProveedores,
    Productos,
    Proveedores,
    Recordatorios,
    ServicioProductos,
    Servicios,
    Usuario,
)

# Tabla donde vive cada relacion en cascada de Usuario, para no repetir el
# `select` en el test parametrizado.
HIJOS = {"perfil": Perfiles, "agenda": Agenda, "notificaciones": Notificaciones}


async def test_precios_vuelven_como_decimal(sesion: AsyncSession) -> None:
    """Un importe monetario no debe degradarse a coma flotante al leerlo."""
    servicio = Servicios(nombre="Corte", duracion_minutos=30, precio=Decimal("45.50"))
    sesion.add(servicio)
    await sesion.commit()

    await sesion.refresh(servicio)

    assert isinstance(servicio.precio, Decimal)
    assert servicio.precio == Decimal("45.50")


async def test_hora_y_fecha_se_conservan(sesion: AsyncSession) -> None:
    """`Time` y `Date` se guardan tal cual, sin zona horaria ni truncamiento."""
    usuario = Usuario(
        nombre="Luis",
        apellido="Soto",
        email="luis@salon.test",
        password_hash=hash_password("Contrasena1"),
    )
    sesion.add(usuario)
    await sesion.commit()
    sesion.add(
        Agenda(
            usuario_id=usuario.id,
            dia_semana=2,
            hora_inicio=time(9, 30),
            hora_fin=time(18, 0),
        )
    )
    await sesion.commit()

    agenda = await sesion.scalar(select(Agenda).where(Agenda.usuario_id == usuario.id))

    assert agenda is not None
    assert agenda.hora_inicio == time(9, 30)
    assert agenda.hora_fin == time(18, 0)


async def test_email_unico_en_la_base(sesion: AsyncSession) -> None:
    """La restriccion `unique` del modelo llega hasta el esquema, no es solo Python."""
    sesion.add_all(
        [
            Usuario(
                nombre="Ana",
                apellido="Ruiz",
                email="ana@salon.test",
                password_hash=hash_password("Contrasena1"),
            ),
            Usuario(
                nombre="Otra",
                apellido="Persona",
                email="ana@salon.test",
                password_hash=hash_password("Contrasena1"),
            ),
        ]
    )

    with pytest.raises(IntegrityError):
        await sesion.commit()
    await sesion.rollback()


async def test_cita_exige_usuario_y_servicio(sesion: AsyncSession) -> None:
    """Una cita sin usuario ni servicio viola las FK y no se guarda en silencio."""
    from app.models import Citas

    sesion.add(
        Citas(
            usuario_id=999,
            servicio_id=999,
            fecha_inicio=datetime(2026, 1, 1, 10, 0),
            fecha_fin=datetime(2026, 1, 1, 11, 0),
        )
    )

    with pytest.raises(IntegrityError):
        await sesion.commit()
    await sesion.rollback()


async def test_perfil_es_uno_por_usuario(sesion: AsyncSession) -> None:
    """`Perfiles.usuario_id` es unico: un segundo perfil es un error de integridad."""
    usuario = Usuario(
        nombre="Ana",
        apellido="Ruiz",
        email="ana@salon.test",
        password_hash=hash_password("Contrasena1"),
    )
    sesion.add(usuario)
    await sesion.commit()
    sesion.add_all([Perfiles(usuario_id=usuario.id), Perfiles(usuario_id=usuario.id)])

    with pytest.raises(IntegrityError):
        await sesion.commit()
    await sesion.rollback()


async def test_relacion_usuario_perfil_navega_en_ambos_sentidos(
    sesion: AsyncSession,
) -> None:
    """`back_populates` deja ir de Usuario a Perfiles y volver."""
    usuario = Usuario(
        nombre="Ana",
        apellido="Ruiz",
        email="ana@salon.test",
        password_hash=hash_password("Contrasana1"),
    )
    usuario.perfil = Perfiles(rol="admin")
    sesion.add(usuario)
    await sesion.commit()

    perfil = await sesion.scalar(select(Perfiles))

    assert perfil is not None
    assert perfil.rol == "admin"
    assert perfil.usuario.email == "ana@salon.test"


@pytest.mark.parametrize(
    "atributo_hijo",
    ["perfil", "agenda", "notificaciones"],
)
async def test_cascada_al_borrar_usuario(
    sesion: AsyncSession, atributo_hijo: str
) -> None:
    """Las relaciones con `ondelete="CASCADE"` se borran con su padre.

    Sin `cascade="all, delete-orphan"` en la relacion, el ORM hacia
    `UPDATE hijo SET fk = NULL` y reventaba el NOT NULL. El nombre de la
    relacion va parametrizado porque las tres comparten el mismo fallo y
    basta un fallo para romper el borrado del usuario.
    """
    usuario = Usuario(
        nombre="Ana",
        apellido="Ruiz",
        email="ana@salon.test",
        password_hash=hash_password("Contrasena1"),
    )
    if atributo_hijo == "perfil":
        usuario.perfil = Perfiles(rol="cliente")
    elif atributo_hijo == "agenda":
        usuario.agenda = [Agenda(dia_semana=1, hora_inicio=time(9, 0), hora_fin=time(18, 0))]
    else:
        usuario.notificaciones = [Notificaciones(titulo="Hola", mensaje="Tu cita es manana")]
    sesion.add(usuario)
    await sesion.commit()

    await sesion.delete(usuario)
    await sesion.commit()

    assert await sesion.scalar(select(HIJOS[atributo_hijo])) is None


async def test_el_historico_de_inventario_sobrevive_al_usuario(
    sesion: AsyncSession,
) -> None:
    """`Inventario.usuario_id` declara SET NULL: el movimiento no se borra.

    Es el contrapunto del test anterior: sin este, alguien podria "arreglar"
    el borrado en cascada anadiendo delete-orphan a todas las relaciones y
    destruir el historial de inventario del salon.
    """
    usuario = Usuario(
        nombre="Ana",
        apellido="Ruiz",
        email="ana@salon.test",
        password_hash=hash_password("Contrasena1"),
    )
    producto = Productos(nombre="Shampoo", stock=5, stock_minimo=1, precio_compra=Decimal("8.00"))
    usuario.movimientos_inventario = [
        Inventario(producto=producto, tipo="entrada", cantidad=5)
    ]
    sesion.add(usuario)
    await sesion.commit()
    movimiento_id = usuario.movimientos_inventario[0].id

    await sesion.delete(usuario)
    await sesion.commit()

    movimiento = await sesion.get(Inventario, movimiento_id)
    assert movimiento is not None
    assert movimiento.usuario_id is None


async def test_producto_proveedores_no_se_repite(sesion: AsyncSession) -> None:
    """`UniqueConstraint("producto_id", "proveedor_id")` impide el vinculo duplicado."""
    producto = Productos(nombre="Shampoo", stock=10, stock_minimo=2, precio_compra=Decimal("8.00"))
    proveedor = Proveedores(nombre="Distribuidora Norte")
    sesion.add_all([producto, proveedor])
    await sesion.commit()
    sesion.add_all(
        [
            ProductoProveedores(producto_id=producto.id, proveedor_id=proveedor.id),
            ProductoProveedores(producto_id=producto.id, proveedor_id=proveedor.id),
        ]
    )

    with pytest.raises(IntegrityError):
        await sesion.commit()
    await sesion.rollback()


async def test_catalogo_precios_conserva_la_vigencia(sesion: AsyncSession) -> None:
    """Un precio con `vigencia_hasta` se recupera tal como se guardo."""
    servicio = Servicios(nombre="Color", duracion_minutos=60, precio=Decimal("70.00"))
    sesion.add(servicio)
    await sesion.commit()
    sesion.add(
        CatalogoPrecios(
            servicio_id=servicio.id,
            precio=Decimal("65.00"),
            vigencia_desde=date(2026, 1, 1),
            vigencia_hasta=date(2026, 6, 30),
        )
    )
    await sesion.commit()

    precio = await sesion.scalar(select(CatalogoPrecios))

    assert precio is not None
    assert precio.vigencia_desde == date(2026, 1, 1)
    assert precio.vigencia_hasta == date(2026, 6, 30)


async def test_cascada_al_borrar_una_cita(sesion: AsyncSession) -> None:
    """Los recordatorios de una cita se van con ella."""
    usuario = Usuario(
        nombre="Ana",
        apellido="Ruiz",
        email="ana@salon.test",
        password_hash=hash_password("Contrasena1"),
    )
    servicio = Servicios(nombre="Corte", duracion_minutos=30, precio=Decimal("30.00"))
    cita = Citas(
        usuario=usuario,
        servicio=servicio,
        fecha_inicio=datetime(2026, 1, 1, 10, 0),
        fecha_fin=datetime(2026, 1, 1, 10, 30),
    )
    cita.recordatorios = [Recordatorios(programado_para=datetime(2026, 1, 1, 9, 0))]
    sesion.add(cita)
    await sesion.commit()

    await sesion.delete(cita)
    await sesion.commit()

    assert await sesion.scalar(select(Recordatorios)) is None


async def test_cascada_al_borrar_un_servicio(sesion: AsyncSession) -> None:
    """Los precios historicos se van con el servicio, la galeria no.

    `CatalogoPrecios` declara ondelete="CASCADE" y `Galeria` SET NULL: son
    decisiones distintas sobre el mismo padre y el test las fija las dos.
    """
    servicio = Servicios(nombre="Color", duracion_minutos=60, precio=Decimal("70.00"))
    servicio.precios = [
        CatalogoPrecios(precio=Decimal("70.00"), vigencia_desde=date(2026, 1, 1))
    ]
    servicio.galeria = [Galeria(titulo="Antes", imagen_url="https://cdn/a.jpg")]
    sesion.add(servicio)
    await sesion.commit()

    await sesion.delete(servicio)
    await sesion.commit()

    assert await sesion.scalar(select(CatalogoPrecios)) is None
    foto = await sesion.scalar(select(Galeria))
    assert foto is not None
    assert foto.servicio_id is None


async def test_servicio_productos_pide_cantidad_positiva(sesion: AsyncSession) -> None:
    """La cantidad viene de `ServicioProductos`; el modelo fija un default de 1."""
    servicio = Servicios(nombre="Manicure", duracion_minutos=45, precio=Decimal("20.00"))
    producto = Productos(nombre="Esmalte", stock=5, stock_minimo=1, precio_compra=Decimal("3.50"))
    sesion.add_all([servicio, producto])
    await sesion.commit()
    vinculo = ServicioProductos(servicio_id=servicio.id, producto_id=producto.id)
    sesion.add(vinculo)
    await sesion.commit()

    await sesion.refresh(vinculo)

    assert vinculo.cantidad == Decimal("1")