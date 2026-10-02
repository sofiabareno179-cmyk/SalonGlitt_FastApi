"""Modelos SQLAlchemy para la gestion del salon.

Los campos representan una propuesta inicial porque el DDL original no esta
incluido en el proyecto. Ajustar nombres y restricciones al esquema real.
"""
from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base declarativa comun para los modelos del proyecto."""


class Usuario(Base):
    __tablename__ = "usuario"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    apellido: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    telefono: Mapped[str | None] = mapped_column(String(30))
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # El `cascade` del ORM debe coincidir con el `ondelete` de la columna.
    # Sin el, SQLAlchemy pone la FK hija a NULL en vez de borrar el hijo, y
    # como estas columnas son NOT NULL el borrado del padre revienta con
    # IntegrityError. Por eso las relaciones con ondelete="CASCADE" --estas
    # tres-- lo declaran explicitamente.
    perfil: Mapped[Perfiles | None] = relationship(
        back_populates="usuario", uselist=False, cascade="all, delete-orphan"
    )
    citas: Mapped[list[Citas]] = relationship(
        back_populates="usuario", foreign_keys="Citas.usuario_id"
    )
    agenda: Mapped[list[Agenda]] = relationship(
        back_populates="usuario", cascade="all, delete-orphan"
    )
    notificaciones: Mapped[list[Notificaciones]] = relationship(
        back_populates="usuario", cascade="all, delete-orphan"
    )
    # `Inventario.usuario_id` declara ondelete="SET NULL": los movimientos son
    # un registro historico y sobreviven al borrado del usuario, asi que aqui
    # NO debe haber delete-orphan.
    movimientos_inventario: Mapped[list[Inventario]] = relationship(back_populates="usuario")


class Perfiles(Base):
    __tablename__ = "perfiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuario.id", ondelete="CASCADE"), unique=True
    )
    rol: Mapped[str] = mapped_column(String(40), default="cliente", nullable=False)
    foto_url: Mapped[str | None] = mapped_column(String(500))

    usuario: Mapped[Usuario] = relationship(back_populates="perfil")


class Agenda(Base):
    __tablename__ = "agenda"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuario.id", ondelete="CASCADE"))
    dia_semana: Mapped[int] = mapped_column(Integer, nullable=False)
    hora_inicio: Mapped[time] = mapped_column(Time, nullable=False)
    hora_fin: Mapped[time] = mapped_column(Time, nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    usuario: Mapped[Usuario] = relationship(back_populates="agenda")
    slots_bloqueados: Mapped[list[SlotsBloqueados]] = relationship(
        back_populates="agenda", cascade="all, delete-orphan"
    )


class Servicios(Base):
    __tablename__ = "servicios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text)
    duracion_minutos: Mapped[int] = mapped_column(Integer, nullable=False)
    precio: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    citas: Mapped[list[Citas]] = relationship(back_populates="servicio")
    precios: Mapped[list[CatalogoPrecios]] = relationship(
        back_populates="servicio", cascade="all, delete-orphan"
    )
    # `Galeria.servicio_id` declara ondelete="SET NULL": una foto suelta sigue
    # valiendo aunque se retire el servicio, asi que no se borra en cascada.
    galeria: Mapped[list[Galeria]] = relationship(back_populates="servicio")
    productos: Mapped[list[ServicioProductos]] = relationship(
        back_populates="servicio", cascade="all, delete-orphan"
    )


class Citas(Base):
    __tablename__ = "citas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuario.id"))
    servicio_id: Mapped[int] = mapped_column(ForeignKey("servicios.id"))
    profesional_id: Mapped[int | None] = mapped_column(ForeignKey("usuario.id"))
    fecha_inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fecha_fin: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    estado: Mapped[str] = mapped_column(String(30), default="pendiente", nullable=False)
    notas: Mapped[str | None] = mapped_column(Text)

    usuario: Mapped[Usuario] = relationship(back_populates="citas", foreign_keys=[usuario_id])
    profesional: Mapped[Usuario | None] = relationship(foreign_keys=[profesional_id])
    servicio: Mapped[Servicios] = relationship(back_populates="citas")
    recordatorios: Mapped[list[Recordatorios]] = relationship(
        back_populates="cita", cascade="all, delete-orphan"
    )


class CatalogoPrecios(Base):
    __tablename__ = "catalogo_precios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    servicio_id: Mapped[int] = mapped_column(ForeignKey("servicios.id", ondelete="CASCADE"))
    precio: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    vigencia_desde: Mapped[date] = mapped_column(Date, nullable=False)
    vigencia_hasta: Mapped[date | None] = mapped_column(Date)

    servicio: Mapped[Servicios] = relationship(back_populates="precios")


class Galeria(Base):
    __tablename__ = "galeria"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    servicio_id: Mapped[int | None] = mapped_column(ForeignKey("servicios.id", ondelete="SET NULL"))
    titulo: Mapped[str] = mapped_column(String(150), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text)
    imagen_url: Mapped[str] = mapped_column(String(500), nullable=False)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    servicio: Mapped[Servicios | None] = relationship(back_populates="galeria")


class Productos(Base):
    __tablename__ = "productos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text)
    sku: Mapped[str | None] = mapped_column(String(80), unique=True)
    stock: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    stock_minimo: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    precio_compra: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # `Inventario.producto_id` NO declara ondelete: borrar un producto con
    # movimientos debe fallar (409) y no arrastrar el historico.
    proveedores: Mapped[list[ProductoProveedores]] = relationship(
        back_populates="producto", cascade="all, delete-orphan"
    )
    movimientos: Mapped[list[Inventario]] = relationship(back_populates="producto")
    servicios: Mapped[list[ServicioProductos]] = relationship(
        back_populates="producto", cascade="all, delete-orphan"
    )


class Proveedores(Base):
    __tablename__ = "proveedores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255))
    telefono: Mapped[str | None] = mapped_column(String(30))
    direccion: Mapped[str | None] = mapped_column(String(300))
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    productos: Mapped[list[ProductoProveedores]] = relationship(back_populates="proveedor")


class ProductoProveedores(Base):
    __tablename__ = "producto_proveedores"
    __table_args__ = (UniqueConstraint("producto_id", "proveedor_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    producto_id: Mapped[int] = mapped_column(ForeignKey("productos.id", ondelete="CASCADE"))
    proveedor_id: Mapped[int] = mapped_column(ForeignKey("proveedores.id", ondelete="CASCADE"))
    codigo_proveedor: Mapped[str | None] = mapped_column(String(100))

    producto: Mapped[Productos] = relationship(back_populates="proveedores")
    proveedor: Mapped[Proveedores] = relationship(back_populates="productos")


class Inventario(Base):
    __tablename__ = "inventario"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    producto_id: Mapped[int] = mapped_column(ForeignKey("productos.id"))
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuario.id", ondelete="SET NULL"))
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)
    cantidad: Mapped[int] = mapped_column(Integer, nullable=False)
    motivo: Mapped[str | None] = mapped_column(String(250))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    producto: Mapped[Productos] = relationship(back_populates="movimientos")
    usuario: Mapped[Usuario | None] = relationship(back_populates="movimientos_inventario")


class Notificaciones(Base):
    __tablename__ = "notificaciones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuario.id", ondelete="CASCADE"))
    titulo: Mapped[str] = mapped_column(String(150), nullable=False)
    mensaje: Mapped[str] = mapped_column(Text, nullable=False)
    leida: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    usuario: Mapped[Usuario] = relationship(back_populates="notificaciones")


class Recordatorios(Base):
    __tablename__ = "recordatorios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cita_id: Mapped[int] = mapped_column(ForeignKey("citas.id", ondelete="CASCADE"))
    programado_para: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    canal: Mapped[str] = mapped_column(String(30), default="email", nullable=False)
    estado: Mapped[str] = mapped_column(String(30), default="pendiente", nullable=False)
    enviado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    cita: Mapped[Citas] = relationship(back_populates="recordatorios")


class ServicioProductos(Base):
    __tablename__ = "servicio_productos"
    __table_args__ = (UniqueConstraint("servicio_id", "producto_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    servicio_id: Mapped[int] = mapped_column(ForeignKey("servicios.id", ondelete="CASCADE"))
    producto_id: Mapped[int] = mapped_column(ForeignKey("productos.id", ondelete="CASCADE"))
    cantidad: Mapped[Decimal] = mapped_column(Numeric(10, 3), default=1, nullable=False)

    servicio: Mapped[Servicios] = relationship(back_populates="productos")
    producto: Mapped[Productos] = relationship(back_populates="servicios")


class SlotsBloqueados(Base):
    __tablename__ = "slots_bloqueados"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    agenda_id: Mapped[int] = mapped_column(ForeignKey("agenda.id", ondelete="CASCADE"))
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    hora_inicio: Mapped[time] = mapped_column(Time, nullable=False)
    hora_fin: Mapped[time] = mapped_column(Time, nullable=False)
    motivo: Mapped[str | None] = mapped_column(String(250))

    agenda: Mapped[Agenda] = relationship(back_populates="slots_bloqueados")