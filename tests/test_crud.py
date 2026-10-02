"""Fabrica `build_crud_router` y los routers que la usan.

Una sola prueba recorre el ciclo completo (alta, listado, detalle, parche,
borrado) porque los cinco endpoints comparten la misma logica: repetir el ciclo
para los catorce recursos seria escribir la misma prueba catorce veces. Lo que
si se comprueba por recurso son los caminos que dependen del modelo: la
proteccion por token y los 409 por restriccion unica.
"""
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password
from app.models import Servicios, Usuario

SERVICIO = {
    "nombre": "Corte de pelo",
    "descripcion": "Incluye lavado",
    "duracion_minutos": 30,
    "precio": "45.50",
}


async def test_ciclo_completo_de_un_recurso(
    cliente: AsyncClient, auth: dict[str, str]
) -> None:
    """Alta 201 -> listado -> detalle -> parche -> borrado 204 -> 404."""
    creado = await cliente.post("/api/v1/servicios", json=SERVICIO, headers=auth)
    assert creado.status_code == 201
    servicio_id = creado.json()["id"]
    assert creado.json()["activo"] is True

    listado = await cliente.get("/api/v1/servicios", headers=auth)
    assert listado.status_code == 200
    assert [s["id"] for s in listado.json()] == [servicio_id]

    detalle = await cliente.get(f"/api/v1/servicios/{servicio_id}", headers=auth)
    assert detalle.status_code == 200
    assert detalle.json()["nombre"] == "Corte de pelo"
    assert detalle.json()["precio"] == "45.50"

    parche = await cliente.patch(
        f"/api/v1/servicios/{servicio_id}", json={"precio": "52.00"}, headers=auth
    )
    assert parche.status_code == 200
    assert parche.json()["precio"] == "52.00"
    # El PATCH es parcial: los campos no enviados conservan su valor.
    assert parche.json()["nombre"] == "Corte de pelo"

    borrado = await cliente.delete(f"/api/v1/servicios/{servicio_id}", headers=auth)
    assert borrado.status_code == 204
    assert borrado.content == b""

    assert (await cliente.get(f"/api/v1/servicios/{servicio_id}", headers=auth)).status_code == 404


async def test_detalle_de_id_inexistente_es_404(
    cliente: AsyncClient, auth: dict[str, str]
) -> None:
    """Un id que no existe es 404 con el mensaje declarado, no 500."""
    respuesta = await cliente.get("/api/v1/servicios/4242", headers=auth)

    assert respuesta.status_code == 404
    assert respuesta.json()["detail"] == "Registro no encontrado"


async def test_parche_y_borrado_sobre_id_inexistente_es_404(
    cliente: AsyncClient, auth: dict[str, str]
) -> None:
    """PATCH y DELETE comprueban la existencia antes de tocar nada."""
    parche = await cliente.patch("/api/v1/servicios/4242", json={"activo": False}, headers=auth)
    borrado = await cliente.delete("/api/v1/servicios/4242", headers=auth)

    assert parche.status_code == 404
    assert borrado.status_code == 404


async def test_todos_los_recursos_exigen_token(cliente: AsyncClient) -> None:
    """Sin bearer, la fabrica devuelve 401 antes de tocar la base.

    Se recorren los catorce recursos generados con `build_crud_router` porque
    la dependencia se aplica en el APIRouter: basta con que uno seolvide para
    que quede un endpoint sin proteccion.
    """
    recursos = [
        "perfiles",
        "citas",
        "agenda",
        "slots-bloqueados",
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
    ]

    for recurso in recursos:
        listado = await cliente.get(f"/api/v1/{recurso}")
        assert listado.status_code == 401, f"{recurso} dejo el listado abierto"
        alta = await cliente.post(f"/api/v1/{recurso}", json={})
        assert alta.status_code == 401, f"{recurso} dejo el alta abierta"


async def test_validacion_del_cuerpo_en_el_alta(
    cliente: AsyncClient, auth: dict[str, str]
) -> None:
    """`duracion_minutos=0` viola `Field(gt=0)`: es 422 antes de la base."""
    respuesta = await cliente.post(
        "/api/v1/servicios", json={**SERVICIO, "duracion_minutos": 0}, headers=auth
    )

    assert respuesta.status_code == 422


