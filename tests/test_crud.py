"""HTTP CRUD tests against the current PostgreSQL-shaped model contract."""
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Usuario

SERVICIO = {
    "nombre": "Corte de pelo",
    "precio": "45.50",
    "duracion": "30 min",
    "categoria": "Cabello",
}


async def test_ciclo_crud_de_servicio(cliente: AsyncClient, auth: dict[str, str]) -> None:
    creado = await cliente.post("/api/v1/servicios", json=SERVICIO, headers=auth)
    assert creado.status_code == 201
    servicio_id = creado.json()["id"]
    assert creado.json()["precio"] == "45.50"

    listado = await cliente.get("/api/v1/servicios", headers=auth)
    assert listado.status_code == 200
    assert [servicio["id"] for servicio in listado.json()] == [servicio_id]

    detalle = await cliente.get(f"/api/v1/servicios/{servicio_id}", headers=auth)
    assert detalle.status_code == 200
    assert detalle.json()["nombre"] == "Corte de pelo"

    actualizado = await cliente.patch(
        f"/api/v1/servicios/{servicio_id}",
        json={"precio": "52.00"},
        headers=auth,
    )
    assert actualizado.status_code == 200
    assert actualizado.json()["precio"] == "52.00"
    assert actualizado.json()["nombre"] == SERVICIO["nombre"]

    borrado = await cliente.delete(f"/api/v1/servicios/{servicio_id}", headers=auth)
    assert borrado.status_code == 204
    assert (
        await cliente.get(f"/api/v1/servicios/{servicio_id}", headers=auth)
    ).status_code == 404


async def test_validacion_de_servicio(cliente: AsyncClient, auth: dict[str, str]) -> None:
    sin_precio = await cliente.post(
        "/api/v1/servicios",
        json={**SERVICIO, "precio": "-1"},
        headers=auth,
    )
    precio_invalido = await cliente.post(
        "/api/v1/servicios",
        json={**SERVICIO, "precio": "10.123"},
        headers=auth,
    )
    faltan_campos = await cliente.post(
        "/api/v1/servicios",
        json={"nombre": "Corte", "precio": "10"},
        headers=auth,
    )

    assert sin_precio.status_code == 422
    assert precio_invalido.status_code == 422
    assert faltan_campos.status_code == 422


async def test_tablas_reales_exigen_autenticacion(cliente: AsyncClient) -> None:
    recursos = [
        "perfiles",
        "citas",
        "agenda",
        "bloqueos",
        "servicios",
        "catalogo-precios",
        "galeria",
        "productos",
        "proveedores",
        "inventario",
        "producto-proveedores",
        "servicio-productos",
        "notificaciones",
        "recordatorios",
        "promociones",
    ]

    for recurso in recursos:
        respuesta = await cliente.get(f"/api/v1/{recurso}")
        assert respuesta.status_code == 401, f"{recurso} debe exigir bearer"


async def test_promociones_usan_su_tabla(cliente: AsyncClient, auth: dict[str, str]) -> None:
    respuesta = await cliente.post(
        "/api/v1/promociones",
        json={"titulo": "Descuento", "descripcion": "10 %", "activa": True},
        headers=auth,
    )

    assert respuesta.status_code == 201
    assert respuesta.json()["titulo"] == "Descuento"
    assert respuesta.json()["activa"] is True


async def test_clave_compuesta_de_producto_proveedor(
    cliente: AsyncClient, auth: dict[str, str]
) -> None:
    producto = await cliente.post(
        "/api/v1/productos",
        json={"nombre": "Shampoo", "precio": 8.5, "categoria": "Cuidado"},
        headers=auth,
    )
    proveedor = await cliente.post(
        "/api/v1/proveedores",
        json={
            "nombre_empresa": "Distribuidora",
            "contacto_nombre": "Ana",
            "telefono": "555123",
        },
        headers=auth,
    )
    assert producto.status_code == proveedor.status_code == 201

    relation = {
        "producto_id": producto.json()["id"],
        "proveedor_id": proveedor.json()["id"],
    }
    creado = await cliente.post(
        "/api/v1/producto-proveedores",
        json=relation,
        headers=auth,
    )
    assert creado.status_code == 201
    assert creado.json() == relation

    path = (
        f"/api/v1/producto-proveedores/"
        f"{relation['producto_id']}/{relation['proveedor_id']}"
    )
    assert (await cliente.get(path, headers=auth)).json() == relation
    actualizado = await cliente.patch(path, json={}, headers=auth)
    assert actualizado.status_code == 200
    assert (await cliente.delete(path, headers=auth)).status_code == 204


async def test_usuario_guarda_hash_y_permite_actualizarlo(
    cliente: AsyncClient,
    auth: dict[str, str],
    registro: dict[str, str],
    sesion: AsyncSession,
) -> None:
    otro = {**registro, "nombreuser": "carla", "email": "carla@salon.test"}
    creado = await cliente.post("/api/v1/usuarios", json=otro, headers=auth)
    assert creado.status_code == 201
    assert "password_hash" not in creado.json()

    usuario = await sesion.scalar(select(Usuario).where(Usuario.email == otro["email"]))
    assert usuario is not None
    assert usuario.password_hash != otro["password"]

    nuevo = "NuevaClave9"
    parche = await cliente.patch(
        f"/api/v1/usuarios/{creado.json()['id']}",
        json={"password": nuevo},
        headers=auth,
    )
    assert parche.status_code == 200
    respuesta_login = await cliente.post(
        "/api/v1/auth/login",
        json={"email": otro["email"], "password": nuevo},
    )
    assert respuesta_login.status_code == 200


async def test_detalle_inexistente_es_404(
    cliente: AsyncClient, auth: dict[str, str]
) -> None:
    respuesta = await cliente.get("/api/v1/servicios/4242", headers=auth)
    assert respuesta.status_code == 404


async def test_fallo_integridad_de_servicio_se_traduce_a_409(
    cliente: AsyncClient,
    auth: dict[str, str],
    monkeypatch,
) -> None:
    from sqlalchemy.ext.asyncio import AsyncSession

    async def _commit_roto(_self: AsyncSession) -> None:
        raise IntegrityError("INSERT", {}, Exception("UNIQUE"))

    monkeypatch.setattr(AsyncSession, "commit", _commit_roto)
    respuesta = await cliente.post("/api/v1/servicios", json=SERVICIO, headers=auth)

    assert respuesta.status_code == 409
    assert respuesta.json()["detail"] == "Conflicto con un registro existente"


async def test_bloqueo_usa_los_campos_reales(
    cliente: AsyncClient,
    auth: dict[str, str],
) -> None:
    usuario = await cliente.post(
        "/api/v1/usuarios",
        json={
            "nombreuser": "bloqueo",
            "email": "bloqueo@salon.test",
            "password": "Contrasena1",
            "rol": "cliente",
        },
        headers=auth,
    )
    assert usuario.status_code == 201
    respuesta = await cliente.post(
        "/api/v1/bloqueos",
        json={
            "fecha": "2026-10-06",
            "hora_inicio": "09:00",
            "hora_fin": "10:00",
            "usuario_id": usuario.json()["id"],
        },
        headers=auth,
    )

    assert respuesta.status_code == 201
    assert respuesta.json()["hora_inicio"] == "09:00"
