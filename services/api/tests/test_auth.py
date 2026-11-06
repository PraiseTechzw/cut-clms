from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from cut_clms_api.auth import get_current_user, require_roles
from cut_clms_api.models import (
    Institution,
    InstitutionalUser,
    InstitutionalUserRole,
    UserRole,
)
from cut_clms_api.settings import Settings


def _key_pair() -> tuple[str, str]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
    public_pem = (
        private_key.public_key()
        .public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
        )
        .decode()
    )
    return private_pem, public_pem


def test_rs256_identity_loads_institution_roles(engine) -> None:  # type: ignore[no-untyped-def]
    private_key, public_key = _key_pair()
    settings = Settings(
        environment="test",
        auth_public_key=public_key,
        auth_issuer="https://identity.example.edu",
        auth_audience="cut-clms-api",
    )
    with Session(engine) as session:
        institution = Institution(name="CUT", code="AUTH-CUT")
        session.add(institution)
        session.flush()
        user = InstitutionalUser(
            institution_id=institution.id,
            email="operator@example.edu",
            display_name="Operator",
        )
        user.roles.append(InstitutionalUserRole(role=UserRole.TECHNICIAN))
        session.add(user)
        session.commit()
        user_id, institution_id = user.id, institution.id

        token = jwt.encode(
            {
                "sub": str(user_id),
                "institution_id": str(institution_id),
                "iss": settings.auth_issuer,
                "aud": settings.auth_audience,
                "exp": datetime.now(UTC) + timedelta(minutes=5),
            },
            private_key,
            algorithm="RS256",
        )
        authenticated = get_current_user(
            HTTPAuthorizationCredentials(scheme="Bearer", credentials=token),
            session,
            settings,
        )

    assert authenticated.id == user_id
    assert authenticated.institution_id == institution_id
    assert authenticated.roles == frozenset({UserRole.TECHNICIAN})
    assert require_roles(UserRole.TECHNICIAN)(authenticated) == authenticated
    with pytest.raises(HTTPException) as raised:
        require_roles(UserRole.INSTITUTION_ADMIN)(authenticated)
    assert raised.value.status_code == 403


def test_human_token_rejects_wrong_audience_and_invalid_identity(engine) -> None:  # type: ignore[no-untyped-def]
    private_key, public_key = _key_pair()
    settings = Settings(
        environment="test",
        auth_public_key=public_key,
        auth_issuer="https://identity.example.edu",
        auth_audience="cut-clms-api",
    )
    token = jwt.encode(
        {
            "sub": str(uuid4()),
            "institution_id": str(uuid4()),
            "iss": settings.auth_issuer,
            "aud": "another-api",
            "exp": datetime.now(UTC) + timedelta(minutes=5),
        },
        private_key,
        algorithm="RS256",
    )
    with Session(engine) as session, pytest.raises(HTTPException) as raised:
        get_current_user(
            HTTPAuthorizationCredentials(scheme="Bearer", credentials=token),
            session,
            settings,
        )

    assert raised.value.status_code == 401
