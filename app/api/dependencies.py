from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_db
from app.core.security import decode_acces_token
from app.models.user import User, UserRole
from app.repositories.appointment import AppointmentRepository
from app.repositories.contact import ContactRepository
from app.repositories.customer import CustomerRepository
from app.repositories.interaction import InteractionRepository
from app.repositories.refresh_token import RefreshTokenRepository
from app.repositories.service import ServiceRepository
from app.repositories.ticket import TicketRepository
from app.repositories.ticket_comment import TicketCommentRepository
from app.repositories.user import UserRepository
from app.services.appointment import AppointmentService
from app.services.auth import AuthService
from app.services.contact import ContactService
from app.services.customer import CustomerService
from app.services.interaction import InteractionService
from app.services.service_catalog import ServiceCatalogService
from app.services.ticket import TicketService
from app.services.ticket_comment import TicketCommentService
from app.services.user import UserService

oauth_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_user_repository(
    db: Annotated[AsyncSession, Depends(get_async_db)],
) -> UserRepository:
    return UserRepository(db=db)


def get_user_service(
    repo: Annotated[UserRepository, Depends(get_user_repository)],
) -> UserService:
    return UserService(repo)


async def get_current_user(
    token: Annotated[str, Depends(oauth_scheme)],
    db: Annotated[AsyncSession, Depends(get_async_db)],
) -> User:
    payload = decode_acces_token(token, expected_type="access")

    email: str = payload.get("sub")
    if email is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token not contain user id"
        )

    user_repo = UserRepository(db)
    user = await user_repo.get_by_email(email)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not fouund"
        )

    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    if getattr(current_user, "disabled", False) or not getattr(
        current_user, "is_active", True
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="User inactive o disabled"
        )

    return current_user


def get_refresh_token_repository(
    db: Annotated[
        AsyncSession,
        Depends(get_async_db),
    ],
) -> RefreshTokenRepository:
    return RefreshTokenRepository(db=db)


def get_auth_service(
    repo: Annotated[UserRepository, Depends(get_user_repository)],
    refresh_repo: Annotated[
        RefreshTokenRepository, Depends(get_refresh_token_repository)
    ],
):
    return AuthService(user_repo=repo, refresh_repo=refresh_repo)


class RoleChecker:
    def __init__(self, allowed_roles: list[UserRole]):
        self.allowed_roles = allowed_roles

    def __call__(
        self, current_user: Annotated[User, Depends(get_current_active_user)]
    ) -> User:
        if current_user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operation not permitted: insfficient privileges",
            )

        return current_user


def require_role(allowed_roles: list[UserRole]):
    return RoleChecker(allowed_roles)


ActiveUser = Annotated[User, Depends(get_current_active_user)]


def get_customer_repository(
    db: Annotated[AsyncSession, Depends(get_async_db)],
) -> CustomerRepository:
    return CustomerRepository(db=db)


def get_customer_service(
    repo: Annotated[CustomerRepository, Depends(get_customer_repository)],
) -> CustomerService:
    return CustomerService(repo)


def get_contact_repository(
    db: Annotated[AsyncSession, Depends(get_async_db)],
) -> ContactRepository:
    return ContactRepository(db=db)


def get_contact_service(
    repo: Annotated[ContactRepository, Depends(get_contact_repository)],
) -> ContactService:
    return ContactService(repo)


def get_service_repository(
    db: Annotated[AsyncSession, Depends(get_async_db)],
) -> ServiceRepository:
    return ServiceRepository(db=db)


def get_service_catalog_service(
    repo: Annotated[ServiceRepository, Depends(get_service_repository)],
) -> ServiceCatalogService:
    return ServiceCatalogService(repo)


def get_interaction_repository(
    db: Annotated[AsyncSession, Depends(get_async_db)],
) -> InteractionRepository:
    return InteractionRepository(db=db)


def get_interaction_service(
    repo: Annotated[InteractionRepository, Depends(get_interaction_repository)],
) -> InteractionService:
    return InteractionService(repo)


def get_appointment_repository(
    db: Annotated[AsyncSession, Depends(get_async_db)],
) -> AppointmentRepository:
    return AppointmentRepository(db=db)


def get_appointment_service(
    repo: Annotated[AppointmentRepository, Depends(get_appointment_repository)],
) -> AppointmentService:
    return AppointmentService(repo)


def get_ticket_repository(
    db: Annotated[AsyncSession, Depends(get_async_db)],
) -> TicketRepository:
    return TicketRepository(db=db)


def get_ticket_service(
    repo: Annotated[TicketRepository, Depends(get_ticket_repository)],
) -> TicketService:
    return TicketService(repo)


def get_ticket_comment_repository(
    db: Annotated[AsyncSession, Depends(get_async_db)],
) -> TicketCommentRepository:
    return TicketCommentRepository(db=db)


def get_ticket_comment_service(
    repo: Annotated[TicketCommentRepository, Depends(get_ticket_comment_repository)],
) -> TicketCommentService:
    return TicketCommentService(repo)
