from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from cut_clms_api.db import get_app_settings, get_db_session
from cut_clms_api.models import InstitutionalUser, UserRole
from cut_clms_api.settings import Settings

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class AuthenticatedUser:
    id: UUID
    institution_id: UUID
    email: str
    roles: frozenset[UserRole]


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    session: Annotated[Session, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> AuthenticatedUser:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing bearer token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized
    if (
        settings.auth_public_key is None
        or settings.auth_issuer is None
        or settings.auth_audience is None
    ):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Human-user authentication is not configured",
        )
    try:
        claims = jwt.decode(
            credentials.credentials,
            settings.auth_public_key.get_secret_value(),
            algorithms=["RS256"],
            issuer=settings.auth_issuer,
            audience=settings.auth_audience,
            options={"require": ["sub", "iss", "aud", "institution_id"]},
        )
        user_id = UUID(claims["sub"])
        institution_id = UUID(claims["institution_id"])
    except (jwt.InvalidTokenError, ValueError, KeyError, TypeError, AttributeError):
        raise unauthorized from None

    user = session.scalar(
        select(InstitutionalUser)
        .options(selectinload(InstitutionalUser.roles))
        .where(
            InstitutionalUser.id == user_id,
            InstitutionalUser.institution_id == institution_id,
            InstitutionalUser.active.is_(True),
        )
    )
    if user is None:
        raise unauthorized
    return AuthenticatedUser(
        id=user.id,
        institution_id=user.institution_id,
        email=user.email,
        roles=frozenset(role.role for role in user.roles),
    )


def require_roles(*allowed_roles: UserRole) -> Callable[..., AuthenticatedUser]:
    def role_dependency(
        user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    ) -> AuthenticatedUser:
        if not user.roles.intersection(allowed_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient role",
            )
        return user

    return role_dependency
