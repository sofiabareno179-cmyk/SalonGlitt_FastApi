"""Fabrica de endpoints CRUD protegidos para modelos simples."""
from copy import copy
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, create_model
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models import Base


def build_crud_router(
    model: type[Base],
    create_schema: type[BaseModel],
    read_schema: type[BaseModel],
    *,
    prefix: str,
    tags: list[str],
) -> APIRouter:
    """Crea listado, detalle, alta, edicion parcial y borrado para un modelo."""
    router = APIRouter(
        prefix=prefix,
        tags=tags,
        dependencies=[Depends(get_current_user)],
    )

    partial_fields: dict[str, tuple[Any, Any]] = {}
    for field_name, field_info in create_schema.model_fields.items():
        optional_info = copy(field_info)
        optional_info.default = None
        partial_fields[field_name] = (field_info.annotation | None, optional_info)
    update_schema = create_model(f"{create_schema.__name__}Patch", **partial_fields)

    async def list_items(db: AsyncSession = Depends(get_db)) -> list[Any]:
        result = await db.scalars(select(model))
        return list(result.all())

    list_items.__name__ = f"list_{model.__tablename__}"
    router.add_api_route("", list_items, methods=["GET"], response_model=list[read_schema])

    async def get_item(item_id: int, db: AsyncSession = Depends(get_db)) -> Any:
        item = await db.get(model, item_id)
        if item is None:
            raise HTTPException(status_code=404, detail="Registro no encontrado")
        return item

    get_item.__name__ = f"get_{model.__tablename__}"
    router.add_api_route("/{item_id}", get_item, methods=["GET"], response_model=read_schema)

    async def create_item(payload: Any, db: AsyncSession = Depends(get_db)) -> Any:
        item = model(**payload.model_dump())
        db.add(item)
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            raise HTTPException(status_code=409, detail="Conflicto con un registro existente") from None
        await db.refresh(item)
        return item

    create_item.__name__ = f"create_{model.__tablename__}"
    create_item.__annotations__["payload"] = create_schema
    router.add_api_route(
        "", create_item, methods=["POST"], response_model=read_schema,
        status_code=status.HTTP_201_CREATED,
    )

    async def update_item(
        item_id: int,
        payload: Any,
        db: AsyncSession = Depends(get_db),
    ) -> Any:
        item = await db.get(model, item_id)
        if item is None:
            raise HTTPException(status_code=404, detail="Registro no encontrado")
        for field_name, value in payload.model_dump(exclude_unset=True).items():
            setattr(item, field_name, value)
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            raise HTTPException(status_code=409, detail="Conflicto con un registro existente") from None
        await db.refresh(item)
        return item

    update_item.__name__ = f"patch_{model.__tablename__}"
    update_item.__annotations__["payload"] = update_schema
    router.add_api_route(
        "/{item_id}", update_item, methods=["PATCH"], response_model=read_schema
    )

    async def delete_item(item_id: int, db: AsyncSession = Depends(get_db)) -> Response:
        item = await db.get(model, item_id)
        if item is None:
            raise HTTPException(status_code=404, detail="Registro no encontrado")
        await db.delete(item)
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            raise HTTPException(status_code=409, detail="No se puede borrar: hay datos relacionados") from None
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    delete_item.__name__ = f"delete_{model.__tablename__}"
    router.add_api_route(
        "/{item_id}", delete_item, methods=["DELETE"], status_code=status.HTTP_204_NO_CONTENT
    )
    return router