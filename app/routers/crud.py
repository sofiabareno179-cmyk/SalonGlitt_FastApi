"""Fabrica de endpoints CRUD protegidos para modelos simples."""
from collections.abc import Sequence
from copy import copy
from enum import Enum
from types import GenericAlias
from typing import Any, cast

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, create_model
from sqlalchemy import inspect, select
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
    tags: Sequence[str | Enum],
) -> APIRouter:
    """Crea listado, detalle, alta, edicion parcial y borrado para un modelo."""
    router = APIRouter(
        prefix=prefix,
        tags=list(tags),
        dependencies=[Depends(get_current_user)],
    )

    partial_fields: dict[str, Any] = {}
    for field_name, field_info in create_schema.model_fields.items():
        optional_info = copy(field_info)
        optional_info.default = None
        field_type = cast(Any, field_info.annotation)
        partial_fields[field_name] = (field_type | None, optional_info)
    update_schema = create_model(f"{create_schema.__name__}Patch", **partial_fields)
    mapper = inspect(model)
    primary_key_fields = [
        mapper.get_property_by_column(column).key for column in mapper.primary_key
    ]

    async def list_items(db: AsyncSession = Depends(get_db)) -> list[Base]:
        result = await db.scalars(select(model))
        return list(result.all())

    list_items.__name__ = f"list_{model.__tablename__}"
    router.add_api_route(
        "",
        list_items,
        methods=["GET"],
        response_model=GenericAlias(list, read_schema),
    )

    if len(primary_key_fields) == 1:
        async def get_item_by_id(
            item_id: int, db: AsyncSession = Depends(get_db)
        ) -> Base:
            item = await db.get(model, item_id)
            if item is None:
                raise HTTPException(status_code=404, detail="Registro no encontrado")
            return item

        get_item_by_id.__name__ = f"get_{model.__tablename__}"
        router.add_api_route(
            "/{item_id}", get_item_by_id, methods=["GET"], response_model=read_schema
        )
    elif len(primary_key_fields) == 2:
        async def get_item_by_composite_key(
            first_key: int,
            second_key: int,
            db: AsyncSession = Depends(get_db),
        ) -> Base:
            item = await db.get(model, (first_key, second_key))
            if item is None:
                raise HTTPException(status_code=404, detail="Registro no encontrado")
            return item

        get_item_by_composite_key.__name__ = f"get_{model.__tablename__}"
        router.add_api_route(
            "/{first_key}/{second_key}",
            get_item_by_composite_key,
            methods=["GET"],
            response_model=read_schema,
        )
    else:
        raise ValueError(f"{model.__name__} must have one or two primary-key columns")

    async def create_item(payload: BaseModel, db: AsyncSession = Depends(get_db)) -> Base:
        item = model(**payload.model_dump())
        db.add(item)
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            raise HTTPException(
                status_code=409, detail="Conflicto con un registro existente"
            ) from None
        await db.refresh(item)
        return item

    create_item.__name__ = f"create_{model.__tablename__}"
    create_item.__annotations__["payload"] = create_schema
    router.add_api_route(
        "", create_item, methods=["POST"], response_model=read_schema,
        status_code=status.HTTP_201_CREATED,
    )

    if len(primary_key_fields) == 1:
        async def update_item_by_id(
            item_id: int,
            payload: BaseModel,
            db: AsyncSession = Depends(get_db),
        ) -> Base:
            item = await db.get(model, item_id)
            if item is None:
                raise HTTPException(status_code=404, detail="Registro no encontrado")
            for field_name, value in payload.model_dump(exclude_unset=True).items():
                setattr(item, field_name, value)
            try:
                await db.commit()
            except IntegrityError:
                await db.rollback()
                raise HTTPException(
                    status_code=409, detail="Conflicto con un registro existente"
                ) from None
            await db.refresh(item)
            return item

        update_item_by_id.__name__ = f"patch_{model.__tablename__}"
        update_item_by_id.__annotations__["payload"] = update_schema
        router.add_api_route(
            "/{item_id}",
            update_item_by_id,
            methods=["PATCH"],
            response_model=read_schema,
        )
    else:
        async def update_item_by_composite_key(
            first_key: int,
            second_key: int,
            payload: BaseModel,
            db: AsyncSession = Depends(get_db),
        ) -> Base:
            item = await db.get(model, (first_key, second_key))
            if item is None:
                raise HTTPException(status_code=404, detail="Registro no encontrado")
            for field_name, value in payload.model_dump(exclude_unset=True).items():
                setattr(item, field_name, value)
            try:
                await db.commit()
            except IntegrityError:
                await db.rollback()
                raise HTTPException(
                    status_code=409, detail="Conflicto con un registro existente"
                ) from None
            await db.refresh(item)
            return item

        update_item_by_composite_key.__name__ = f"patch_{model.__tablename__}"
        update_item_by_composite_key.__annotations__["payload"] = update_schema
        router.add_api_route(
            "/{first_key}/{second_key}",
            update_item_by_composite_key,
            methods=["PATCH"],
            response_model=read_schema,
        )

    if len(primary_key_fields) == 1:
        async def delete_item_by_id(
            item_id: int, db: AsyncSession = Depends(get_db)
        ) -> Response:
            item = await db.get(model, item_id)
            if item is None:
                raise HTTPException(status_code=404, detail="Registro no encontrado")
            await db.delete(item)
            try:
                await db.commit()
            except IntegrityError:
                await db.rollback()
                raise HTTPException(
                    status_code=409,
                    detail="No se puede borrar: hay datos relacionados",
                ) from None
            return Response(status_code=status.HTTP_204_NO_CONTENT)

        delete_item_by_id.__name__ = f"delete_{model.__tablename__}"
        router.add_api_route(
            "/{item_id}",
            delete_item_by_id,
            methods=["DELETE"],
            status_code=status.HTTP_204_NO_CONTENT,
        )
    else:
        async def delete_item_by_composite_key(
            first_key: int,
            second_key: int,
            db: AsyncSession = Depends(get_db),
        ) -> Response:
            item = await db.get(model, (first_key, second_key))
            if item is None:
                raise HTTPException(status_code=404, detail="Registro no encontrado")
            await db.delete(item)
            try:
                await db.commit()
            except IntegrityError:
                await db.rollback()
                raise HTTPException(
                    status_code=409,
                    detail="No se puede borrar: hay datos relacionados",
                ) from None
            return Response(status_code=status.HTTP_204_NO_CONTENT)

        delete_item_by_composite_key.__name__ = f"delete_{model.__tablename__}"
        router.add_api_route(
            "/{first_key}/{second_key}",
            delete_item_by_composite_key,
            methods=["DELETE"],
            status_code=status.HTTP_204_NO_CONTENT,
        )
    return router