async def test_precio_incorrecto_es_422(cliente: AsyncClient, auth: dict[str, str]) -> None:
    """Un precio negativo o con demas decimales lo rechaza el esquema."""
    negativa = await cliente.post(
        "/api/v1/servicios", json={**SERVICIO, "precio": "-1"}, headers=auth
    )
    precision = await cliente.post(
        "/api/v1/servicios", json={**SERVICIO, "precio": "10.123"}, headers=auth
    )

    assert negativa.status_code == 422
    assert precision.status_code == 422


async def test_sku_duplicado_es_409(cliente: AsyncClient, auth: dict[str, str]) -> None:
    """El `IntegrityError` del UNIQUE se traduce a 409, no a 500."""
    producto = {"nombre": "Shampoo", "sku": "SH-001", "stock": 5, "precio_compra": "8.00"}
    await cliente.post("/api/v1/productos", json=producto, headers=auth)

    respuesta = await cliente.post("/api/v1/productos", json=producto, headers=auth)

    assert respuesta.status_code == 409
    assert respuesta.json()["detail"] == "Conflicto con un registro existente"


async def test_sku_nulo_permite_varios_productos(
    cliente: AsyncClient, auth: dict[str, str]
) -> None:
    """`sku` es unico pero admite NULL: dos productos sin SKU no colisionan.

    Es la diferencia entre un UNIQUE de PostgreSQL y uno de SQLite; si este
    test falla en otro motor, la migracion necesita un indice parcial.
    """
    producto = {"nombre": "Cepillo", "stock": 1, "precio_compra": "4.00"}

    primero = await cliente.post("/api/v1/productos", json=producto, headers=auth)
    segundo = await cliente.post("/api/v1/productos", json=producto, headers=auth)

    assert primero.status_code == 201
    assert segundo.status_code == 201


async def test_galeria_acepta_servicio_nulo(cliente: AsyncClient, auth: dict[str, str]) -> None:
    """Una foto de portfolio no pertenece necesariamente a un servicio."""
    respuesta = await cliente.post(
        "/api/v1/galeria",
        json={"titulo": "Antes y despues", "imagen_url": "https://cdn/foto.jpg"},
        headers=auth,
    )

    assert respuesta.status_code == 201
    assert respuesta.json()["servicio_id"] is None


async def test_inventario_registra_el_movimiento(
    cliente: AsyncClient, auth: dict[str, str]
) -> None:
    """Un movimiento con cantidad 0 se rechaza: `Field(gt=0)`."""
    producto = await cliente.post(
        "/api/v1/productos", json={"nombre": "Guantes", "stock": 50}, headers=auth
    )
    producto_id = producto.json()["id"]

    invalido = await cliente.post(
        "/api/v1/inventario",
        json={"producto_id": producto_id, "tipo": "entrada", "cantidad": 0},
        headers=auth,
    )
    valido = await cliente.post(
        "/api/v1/inventario",
        json={"producto_id": producto_id, "tipo": "entrada", "cantidad": 10, "motivo": "Compra"},
        headers=auth,
    )

    assert invalido.status_code == 422
    assert valido.status_code == 201
    assert valido.json()["cantidad"] == 10


async def test_usuarios_guarda_el_hash_nunca_la_contrasena(
    cliente: AsyncClient, auth: dict[str, str], registro: dict[str, str]
) -> None:
    """El alta por `/usuarios` hashea la contrasena y no la expone."""
    otro = {**registro, "email": "carla@salon.test"}
    creado = await cliente.post("/api/v1/usuarios", json=otro, headers=auth)

    assert creado.status_code == 201
    cuerpo = creado.json()
    assert "password" not in cuerpo
    assert "password_hash" not in cuerpo

    # Y el login con esa contrasena funciona: prueba indirecta de que se
    # guardo el hash de la contrasena correcta.
    login = await cliente.post(
        "/api/v1/auth/login", json={"email": "carla@salon.test", "password": otro["password"]}
    )
    assert login.status_code == 200


