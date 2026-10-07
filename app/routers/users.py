"""CRUD de usuarios y perfiles; requiere bearer JWT."""
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import hash_password
from app.dependencies import get_current_user
from app.models import Perfiles, Usuario
from app.routers.crud import build_crud_router
from app.schemas.entities import (
    PerfilesCreate,
    PerfilesRead,
    UsuarioCreate,
    UsuarioRead,
    UsuarioUpdate,
)

router = APIRouter()
usuario_router = APIRouter(
    prefix="/usuarios",
    tags=["usuarios"],
    dependencies=[Depends(get_current_user)],
)


@usuario_router.get("", response_model=list[UsuarioRead])
async def list_users(db: AsyncSession = Depends(get_db)) -> list[Usuario]:
    result = await db.scalars(select(Usuario).order_by(Usuario.id))
    return list(result.all())


@usuario_router.get("/{user_id}", response_model=UsuarioRead)
async def get_user(user_id: int, db: AsyncSession = Depends(get_db)) -> Usuario:
    user = await db.get(Usuario, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return user


@usuario_router.post("", response_model=UsuarioRead, status_code=status.HTTP_201_CREATED)
async def create_user(payload: UsuarioCreate, db: AsyncSession = Depends(get_db)) -> Usuario:
    existing = await db.scalar(select(Usuario).where(Usuario.email == payload.email))
    if existing is not None:
        raise HTTPException(status_code=409, detail="El correo ya esta registrado")
    user = Usuario(
        nombreuser=payload.nombreuser,
        email=payload.email,
        password_hash=hash_password(payload.password),
        telefono=payload.telefono,
        rol=payload.rol,
    )
    db.add(user)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="El correo ya esta registrado") from None
    await db.refresh(user)
    return user


@usuario_router.patch("/{user_id}", response_model=UsuarioRead)
async def update_user(
    user_id: int,
    payload: UsuarioUpdate,
    db: AsyncSession = Depends(get_db),
) -> Usuario:
    user = await db.get(Usuario, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    values = payload.model_dump(exclude_unset=True)
    new_password = values.pop("password", None)
    if new_password is not None:
        values["password_hash"] = hash_password(new_password)
    for field_name, value in values.items():
        setattr(user, field_name, value)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Conflicto con un usuario existente") from None
    await db.refresh(user)
    return user


@usuario_router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: int, db: AsyncSession = Depends(get_db)) -> Response:
    user = await db.get(Usuario, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    await db.delete(user)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail="No se puede borrar: hay datos relacionados",
        ) from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)


router.include_router(usuario_router)
router.include_router(
    build_crud_router(
        Perfiles,
        PerfilesCreate,
        PerfilesRead,
        prefix="/perfiles",
        tags=["perfiles"],
    )
)