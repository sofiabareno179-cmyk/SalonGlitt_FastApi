"""Registro, inicio de sesion y consulta de identidad."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.dependencies import get_current_user
from app.models import Usuario
from app.schemas.entities import LoginRequest, TokenResponse, UsuarioCreate, UsuarioRead

router = APIRouter(prefix="/auth", tags=["autenticacion"])


async def _register(payload: UsuarioCreate, db: AsyncSession) -> Usuario:
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


@router.post("/register", response_model=UsuarioRead, status_code=status.HTTP_201_CREATED)
async def register(payload: UsuarioCreate, db: AsyncSession = Depends(get_db)) -> Usuario:
    """Crea una cuenta publica; nunca devuelve ni almacena la contrasena en claro."""
    return await _register(payload, db)


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    """Valida el usuario y entrega un bearer JWT."""
    user = await db.scalar(select(Usuario).where(Usuario.email == payload.email))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contrasena incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return TokenResponse(access_token=create_access_token(user.id))


@router.get("/me", response_model=UsuarioRead)
async def me(user: Usuario = Depends(get_current_user)) -> Usuario:
    """Devuelve el usuario asociado al token actual."""
    return user