from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import ActiveUser, get_ticket_service
from app.schemas.pagination import PaginateResponse
from app.schemas.ticket import TicketCreate, TicketFilters, TicketResponse, TicketUpdate
from app.services.ticket import TicketService

router = APIRouter(prefix="/tickets", tags=["Ticket"])
TicketDependency = Annotated[TicketService, Depends(get_ticket_service)]


@router.post("", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
async def create_ticket(
    data: TicketCreate,
    actor: ActiveUser,
    service: TicketDependency,
):
    return await service.create(data, actor)


@router.get("", response_model=PaginateResponse[TicketResponse])
async def list_tickets(
    filters: Annotated[TicketFilters, Query()],
    actor: ActiveUser,
    service: TicketDependency,
):
    return await service.get_all(filters, actor)


@router.get("/{ticket_id}", response_model=TicketResponse)
async def get_ticket(
    ticket_id: UUID,
    actor: ActiveUser,
    service: TicketDependency,
):
    return await service.get_by_id(ticket_id, actor)


@router.patch("/{ticket_id}", response_model=TicketResponse)
async def update_ticket(
    ticket_id: UUID,
    data: TicketUpdate,
    actor: ActiveUser,
    service: TicketDependency,
):
    return await service.update(ticket_id, data, actor)
