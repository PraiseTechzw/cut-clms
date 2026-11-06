import argparse
import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select

from cut_clms_api.db import create_database_engine, create_session_factory
from cut_clms_api.models import AuditLog, EndpointDevice, EnrollmentToken, Institution
from cut_clms_api.settings import get_settings


def _create_institution(name: str, code: str) -> None:
    engine = create_database_engine()
    try:
        with create_session_factory(engine)() as session:
            institution = Institution(name=name, code=code)
            session.add(institution)
            session.commit()
            print(institution.id)
    finally:
        engine.dispose()


def _create_enrollment_token(institution_id: UUID, expires_in_hours: int) -> None:
    engine = create_database_engine()
    try:
        with create_session_factory(engine)() as session:
            institution = session.scalar(
                select(Institution).where(Institution.id == institution_id)
            )
            if institution is None:
                raise SystemExit("Institution not found")
            token = secrets.token_urlsafe(32)
            session.add(
                EnrollmentToken(
                    institution_id=institution_id,
                    token_hash=hashlib.sha256(token.encode("utf-8")).hexdigest(),
                    expires_at=datetime.now(UTC) + timedelta(hours=expires_in_hours),
                )
            )
            session.commit()
            print(token)
    finally:
        engine.dispose()


def _revoke_endpoint(endpoint_id: UUID) -> None:
    engine = create_database_engine()
    try:
        with create_session_factory(engine)() as session:
            endpoint = session.scalar(
                select(EndpointDevice).where(EndpointDevice.id == endpoint_id)
            )
            if endpoint is None:
                raise SystemExit("Endpoint not found")
            if endpoint.revoked_at is not None:
                raise SystemExit("Endpoint credential is already revoked")
            endpoint.revoked_at = datetime.now(UTC)
            session.add(
                AuditLog(
                    institution_id=endpoint.institution_id,
                    actor_type="operator",
                    actor_id=None,
                    action="endpoint.credential_revoked",
                    endpoint_id=endpoint.id,
                    details={},
                )
            )
            session.commit()
    finally:
        engine.dispose()


def main() -> None:
    get_settings()
    parser = argparse.ArgumentParser(
        description="CUT-CLMS API administration utilities"
    )
    commands = parser.add_subparsers(dest="command", required=True)

    institution = commands.add_parser("create-institution")
    institution.add_argument("--name", required=True)
    institution.add_argument("--code", required=True)

    enrollment = commands.add_parser("create-enrollment-token")
    enrollment.add_argument("--institution-id", type=UUID, required=True)
    enrollment.add_argument("--expires-in-hours", type=int, default=24)

    revoke = commands.add_parser("revoke-endpoint")
    revoke.add_argument("--endpoint-id", type=UUID, required=True)

    args = parser.parse_args()
    if args.command == "create-institution":
        _create_institution(args.name, args.code)
    elif args.command == "create-enrollment-token":
        if args.expires_in_hours < 1:
            parser.error("--expires-in-hours must be positive")
        _create_enrollment_token(args.institution_id, args.expires_in_hours)
    elif args.command == "revoke-endpoint":
        _revoke_endpoint(args.endpoint_id)
