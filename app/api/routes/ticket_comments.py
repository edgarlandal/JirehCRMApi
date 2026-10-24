from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import ActiveUser, get_ticket_comment_service
from app.schemas.pagination import PaginateResponse
from app.schemas.ticket_comment import (
    TicketCommentCreate,
    TicketCommentFilters,
    TicketCommentResponse,
    TicketCommentUpdate,
)
from app.services.ticket_comment import TicketCommentService

router = APIRouter(prefix="/ticket-comments", tags=["TicketComment"])
TicketCommentDependency = Annotated[
    TicketCommentService, Depends(get_ticket_comment_service)
]


@router.post(
    "", response_model=TicketCommentResponse, status_code=status.HTTP_201_CREATED
)
async def create_ticket_comment(
    data: TicketCommentCreate,
    actor: ActiveUser,
    service: TicketCommentDependency,
):
    return await service.create(data, actor)


@router.get("", response_model=PaginateResponse[TicketCommentResponse])
async def list_ticket_comments(
    filters: Annotated[TicketCommentFilters, Query()],
    actor: ActiveUser,
    service: TicketCommentDependency,
):
    return await service.get_all(filters, actor)


@router.get("/{comment_id}", response_model=TicketCommentResponse)
async def get_ticket_comment(
    comment_id: UUID,
    actor: ActiveUser,
    service: TicketCommentDependency,
):
    return await service.get_by_id(comment_id, actor)


@router.patch("/{comment_id}", response_model=TicketCommentResponse)
async def update_ticket_comment(
    comment_id: UUID,
    data: TicketCommentUpdate,
    actor: ActiveUser,
    service: TicketCommentDependency,
):
    return await service.update(comment_id, data, actor)
