"""Esquemas Pydantic de entrada y salida para las entidades del salon."""
from datetime import date, datetime, time
from decimal import Decimal

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ReadSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class UsuarioCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=100)
    apellido: str = Field(min_length=1, max_length=100)
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=128)
    telefono: str | None = Field(default=None, max_length=30)


class UsuarioRead(ReadSchema):
    id: int
    nombre: str
    apellido: str
    email: str
    telefono: str | None
    activo: bool
    creado_en: datetime


class UsuarioUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=100)
    apellido: str | None = Field(default=None, min_length=1, max_length=100)
    email: str | None = Field(default=None, min_length=3, max_length=255)
    password: str | None = Field(default=None, min_length=8, max_length=128)
    telefono: str | None = Field(default=None, max_length=30)


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"


class PerfilesCreate(BaseModel):
    usuario_id: int
    rol: str = Field(default="cliente", max_length=40)
    foto_url: str | None = Field(default=None, max_length=500)


class PerfilesRead(ReadSchema):
    id: int
    usuario_id: int
    rol: str
    foto_url: str | None


class AgendaCreate(BaseModel):
    usuario_id: int
    dia_semana: int = Field(ge=0, le=6)
    hora_inicio: time
    hora_fin: time
    activo: bool = True


class AgendaRead(ReadSchema):
    id: int
    usuario_id: int
    dia_semana: int
    hora_inicio: time
    hora_fin: time
    activo: bool


class ServiciosCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=120)
    descripcion: str | None = None
    duracion_minutos: int = Field(gt=0)
    precio: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    activo: bool = True


class ServiciosRead(ReadSchema):
    id: int
    nombre: str
    descripcion: str | None
    duracion_minutos: int
    precio: Decimal
    activo: bool


class CitasCreate(BaseModel):
    usuario_id: int
    servicio_id: int
    profesional_id: int | None = None
    fecha_inicio: datetime
    fecha_fin: datetime
    estado: str = Field(default="pendiente", max_length=30)
    notas: str | None = None


class CitasRead(ReadSchema):
    id: int
    usuario_id: int
    servicio_id: int
    profesional_id: int | None
    fecha_inicio: datetime
    fecha_fin: datetime
    estado: str
    notas: str | None


class CatalogoPreciosCreate(BaseModel):
    servicio_id: int
    precio: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    vigencia_desde: date
    vigencia_hasta: date | None = None


class CatalogoPreciosRead(ReadSchema):
    id: int
    servicio_id: int
    precio: Decimal
    vigencia_desde: date
    vigencia_hasta: date | None


class GaleriaCreate(BaseModel):
    servicio_id: int | None = None
    titulo: str = Field(min_length=1, max_length=150)
    descripcion: str | None = None
    imagen_url: str = Field(min_length=1, max_length=500)


class GaleriaRead(ReadSchema):
    id: int
    servicio_id: int | None
    titulo: str
    descripcion: str | None
    imagen_url: str
    creado_en: datetime


class ProductosCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=150)
    descripcion: str | None = None
    sku: str | None = Field(default=None, max_length=80)
    stock: int = Field(default=0, ge=0)
    stock_minimo: int = Field(default=0, ge=0)
    precio_compra: Decimal = Field(default=Decimal("0"), ge=0, max_digits=10, decimal_places=2)
    activo: bool = True


class ProductosRead(ReadSchema):
    id: int
    nombre: str
    descripcion: str | None
    sku: str | None
    stock: int
    stock_minimo: int
    precio_compra: Decimal
    activo: bool


class ProveedoresCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=150)
    email: str | None = Field(default=None, max_length=255)
    telefono: str | None = Field(default=None, max_length=30)
    direccion: str | None = Field(default=None, max_length=300)


class ProveedoresRead(ReadSchema):
    id: int
    nombre: str
    email: str | None
    telefono: str | None
    direccion: str | None
    activo: bool


class ProductoProveedoresCreate(BaseModel):
    producto_id: int
    proveedor_id: int
    codigo_proveedor: str | None = Field(default=None, max_length=100)


class ProductoProveedoresRead(ReadSchema):
    id: int
    producto_id: int
    proveedor_id: int
    codigo_proveedor: str | None


class InventarioCreate(BaseModel):
    producto_id: int
    usuario_id: int | None = None
    tipo: str = Field(min_length=1, max_length=20)
    cantidad: int = Field(gt=0)
    motivo: str | None = Field(default=None, max_length=250)


class InventarioRead(ReadSchema):
    id: int
    producto_id: int
    usuario_id: int | None
    tipo: str
    cantidad: int
    motivo: str | None
    creado_en: datetime


class NotificacionesCreate(BaseModel):
    usuario_id: int
    titulo: str = Field(min_length=1, max_length=150)
    mensaje: str = Field(min_length=1)


class NotificacionesRead(ReadSchema):
    id: int
    usuario_id: int
    titulo: str
    mensaje: str
    leida: bool
    creado_en: datetime


class RecordatoriosCreate(BaseModel):
    cita_id: int
    programado_para: datetime
    canal: str = Field(default="email", max_length=30)


class RecordatoriosRead(ReadSchema):
    id: int
    cita_id: int
    programado_para: datetime
    canal: str
    estado: str
    enviado_en: datetime | None


class ServicioProductosCreate(BaseModel):
    servicio_id: int
    producto_id: int
    cantidad: Decimal = Field(default=Decimal("1"), gt=0, max_digits=10, decimal_places=3)


class ServicioProductosRead(ReadSchema):
    id: int
    servicio_id: int
    producto_id: int
    cantidad: Decimal


class SlotsBloqueadosCreate(BaseModel):
    agenda_id: int
    fecha: date
    hora_inicio: time
    hora_fin: time
    motivo: str | None = Field(default=None, max_length=250)


class SlotsBloqueadosRead(ReadSchema):
    id: int
    agenda_id: int
    fecha: date
    hora_inicio: time
    hora_fin: time
    motivo: str | None