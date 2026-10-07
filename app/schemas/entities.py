"""Pydantic schemas matching the existing salon database."""
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ReadSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class UsuarioCreate(BaseModel):
    nombreuser: str = Field(min_length=1, max_length=100)
    email: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=8, max_length=128)
    telefono: str | None = Field(default=None, max_length=20)
    rol: str = Field(default="cliente", max_length=20)


class UsuarioRead(ReadSchema):
    id: int
    nombreuser: str
    email: str
    telefono: str | None
    rol: str


class UsuarioUpdate(BaseModel):
    nombreuser: str | None = Field(default=None, min_length=1, max_length=100)
    email: str | None = Field(default=None, min_length=3, max_length=100)
    password: str | None = Field(default=None, min_length=8, max_length=128)
    telefono: str | None = Field(default=None, max_length=20)
    rol: str | None = Field(default=None, max_length=20)


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=8, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"  # noqa: S105


class PerfilesCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=50)
    apellido: str | None = Field(default=None, max_length=50)
    bio: str | None = None
    usuario_id: int


class PerfilesRead(ReadSchema):
    id: int
    nombre: str
    apellido: str | None
    bio: str | None
    usuario_id: int


class AgendaCreate(BaseModel):
    dia_semana: str = Field(min_length=1, max_length=255)
    hora_inicio: str = Field(min_length=1, max_length=255)
    hora_fin: str = Field(min_length=1, max_length=255)
    usuario_id: int


class AgendaRead(ReadSchema):
    id: int
    dia_semana: str
    hora_inicio: str
    hora_fin: str
    usuario_id: int


class ServiciosCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=120)
    precio: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    duracion: str = Field(min_length=1, max_length=50)
    categoria: str = Field(min_length=1, max_length=100)
    cita_id: int | None = None
    imagen: str | None = Field(default=None, max_length=500)
    tip: str | None = None


class ServiciosRead(ReadSchema):
    id: int
    nombre: str
    precio: Decimal
    duracion: str
    categoria: str
    cita_id: int | None
    imagen: str | None
    tip: str | None


class CitasCreate(BaseModel):
    fecha_hora: datetime
    estado: str = Field(min_length=1, max_length=100)
    usuario_id: int
    servicio: str | None = Field(default=None, max_length=150)


class CitasRead(ReadSchema):
    id: int
    fecha_hora: datetime
    estado: str
    usuario_id: int
    servicio: str | None


class CatalogoPreciosCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=150)
    descripcion: str | None = Field(default=None, max_length=500)
    precio: float = Field(ge=0)
    categoria: str = Field(min_length=1, max_length=100)
    fecha_creacion: datetime | None = None


class CatalogoPreciosRead(ReadSchema):
    id: int
    nombre: str
    descripcion: str | None
    precio: float
    categoria: str
    fecha_creacion: datetime | None


class GaleriaCreate(BaseModel):
    titulo: str = Field(min_length=1, max_length=255)
    archivo: str = Field(min_length=1, max_length=255)
    descripcion: str | None = Field(default=None, max_length=500)
    fecha_subida: datetime | None = None
    tipo: str = Field(default="imagen", max_length=10)


class GaleriaRead(ReadSchema):
    id: int
    titulo: str
    archivo: str
    descripcion: str | None
    fecha_subida: datetime | None
    tipo: str


class ProductosCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=150)
    descripcion: str | None = Field(default=None, max_length=500)
    precio: float = Field(ge=0)
    categoria: str = Field(min_length=1, max_length=100)


class ProductosRead(ReadSchema):
    id: int
    nombre: str
    descripcion: str | None
    precio: float
    categoria: str


class ProveedoresCreate(BaseModel):
    nombre_empresa: str = Field(min_length=1, max_length=150)
    contacto_nombre: str = Field(min_length=1, max_length=150)
    telefono: str = Field(min_length=1, max_length=20)
    email: str | None = Field(default=None, max_length=100)
    direccion: str | None = Field(default=None, max_length=250)


class ProveedoresRead(ReadSchema):
    id: int
    nombre_empresa: str
    contacto_nombre: str
    telefono: str
    email: str | None
    direccion: str | None


class ProductoProveedoresCreate(BaseModel):
    producto_id: int
    proveedor_id: int


class ProductoProveedoresRead(ReadSchema):
    producto_id: int
    proveedor_id: int


class InventarioCreate(BaseModel):
    stock: int
    fecha: str = Field(min_length=1, max_length=100)
    producto_id: int
    tipo: str | None = Field(default=None, max_length=20)


class InventarioRead(ReadSchema):
    id: int
    stock: int
    fecha: str
    producto_id: int
    tipo: str | None


class NotificacionesCreate(BaseModel):
    usuario_id: int
    titulo: str = Field(min_length=1, max_length=200)
    mensaje: str | None = Field(default=None, max_length=500)
    leida: bool | None = None
    fecha_creacion: datetime | None = None


class NotificacionesRead(ReadSchema):
    id: int
    usuario_id: int
    titulo: str
    mensaje: str | None
    leida: bool | None
    fecha_creacion: datetime | None


class RecordatoriosCreate(BaseModel):
    titulo: str = Field(min_length=1, max_length=150)
    mensaje: str | None = Field(default=None, max_length=500)
    fecha_recordatorio: str = Field(min_length=1, max_length=100)
    usuario_id: int


class RecordatoriosRead(ReadSchema):
    id: int
    titulo: str
    mensaje: str | None
    fecha_recordatorio: str
    usuario_id: int


class ServicioProductosCreate(BaseModel):
    servicio_id: int
    producto_id: int


class ServicioProductosRead(ReadSchema):
    servicio_id: int
    producto_id: int


class BloqueosCreate(BaseModel):
    fecha: date
    hora_inicio: str = Field(min_length=5, max_length=5)
    hora_fin: str = Field(min_length=5, max_length=5)
    motivo: str | None = Field(default=None, max_length=255)
    usuario_id: int
    created_at: datetime | None = None


class BloqueosRead(ReadSchema):
    id: int
    fecha: date
    hora_inicio: str
    hora_fin: str
    motivo: str | None
    usuario_id: int
    created_at: datetime | None


class PromocionesCreate(BaseModel):
    titulo: str = Field(min_length=1, max_length=200)
    descripcion: str | None = None
    activa: bool | None = None
    updated_at: datetime | None = None


class PromocionesRead(ReadSchema):
    id: int
    titulo: str
    descripcion: str | None
    activa: bool | None
    updated_at: datetime | None
