import hashlib
import secrets
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from cut_clms_api.db import get_db_session
from cut_clms_api.models import (
    AuditLog,
    DeviceTelemetry,
    EndpointDevice,
    EnrollmentToken,
    InstalledSoftwareRecord,
)
from cut_clms_api.models import DeviceInventory as DeviceInventoryRecord
from cut_clms_api.schemas import (
    AcceptedResponse,
    APIErrorResponse,
    EnrollmentRequest,
    EnrollmentResponse,
    HealthPayload,
    HeartbeatRequest,
    InventoryPayload,
)

router = APIRouter(
    prefix="/api/v1/endpoints",
    tags=["Endpoint agent"],
    responses={
        status_code: {"model": APIErrorResponse}
        for status_code in (401, 403, 409, 422, 429, 503)
    },
)


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _device_credential_hash(credential: str) -> str:
    return hashlib.sha256(credential.encode("utf-8")).hexdigest()


def _get_authenticated_endpoint(
    authorization: str | None, session: Session
) -> EndpointDevice:
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing device bearer credential",
            headers={"WWW-Authenticate": "Bearer"},
        )
    credential = authorization[7:]
    if not 32 <= len(credential) <= 128:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid device credential"
        )
    endpoint = session.scalar(
        select(EndpointDevice).where(
            EndpointDevice.credential_hash == _device_credential_hash(credential),
            EndpointDevice.revoked_at.is_(None),
        )
    )
    if endpoint is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid device credential"
        )
    return endpoint


def _save_inventory(
    session: Session, endpoint: EndpointDevice, inventory: InventoryPayload
) -> None:
    data = inventory.model_dump(mode="json")
    record = DeviceInventoryRecord(
        endpoint_id=endpoint.id,
        collected_at=_utc(inventory.collected_at),
        operating_system=data["operating_system"],
        hardware={
            key: value for key, value in data["hardware"].items() if key != "storage"
        },
        storage_devices=data["hardware"]["storage"],
        network_interfaces=data["network_interfaces"],
    )
    session.add(record)
    session.flush()
    session.add_all(
        InstalledSoftwareRecord(
            endpoint_id=endpoint.id,
            inventory_id=record.id,
            name=item.name,
            version=item.version,
            publisher=item.publisher,
        )
        for item in inventory.installed_software
    )
    session.add(_telemetry(endpoint.id, inventory.collected_at, inventory.health))


def _telemetry(
    endpoint_id: UUID, reported_at: datetime, health: HealthPayload
) -> DeviceTelemetry:
    return DeviceTelemetry(
        endpoint_id=endpoint_id,
        agent_reported_at=_utc(reported_at),
        cpu_utilization_percent=health.cpu_utilization_percent,
        memory_utilization_percent=health.memory_utilization_percent,
        uptime_seconds=health.uptime_seconds,
        agent_status=health.agent_status,
        disk_health=[item.model_dump(mode="json") for item in health.disks],
    )


@router.post(
    "/enroll",
    response_model=EnrollmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Enroll an endpoint using a single-use institutional token",
)
def enroll_endpoint(
    request: EnrollmentRequest,
    session: Annotated[Session, Depends(get_db_session)],
    enrollment_token: Annotated[str | None, Header(alias="X-Enrollment-Token")] = None,
) -> EnrollmentResponse:
    if enrollment_token is None or not 32 <= len(enrollment_token) <= 128:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing enrollment token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    device_id = request.inventory.identity.device_id
    if device_id is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A stable device identifier is required for enrollment",
        )

    now = datetime.now(UTC)
    token = session.scalar(
        select(EnrollmentToken)
        .where(
            EnrollmentToken.token_hash == _token_hash(enrollment_token),
            EnrollmentToken.consumed_at.is_(None),
            EnrollmentToken.revoked_at.is_(None),
        )
        .with_for_update()
    )
    if token is None or _utc(token.expires_at) <= now:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Enrollment token is invalid, expired, or already used",
        )
    existing_endpoint = session.scalar(
        select(EndpointDevice)
        .where(EndpointDevice.device_id == device_id)
        .with_for_update()
    )
    if existing_endpoint is not None and existing_endpoint.revoked_at is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This device is already enrolled",
        )
    if (
        existing_endpoint is not None
        and existing_endpoint.institution_id != token.institution_id
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This device belongs to another institution",
        )

    credential = secrets.token_urlsafe(32)
    if existing_endpoint is None:
        endpoint = EndpointDevice(
            institution_id=token.institution_id,
            device_id=device_id,
            credential_hash=_device_credential_hash(credential),
            hostname=request.inventory.identity.hostname,
            status=request.inventory.health.agent_status,
            agent_version=request.agent_version,
            os_name=request.inventory.operating_system.name,
            os_release=request.inventory.operating_system.release,
            last_seen_at=now,
        )
        audit_action = "endpoint.enrolled"
    else:
        endpoint = existing_endpoint
        endpoint.credential_hash = _device_credential_hash(credential)
        endpoint.hostname = request.inventory.identity.hostname
        endpoint.status = request.inventory.health.agent_status
        endpoint.agent_version = request.agent_version
        endpoint.os_name = request.inventory.operating_system.name
        endpoint.os_release = request.inventory.operating_system.release
        endpoint.enrolled_at = now
        endpoint.last_seen_at = now
        endpoint.revoked_at = None
        audit_action = "endpoint.reenrolled"
    token.consumed_at = now
    session.add(endpoint)
    session.flush()
    _save_inventory(session, endpoint, request.inventory)
    session.add(
        AuditLog(
            institution_id=endpoint.institution_id,
            actor_type="endpoint",
            actor_id=endpoint.id,
            action=audit_action,
            endpoint_id=endpoint.id,
            details={
                "hostname": endpoint.hostname,
                "agent_version": endpoint.agent_version,
            },
        )
    )
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This device or enrollment token has already been used",
        ) from None
    return EnrollmentResponse(endpoint_id=endpoint.id, device_credential=credential)


@router.post(
    "/heartbeat",
    response_model=AcceptedResponse,
    summary="Submit device health and agent status",
)
def submit_heartbeat(
    request: HeartbeatRequest,
    session: Annotated[Session, Depends(get_db_session)],
    authorization: Annotated[str | None, Header()] = None,
) -> AcceptedResponse:
    endpoint = _get_authenticated_endpoint(authorization, session)
    now = datetime.now(UTC)
    endpoint.last_seen_at = now
    endpoint.status = request.health.agent_status
    endpoint.agent_version = request.agent_version
    session.add(_telemetry(endpoint.id, request.reported_at, request.health))
    session.commit()
    return AcceptedResponse(received_at=now)


@router.post(
    "/inventory",
    response_model=AcceptedResponse,
    summary="Submit the authenticated endpoint's latest inventory",
)
def submit_inventory(
    inventory: InventoryPayload,
    session: Annotated[Session, Depends(get_db_session)],
    authorization: Annotated[str | None, Header()] = None,
) -> AcceptedResponse:
    endpoint = _get_authenticated_endpoint(authorization, session)
    if inventory.identity.device_id != endpoint.device_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inventory identity does not match the authenticated endpoint",
        )
    endpoint.hostname = inventory.identity.hostname
    endpoint.os_name = inventory.operating_system.name
    endpoint.os_release = inventory.operating_system.release
    endpoint.status = inventory.health.agent_status
    endpoint.last_seen_at = datetime.now(UTC)
    _save_inventory(session, endpoint, inventory)
    session.commit()
    return AcceptedResponse(received_at=datetime.now(UTC))