async def test_usuarios_devuelve_el_hash_para_inspeccion(
    cliente: AsyncClient, auth: dict[str, str], registro: dict[str, str],
    sesion: AsyncSession,
) -> None:
    """Verificacion directa en base: lo almacenado valida como hash PBKDF2."""
    await cliente.post(
        "/api/v1/usuarios", json={**registro, "email": "dani@salon.test"}, headers=auth
    )

    usuario = await sesion.scalar(select(Usuario).where(Usuario.email == "dani@salon.test"))

    assert usuario is not None
    assert usuario.password_hash != registro["password"]
    assert usuario.password_hash.startswith("pbkdf2_sha256$")
    assert verify_password(registro["password"], usuario.password_hash) is True


async def test_patch_de_usuario_rehashea_la_contrasena(
    cliente: AsyncClient, auth: dict[str, str], email: str
) -> None:
    """Cambiar la contrasena por PATCH permite entrar con la nueva y no con la vieja."""
    usuario_id = (await cliente.get("/api/v1/usuarios", headers=auth)).json()[0]["id"]

    parche = await cliente.patch(
        f"/api/v1/usuarios/{usuario_id}", json={"password": "NuevaClave9"}, headers=auth
    )

    assert parche.status_code == 200
    assert "password_hash" not in parche.json()
    nueva = await cliente.post(
        "/api/v1/auth/login", json={"email": email, "password": "NuevaClave9"}
    )
    vieja = await cliente.post(
        "/api/v1/auth/login", json={"email": email, "password": "Contrasena1"}
    )
    assert nueva.status_code == 200
    assert vieja.status_code == 401


async def test_patch_de_usuario_solo_toca_lo_enviado(
    cliente: AsyncClient, auth: dict[str, str]
) -> None:
    """`exclude_unset` evita que un campo ausente se convierta en NULL."""
    usuario_id = (await cliente.get("/api/v1/usuarios", headers=auth)).json()[0]["id"]

    parche = await cliente.patch(
        f"/api/v1/usuarios/{usuario_id}", json={"telefono": "600123456"}, headers=auth
    )

    assert parche.status_code == 200
    cuerpo = parche.json()
    assert cuerpo["telefono"] == "600123456"
    assert cuerpo["email"] == "ana@salon.test"
    assert cuerpo["nombre"] == "Ana"


async def test_patch_valida_el_esquema(cliente: AsyncClient, auth: dict[str, str]) -> None:
    """`UsuarioUpdate` conserva las restricciones del modelo de creacion."""
    usuario_id = (await cliente.get("/api/v1/usuarios", headers=auth)).json()[0]["id"]

    respuesta = await cliente.patch(
        f"/api/v1/usuarios/{usuario_id}", json={"password": "corta"}, headers=auth
    )

    assert respuesta.status_code == 422


async def test_alta_de_usuario_duplicado_es_409(
    cliente: AsyncClient, auth: dict[str, str], registro: dict[str, str]
) -> None:
    """El router de usuarios comprueba el duplicado antes de insertar."""
    respuesta = await cliente.post(
        "/api/v1/usuarios", json={**registro, "email": "ana@salon.test"}, headers=auth
    )

    assert respuesta.status_code == 409
    assert respuesta.json()["detail"] == "El correo ya esta registrado"


async def test_borrar_usuario_es_204_y_deja_de_resolver(
    cliente: AsyncClient, auth: dict[str, str], registro: dict[str, str]
) -> None:
    """Tras el DELETE, el detalle responde 404.

    Se borra un usuario distinto al del token: si se borrara al propietario,
    el GET posterior respondería 401 y la prueba no distinguiría un borrado
    correcto de un fallo de autenticación.
    """
    await cliente.post(
        "/api/v1/usuarios", json={**registro, "email": "efrain@salon.test"}, headers=auth
    )
    usuarios = (await cliente.get("/api/v1/usuarios", headers=auth)).json()
    objetivo = next(u["id"] for u in usuarios if u["email"] == "efrain@salon.test")

    borrado = await cliente.delete(f"/api/v1/usuarios/{objetivo}", headers=auth)

    assert borrado.status_code == 204
    detalle = await cliente.get(f"/api/v1/usuarios/{objetivo}", headers=auth)
    assert detalle.status_code == 404
    assert detalle.json()["detail"] == "Usuario no encontrado"


