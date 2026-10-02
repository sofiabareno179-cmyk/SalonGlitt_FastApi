"""Hashing de contrasenas y tokens JWT.

Se prueban por separado del flujo HTTP porque son la base del contrato de
seguridad: si `verify_password` devolviera `True` con cualquier cadena, el
resto de las pruebas de autenticacion seguirian en verde y no servirian de nada.
"""
from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_hash_y_verify_coinciden() -> None:
    """La contrasena original valida contra su propio hash."""
    codificada = hash_password("Contrasena1")

    assert verify_password("Contrasena1", codificada) is True


def test_verify_rechaza_otra_contrasena() -> None:
    """Una contrasena distinta no debe validar, aunque el formato sea correcto."""
    codificada = hash_password("Contrasena1")

    assert verify_password("Contrasena2", codificada) is False


def test_cada_hash_usa_un_salt_distinto() -> None:
    """Dos usuarios con la misma contrasena no deben compartir hash.

    Sin salt aleatorio, dos cuentas con la misma contrasena serian
    identificables con solo comparar la columna `password_hash`.
    """
    primero = hash_password("Contrasena1")
    segundo = hash_password("Contrasena1")

    assert primero != segundo
    # El formato es `pbkdf2_sha256$<iteraciones>$<salt>$<digest>`.
    assert primero.count("$") == 3
    assert primero.startswith("pbkdf2_sha256$")


@pytest.mark.parametrize(
    "codificada",
    [
        "",
        "no-es-un-hash",
        "pbkdf2_sha256$310000$abcd",
        "bcrypt$310000$abcd$efgh",
        "pbkdf2_sha256$no-numerico$abcd$efgh",
    ],
)
def test_verify_no_revienta_con_hashes_malformados(codificada: str) -> None:
    """Un hash corrupto en la base se trata como 'no coincide', no como error 500."""
    assert verify_password("Contrasena1", codificada) is False


def test_token_lleva_el_id_del_usuario() -> None:
    """`sub` es el identificador del usuario, en texto."""
    token = create_access_token(42)

    assert decode_access_token(token)["sub"] == "42"


def test_token_firmado_con_otra_clave_es_rechazado() -> None:
    """Un token ajeno (por ejemplo, de otro entorno) no debe validar."""
    ahora = datetime.now(UTC) + timedelta(minutes=5)
    # La clave falsa tiene 32 bytes: PyJWT avisa por debajo de ese tamano y el
    # aviso taparia el error que la prueba si busca detectar.
    clave_falsa = "clave-falsa-de-32-bytes-exactos!!"
    forjado = jwt.encode({"sub": "1", "exp": ahora}, clave_falsa, algorithm="HS256")

    with pytest.raises(jwt.PyJWTError):
        decode_access_token(forjado)


def test_token_vencido_es_rechazado() -> None:
    """La expiracion se valida al decodificar, no solo al firmar."""
    pasado = datetime.now(UTC) - timedelta(minutes=1)
    vencido = jwt.encode(
        {"sub": "1", "exp": pasado},
        get_settings().secret_key,
        algorithm=get_settings().jwt_algorithm,
    )

    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(vencido)