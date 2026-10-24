from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from loguru import logger

from app.api.dependencies import get_user_service, require_role
from app.models.user import User, UserRole
from app.schemas.pagination import PaginateResponse, PaginationParams
from app.schemas.user import UserAdminUpdate, UserCreate, UserReponse
from app.services.user import UserService

admin_required = require_role([UserRole.ADMIN])

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
    dependencies=[Depends(admin_required)],
)


@router.post("", response_model=UserReponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    actor: Annotated[User, Depends(admin_required)],
    user_in: UserCreate,
    service: Annotated[UserService, Depends(get_user_service)],
):
    user = await service.register_user(user_in)
    logger.info(
        "user_created",
        event="admin.user_created",
        actor_id=str(actor.id),
        user_id=str(user.id),
    )
    return user


@router.get("", response_model=PaginateResponse[UserReponse])
async def list_users(
    actor: Annotated[User, Depends(admin_required)],
    service: Annotated[UserService, Depends(get_user_service)],
    pagination: Annotated[PaginationParams, Depends()],
):
    result = await service.get_users(pagination)
    logger.info("users_listed", event="admin.users_listed", actor_id=str(actor.id))
    return result


@router.get("/{user_id}", response_model=UserReponse)
async def get_user_by_id(
    user_id: UUID, service: Annotated[UserService, Depends(get_user_service)]
):
    return await service.get_user_by_id(str(user_id))


@router.patch("/{user_id}", response_model=UserReponse)
async def update_user(
    user_id: UUID,
    user_in: UserAdminUpdate,
    actor: Annotated[User, Depends(admin_required)],
    service: Annotated[UserService, Depends(get_user_service)],
):
    user = await service.admin_update_user(user_id=str(user_id), user_in=user_in)
    logger.info(
        "user_updated",
        event="admin.user_updated",
        actor_id=str(actor.id),
        user_id=str(user.id),
        fields=list(user_in.model_fields_set),
    )
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: UUID,
    actor: Annotated[User, Depends(admin_required)],
    service: Annotated[UserService, Depends(get_user_service)],
):
    actor_id = str(actor.id)
    await service.delete_user(str(user_id))
    logger.info(
        "user_deleted",
        event="admin.user_deleted",
        actor_id=actor_id,
        user_id=str(user_id),
    )