async def test_usuarios_requieren_token(cliente: AsyncClient) -> None:
    """El router de usuarios declara la dependencia de autenticacion."""
    listado = await cliente.get("/api/v1/usuarios")
    alta = await cliente.post("/api/v1/usuarios", json={})

    assert listado.status_code == 401
    assert alta.status_code == 401


async def test_borrar_usuario_con_perfil_lo_arrastra_en_cascada(
    cliente: AsyncClient, auth: dict[str, str], registro: dict[str, str]
) -> None:
    """Con `cascade="all, delete-orphan"` el perfil desaparece con el usuario.

    Antes este caso devolvia 409 "hay datos relacionados": el esquema declara
    `ondelete="CASCADE"` pero el ORM no lo respetaba. El 409 sigue siendo lo
    correcto para las citas (ver el test siguiente), no para el perfil.
    """
    creado = await cliente.post(
        "/api/v1/usuarios", json={**registro, "email": "gina@salon.test"}, headers=auth
    )
    usuario_id = creado.json()["id"]
    perfil = await cliente.post(
        "/api/v1/perfiles", json={"usuario_id": usuario_id, "rol": "cliente"}, headers=auth
    )
    perfil_id = perfil.json()["id"]

    borrado = await cliente.delete(f"/api/v1/usuarios/{usuario_id}", headers=auth)

    assert borrado.status_code == 204
    assert (await cliente.get(f"/api/v1/perfiles/{perfil_id}", headers=auth)).status_code == 404


async def test_borrar_usuario_con_citas_es_409(
    cliente: AsyncClient, auth: dict[str, str], registro: dict[str, str]
) -> None:
    """`Citas.usuario_id` NO declara ondelete: con historial el borrado se rechaza.

    Es la contraparte intencionada de la cascada. Perder las citas de un
    cliente por borrar su usuario seria peor que devolver un 409, asi que este
    contrato se fija a proposito.
    """
    creado = await cliente.post(
        "/api/v1/usuarios", json={**registro, "email": "hugo@salon.test"}, headers=auth
    )
    usuario_id = creado.json()["id"]
    servicio = await cliente.post("/api/v1/servicios", json=SERVICIO, headers=auth)
    cita = await cliente.post(
        "/api/v1/citas",
        json={
            "usuario_id": usuario_id,
            "servicio_id": servicio.json()["id"],
            "fecha_inicio": "2026-01-01T10:00:00",
            "fecha_fin": "2026-01-01T10:30:00",
        },
        headers=auth,
    )
    assert cita.status_code == 201

    borrado = await cliente.delete(f"/api/v1/usuarios/{usuario_id}", headers=auth)

    assert borrado.status_code == 409
    assert borrado.json()["detail"] == "No se puede borrar: hay datos relacionados"
    # El usuario sigue en pie: un 409 no debe dejar el registro a medias.
    assert (await cliente.get(f"/api/v1/usuarios/{usuario_id}", headers=auth)).status_code == 200


async def test_detalle_de_usuario_consulta_correcta(
    cliente: AsyncClient, auth: dict[str, str], email: str
) -> None:
    """GET /usuarios/{id} devuelve el registro pedido."""
    usuario_id = (await cliente.get("/api/v1/auth/me", headers=auth)).json()["id"]

    respuesta = await cliente.get(f"/api/v1/usuarios/{usuario_id}", headers=auth)

    assert respuesta.status_code == 200
    assert respuesta.json()["email"] == email


async def test_operaciones_sin_id_inexistente_en_usuarios(
    cliente: AsyncClient, auth: dict[str, str]
) -> None:
    """GET/PATCH/DELETE sobre un id inexistente responden 404."""
    detalle = await cliente.get("/api/v1/usuarios/999", headers=auth)
    parche = await cliente.patch("/api/v1/usuarios/999", json={"nombre": "X"}, headers=auth)
    borrado = await cliente.delete("/api/v1/usuarios/999", headers=auth)

    assert detalle.status_code == 404
    assert parche.status_code == 404
    assert borrado.status_code == 404


