from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import ActiveUser, get_interaction_service
from app.schemas.interaction import (
    InteractionCreate,
    InteractionFilters,
    InteractionResponse,
    InteractionUpdate,
)
from app.schemas.pagination import PaginateResponse
from app.services.interaction import InteractionService

router = APIRouter(prefix="/interactions", tags=["Interaction"])
InteractionDependency = Annotated[InteractionService, Depends(get_interaction_service)]


@router.post(
    "", response_model=InteractionResponse, status_code=status.HTTP_201_CREATED
)
async def create_interaction(
    data: InteractionCreate,
    actor: ActiveUser,
    service: InteractionDependency,
):
    return await service.create(data, actor)


@router.get("", response_model=PaginateResponse[InteractionResponse])
async def list_interactions(
    filters: Annotated[InteractionFilters, Query()],
    actor: ActiveUser,
    service: InteractionDependency,
):
    return await service.get_all(filters, actor)


@router.get("/{interaction_id}", response_model=InteractionResponse)
async def get_interaction(
    interaction_id: UUID,
    actor: ActiveUser,
    service: InteractionDependency,
):
    return await service.get_by_id(interaction_id, actor)


@router.patch("/{interaction_id}", response_model=InteractionResponse)
async def update_interaction(
    interaction_id: UUID,
    data: InteractionUpdate,
    actor: ActiveUser,
    service: InteractionDependency,
):
    return await service.update(interaction_id, data, actor)
