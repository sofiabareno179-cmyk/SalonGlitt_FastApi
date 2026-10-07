"""SQLAlchemy mappings for the salon's existing PostgreSQL schema."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Shared declarative base."""


class Usuario(Base):
    __tablename__ = "usuario"

    id: Mapped[int] = mapped_column("idusuario", Integer, primary_key=True)
    nombreuser: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(250), nullable=False)
    telefono: Mapped[str | None] = mapped_column(String(20))
    rol: Mapped[str] = mapped_column(String(20), nullable=False)


class Perfiles(Base):
    __tablename__ = "perfiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(50), nullable=False)
    apellido: Mapped[str | None] = mapped_column(String(50))
    bio: Mapped[str | None] = mapped_column(Text)
    usuario_id: Mapped[int] = mapped_column(
        "idusuario", ForeignKey("usuario.idusuario"), unique=True, nullable=False
    )


class Agenda(Base):
    __tablename__ = "agenda"

    id: Mapped[int] = mapped_column("idagenda", Integer, primary_key=True)
    dia_semana: Mapped[str] = mapped_column("diasemana", String(255), nullable=False)
    hora_inicio: Mapped[str] = mapped_column("horainicio", String(255), nullable=False)
    hora_fin: Mapped[str] = mapped_column("horafin", String(255), nullable=False)
    usuario_id: Mapped[int] = mapped_column(
        "idusuario", ForeignKey("usuario.idusuario"), nullable=False
    )


class Citas(Base):
    __tablename__ = "citas"

    id: Mapped[int] = mapped_column("idcitas", Integer, primary_key=True)
    fecha_hora: Mapped[datetime] = mapped_column(
        "fechahora", DateTime(timezone=False), nullable=False
    )
    estado: Mapped[str] = mapped_column(String(100), nullable=False)
    usuario_id: Mapped[int] = mapped_column(
        "idusuario", ForeignKey("usuario.idusuario"), nullable=False
    )
    servicio: Mapped[str | None] = mapped_column(String(150))


class CatalogoPrecios(Base):
    __tablename__ = "catalogo_precios"

    id: Mapped[int] = mapped_column("idcatalogo", Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String(500))
    precio: Mapped[float] = mapped_column(Float, nullable=False)
    categoria: Mapped[str] = mapped_column(String(100), nullable=False)
    fecha_creacion: Mapped[datetime | None] = mapped_column(DateTime(timezone=False))


class Galeria(Base):
    __tablename__ = "galeria"

    id: Mapped[int] = mapped_column("idgaleria", Integer, primary_key=True)
    titulo: Mapped[str] = mapped_column(String(255), nullable=False)
    archivo: Mapped[str] = mapped_column(String(255), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String(500))
    fecha_subida: Mapped[datetime | None] = mapped_column(DateTime(timezone=False))
    tipo: Mapped[str] = mapped_column(String(10), nullable=False, server_default="imagen")


class Productos(Base):
    __tablename__ = "productos"

    id: Mapped[int] = mapped_column("idproductos", Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String(500))
    precio: Mapped[float] = mapped_column(Float, nullable=False)
    categoria: Mapped[str] = mapped_column(String(100), nullable=False)


class Proveedores(Base):
    __tablename__ = "proveedores"

    id: Mapped[int] = mapped_column("idproveedores", Integer, primary_key=True)
    nombre_empresa: Mapped[str] = mapped_column(String(150), nullable=False)
    contacto_nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    telefono: Mapped[str] = mapped_column(String(20), nullable=False)
    email: Mapped[str | None] = mapped_column(String(100))
    direccion: Mapped[str | None] = mapped_column(String(250))


class ProductoProveedores(Base):
    __tablename__ = "producto_proveedores"

    producto_id: Mapped[int] = mapped_column(
        ForeignKey("productos.idproductos"), primary_key=True, nullable=False
    )
    proveedor_id: Mapped[int] = mapped_column(
        ForeignKey("proveedores.idproveedores"), primary_key=True, nullable=False
    )


class Inventario(Base):
    __tablename__ = "inventario"

    id: Mapped[int] = mapped_column("idinventario", Integer, primary_key=True)
    stock: Mapped[int] = mapped_column(Integer, nullable=False)
    fecha: Mapped[str] = mapped_column(String(100), nullable=False)
    producto_id: Mapped[int] = mapped_column(
        "idproductos",
        ForeignKey("productos.idproductos"),
        unique=True,
        nullable=False,
    )
    tipo: Mapped[str | None] = mapped_column(String(20))


class Notificaciones(Base):
    __tablename__ = "notificaciones"

    id: Mapped[int] = mapped_column("idnotificacion", Integer, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(
        "idusuario", ForeignKey("usuario.idusuario"), nullable=False
    )
    titulo: Mapped[str] = mapped_column(String(200), nullable=False)
    mensaje: Mapped[str | None] = mapped_column(String(500))
    leida: Mapped[bool | None] = mapped_column(Boolean)
    fecha_creacion: Mapped[datetime | None] = mapped_column(DateTime(timezone=False))


class Recordatorios(Base):
    __tablename__ = "recordatorios"

    id: Mapped[int] = mapped_column("idrecordatorios", Integer, primary_key=True)
    titulo: Mapped[str] = mapped_column(String(150), nullable=False)
    mensaje: Mapped[str | None] = mapped_column(String(500))
    fecha_recordatorio: Mapped[str] = mapped_column(String(100), nullable=False)
    usuario_id: Mapped[int] = mapped_column(
        "idusuario", ForeignKey("usuario.idusuario"), nullable=False
    )


class ServicioProductos(Base):
    __tablename__ = "servicio_productos"

    servicio_id: Mapped[int] = mapped_column(
        ForeignKey("servicios.idservicio"), primary_key=True, nullable=False
    )
    producto_id: Mapped[int] = mapped_column(
        ForeignKey("productos.idproductos"), primary_key=True, nullable=False
    )


class Bloqueos(Base):
    __tablename__ = "bloqueos"

    id: Mapped[int] = mapped_column("idbloqueo", Integer, primary_key=True)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    hora_inicio: Mapped[str] = mapped_column(String(5), nullable=False)
    hora_fin: Mapped[str] = mapped_column(String(5), nullable=False)
    motivo: Mapped[str | None] = mapped_column(String(255))
    usuario_id: Mapped[int] = mapped_column(
        "idusuario", ForeignKey("usuario.idusuario"), nullable=False
    )
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False))


class Servicios(Base):
    __tablename__ = "servicios"

    id: Mapped[int] = mapped_column("idservicio", Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    precio: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    duracion: Mapped[str] = mapped_column(String(50), nullable=False)
    categoria: Mapped[str] = mapped_column(String(100), nullable=False)
    cita_id: Mapped[int | None] = mapped_column(
        "idcitas", ForeignKey("citas.idcitas"), unique=True
    )
    imagen: Mapped[str | None] = mapped_column(String(500))
    tip: Mapped[str | None] = mapped_column(Text)


class Promociones(Base):
    __tablename__ = "promociones"

    id: Mapped[int] = mapped_column("idpromocion", Integer, primary_key=True)
    titulo: Mapped[str] = mapped_column(String(200), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text)
    activa: Mapped[bool | None] = mapped_column(Boolean)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False))