# --- Traduccion de IntegrityError a 409 -------------------------------------
#
# Estos tres caminos solo se alcanzan con una restriccion que el codigo no
# comprueba antes de insertar: una carrera entre dos peticiones que crean el
# mismo registro a la vez, o un DELETE con filas dependientes que el motor
# rechaza. Provocarlos de verdad exigiria concurrencia o constraints que el
# esquema no declara, asi que se simula el fallo del driver. Lo que se verifica
# es la traduccion a 409 y el rollback, no el comportamiento de PostgreSQL.


async def _commit_roto(self: AsyncSession) -> None:
    """Sustituye a `AsyncSession.commit` para que siempre reviente."""
    raise IntegrityError("INSERT", {}, Exception("UNIQUE"))


@pytest.fixture
def commit_falla(monkeypatch: pytest.MonkeyPatch) -> None:
    """Haz que `commit` de SQLAlchemy levante IntegrityError."""
    monkeypatch.setattr(AsyncSession, "commit", _commit_roto)


async def test_alta_con_conflicto_en_base_es_409(
    cliente: AsyncClient, auth: dict[str, str], commit_falla: None
) -> None:
    """La fabrica convierte el IntegrityError del driver en 409, no en 500."""
    respuesta = await cliente.post("/api/v1/servicios", json=SERVICIO, headers=auth)

    assert respuesta.status_code == 409
    assert respuesta.json()["detail"] == "Conflicto con un registro existente"


async def test_parche_con_conflicto_en_base_es_409(
    cliente: AsyncClient, auth: dict[str, str], sesion: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """El PATCH con un conflicto responde 409 con el mismo texto.

    El servicio se inserta directamente en la base porque el parche de
    `commit` ya esta activo y por el `POST` fallaria.
    """
    servicio = Servicios(nombre="Color", duracion_minutos=45, precio=Decimal("60.00"))
    sesion.add(servicio)
    await sesion.commit()
    monkeypatch.setattr(AsyncSession, "commit", _commit_roto)

    respuesta = await cliente.patch(
        f"/api/v1/servicios/{servicio.id}", json={"activo": False}, headers=auth
    )

    assert respuesta.status_code == 409
    assert respuesta.json()["detail"] == "Conflicto con un registro existente"


async def test_borrado_con_filas_dependientes_es_409(
    cliente: AsyncClient, auth: dict[str, str], sesion: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """El borrado bloqueado explica el motivo: hay datos relacionados."""
    servicio = Servicios(nombre="Color", duracion_minutos=45, precio=Decimal("60.00"))
    sesion.add(servicio)
    await sesion.commit()
    monkeypatch.setattr(AsyncSession, "commit", _commit_roto)

    respuesta = await cliente.delete(f"/api/v1/servicios/{servicio.id}", headers=auth)

    assert respuesta.status_code == 409
    assert respuesta.json()["detail"] == "No se puede borrar: hay datos relacionados"


async def test_alta_de_usuario_con_conflicto_en_base_es_409(
    cliente: AsyncClient, auth: dict[str, str], commit_falla: None
) -> None:
    """El router de usuarios tiene su propio manejar de IntegrityError."""
    respuesta = await cliente.post(
        "/api/v1/usuarios", json={"nombre": "A", "apellido": "B", "email": "x@y.test",
                                  "password": "Contrasena1"}, headers=auth
    )

    assert respuesta.status_code == 409
    assert respuesta.json()["detail"] == "El correo ya esta registrado"


async def test_parche_de_usuario_con_conflicto_en_base_es_409(
    cliente: AsyncClient, auth: dict[str, str], commit_falla: None
) -> None:
    """Cambiar el correo a uno ya usado responde 409."""
    usuario_id = (await cliente.get("/api/v1/usuarios", headers=auth)).json()[0]["id"]

    respuesta = await cliente.patch(
        f"/api/v1/usuarios/{usuario_id}", json={"email": "ocupado@salon.test"}, headers=auth
    )

    assert respuesta.status_code == 409
    assert respuesta.json()["detail"] == "Conflicto con un usuario existente"