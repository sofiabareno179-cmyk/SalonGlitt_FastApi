"""Dependencias compartidas por los routers."""
from typing import Annotated, cast

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models import Usuario

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Usuario:
    """Resuelve el usuario autenticado a partir de un bearer token valido."""
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales invalidas o token vencido",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized
    try:
        subject = decode_access_token(credentials.credentials).get("sub")
        user_id = int(cast(str, subject))
    except (jwt.PyJWTError, TypeError, ValueError):
        raise unauthorized from None

    user = await db.get(Usuario, user_id)
    if user is None or not user.activo:
        raise unauthorized
    return user