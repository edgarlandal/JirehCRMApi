from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from loguru import logger

from app.api.dependencies import get_user_service, require_role
from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserProfileUpdate, UserReponse
from app.services.user import UserService

router = APIRouter(
    prefix="/users",
    tags=["Users"],
    dependencies=[Depends(require_role([UserRole.USER, UserRole.ADMIN]))],
)


@router.post("", response_model=UserReponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_in: UserCreate, service: Annotated[UserService, Depends(get_user_service)]
):
    return await service.register_user(user_in)


@router.get("/me", response_model=UserReponse)
async def get_my_profile(
    curr_user: Annotated[User, Depends(require_role([UserRole.USER]))],
):
    return curr_user


@router.patch("/me", response_model=UserReponse)
async def update_profile(
    user_in: UserProfileUpdate,
    actor: Annotated[User, Depends(require_role([UserRole.USER]))],
    service: Annotated[UserService, Depends(get_user_service)],
):
    return await service.update_my_profile(user_id=actor.id, user_in=user_in)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def delete_profile(
    actor: Annotated[User, Depends(require_role([UserRole.USER]))],
    service: Annotated[UserService, Depends(get_user_service)],
):
    await service.delete_user(user_id=actor.id)

    return Response(status_code=status.HTTP_204_NO_CONTENT)
