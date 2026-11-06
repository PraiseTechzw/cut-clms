import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from cut_clms_api.models import (
    AuditLog,
    DeviceInventory,
    DeviceTelemetry,
    EndpointDevice,
    EnrollmentToken,
    InstalledSoftwareRecord,
    Institution,
)


def _inventory(device_id: str = "a" * 64) -> dict[str, object]:
    return {
        "schema_version": 1,
        "collected_at": datetime.now(UTC).isoformat(),
        "identity": {"device_id": device_id, "hostname": "lab-01"},
        "operating_system": {
            "name": "Linux",
            "release": "6.8",
            "version": "test-build",
            "architecture": "x86_64",
        },
        "hardware": {
            "cpu": {"model": "Test CPU", "physical_cores": 4, "logical_cores": 8},
            "total_memory_bytes": 8192,
            "storage": [
                {
                    "device": "/dev/sda1",
                    "mountpoint": "/",
                    "filesystem": "ext4",
                    "total_bytes": 100000,
                    "used_bytes": 40000,
                    "free_bytes": 60000,
                }
            ],
            "manufacturer": None,
            "model": None,
            "serial_number": None,
        },
        "installed_software": [
            {"name": "Example package", "version": "1.2", "publisher": "CUT"}
        ],
        "network_interfaces": [
            {
                "name": "eth0",
                "mac_address": "aa:bb:cc:dd:ee:ff",
                "addresses": [
                    {
                        "address": "192.0.2.10",
                        "family": "ipv4",
                        "netmask": "255.255.255.0",
                    }
                ],
                "is_up": True,
            }
        ],
        "health": {
            "cpu_utilization_percent": 20,
            "memory_utilization_percent": 35,
            "disks": [
                {
                    "mountpoint": "/",
                    "utilization_percent": 40,
                    "available_bytes": 60000,
                }
            ],
            "uptime_seconds": 120,
            "agent_status": "healthy",
            "last_successful_communication_at": None,
        },
        "warnings": [],
    }


def _create_enrollment_token(
    session: Session, *, expired: bool = False, institution_id=None
) -> str:
    if institution_id is None:
        institution = Institution(name="CUT", code=f"CUT-{secrets.token_hex(4)}")
        session.add(institution)
        session.flush()
        institution_id = institution.id
    token = secrets.token_urlsafe(32)
    expires_at = (
        datetime.now(UTC) - timedelta(minutes=1)
        if expired
        else datetime.now(UTC) + timedelta(hours=1)
    )
    session.add(
        EnrollmentToken(
            institution_id=institution_id,
            token_hash=hashlib.sha256(token.encode()).hexdigest(),
            expires_at=expires_at,
        )
    )
    session.commit()
    return token


def _enroll(client, session_factory, *, device_id: str = "a" * 64):  # type: ignore[no-untyped-def]
    with session_factory() as session:
        token = _create_enrollment_token(session)
    response = client.post(
        "/api/v1/endpoints/enroll",
        headers={"X-Enrollment-Token": token},
        json={"agent_version": "0.1.0", "inventory": _inventory(device_id)},
    )
    return token, response


def test_enrollment_consumes_one_time_token_and_persists_inventory(
    client, engine
) -> None:  # type: ignore[no-untyped-def]
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    enrollment_token, response = _enroll(client, session_factory)

    assert response.status_code == 201
    body = response.json()
    credential = body["device_credential"]
    assert len(credential) >= 32

    with session_factory() as session:
        endpoint = session.scalar(select(EndpointDevice))
        token = session.scalar(select(EnrollmentToken))
        inventory = session.scalar(select(DeviceInventory))
        software = session.scalar(select(InstalledSoftwareRecord))
        telemetry = session.scalar(select(DeviceTelemetry))
        audit = session.scalar(select(AuditLog))

        assert endpoint is not None
        assert (
            endpoint.credential_hash == hashlib.sha256(credential.encode()).hexdigest()
        )
        assert endpoint.credential_hash != credential
        assert endpoint.device_id == "a" * 64
        assert token is not None and token.consumed_at is not None
        assert token.token_hash == hashlib.sha256(enrollment_token.encode()).hexdigest()
        assert (
            inventory is not None
            and inventory.storage_devices[0]["free_bytes"] == 60000
        )
        assert software is not None and software.name == "Example package"
        assert telemetry is not None and telemetry.agent_status == "healthy"
        assert audit is not None and credential not in str(audit.details)
        assert enrollment_token not in str(audit.details)


def test_enrollment_requires_valid_single_use_token(client, engine) -> None:  # type: ignore[no-untyped-def]
    with Session(engine) as session:
        expired_token = _create_enrollment_token(session, expired=True)

    response = client.post(
        "/api/v1/endpoints/enroll",
        headers={"X-Enrollment-Token": expired_token},
        json={"agent_version": "0.1.0", "inventory": _inventory()},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"

    session_factory = sessionmaker(bind=engine)
    token, first = _enroll(client, session_factory, device_id="b" * 64)
    assert first.status_code == 201
    replay = client.post(
        "/api/v1/endpoints/enroll",
        headers={"X-Enrollment-Token": token},
        json={"agent_version": "0.1.0", "inventory": _inventory("d" * 64)},
    )
    assert replay.status_code == 401


def test_enrollment_requires_device_id_and_token(client, engine) -> None:  # type: ignore[no-untyped-def]
    no_token = client.post(
        "/api/v1/endpoints/enroll",
        json={"agent_version": "0.1.0", "inventory": _inventory()},
    )
    assert no_token.status_code == 401

    with Session(engine) as session:
        token = _create_enrollment_token(session)
    payload = _inventory()
    payload["identity"]["device_id"] = None  # type: ignore[index]
    response = client.post(
        "/api/v1/endpoints/enroll",
        headers={"X-Enrollment-Token": token},
        json={"agent_version": "0.1.0", "inventory": payload},
    )
    assert response.status_code == 422


def test_heartbeat_authenticates_device_and_records_health(client, engine) -> None:  # type: ignore[no-untyped-def]
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    _, enrollment = _enroll(client, session_factory)
    credential = enrollment.json()["device_credential"]
    heartbeat = client.post(
        "/api/v1/endpoints/heartbeat",
        headers={"Authorization": f"Bearer {credential}"},
        json={
            "agent_version": "0.1.1",
            "reported_at": datetime.now(UTC).isoformat(),
            "health": _inventory()["health"],
        },
    )

    assert heartbeat.status_code == 200
    assert heartbeat.json()["status"] == "accepted"
    with session_factory() as session:
        endpoint = session.scalar(select(EndpointDevice))
        telemetry = session.scalars(select(DeviceTelemetry)).all()
        assert endpoint is not None and endpoint.agent_version == "0.1.1"
        assert endpoint.last_seen_at is not None
        assert len(telemetry) == 2


def test_inventory_requires_device_auth_and_matching_identity(client, engine) -> None:  # type: ignore[no-untyped-def]
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    _, enrollment = _enroll(client, session_factory)
    credential = enrollment.json()["device_credential"]
    bad_identity = client.post(
        "/api/v1/endpoints/inventory",
        headers={"Authorization": f"Bearer {credential}"},
        json=_inventory("c" * 64),
    )
    assert bad_identity.status_code == 403

    accepted = client.post(
        "/api/v1/endpoints/inventory",
        headers={"Authorization": f"Bearer {credential}"},
        json=_inventory(),
    )
    assert accepted.status_code == 200

    unauthorized = client.post(
        "/api/v1/endpoints/heartbeat",
        json={
            "agent_version": "0.1.0",
            "reported_at": datetime.now(UTC).isoformat(),
            "health": _inventory()["health"],
        },
    )
    assert unauthorized.status_code == 401
    assert unauthorized.headers.get("www-authenticate") == "Bearer"


def test_revoked_endpoint_can_reenroll_and_old_credential_stops_working(
    client, engine
) -> None:  # type: ignore[no-untyped-def]
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    _, original_response = _enroll(client, session_factory)
    original_credential = original_response.json()["device_credential"]
    with session_factory() as session:
        endpoint = session.scalar(select(EndpointDevice))
        assert endpoint is not None
        endpoint.revoked_at = datetime.now(UTC)
        institution_id = endpoint.institution_id
        session.commit()
        new_token = _create_enrollment_token(session, institution_id=institution_id)

    reenrolled = client.post(
        "/api/v1/endpoints/enroll",
        headers={"X-Enrollment-Token": new_token},
        json={"agent_version": "0.2.0", "inventory": _inventory()},
    )
    assert reenrolled.status_code == 201
    new_credential = reenrolled.json()["device_credential"]
    assert new_credential != original_credential

    old_credential_response = client.post(
        "/api/v1/endpoints/heartbeat",
        headers={"Authorization": f"Bearer {original_credential}"},
        json={
            "agent_version": "0.1.0",
            "reported_at": datetime.now(UTC).isoformat(),
            "health": _inventory()["health"],
        },
    )
    assert old_credential_response.status_code == 401
    with session_factory() as session:
        actions = session.scalars(select(AuditLog.action)).all()
        assert "endpoint.reenrolled" in actions


def test_validation_errors_use_structured_response(client) -> None:  # type: ignore[no-untyped-def]
    response = client.post(
        "/api/v1/endpoints/heartbeat",
        headers={"Authorization": "Bearer " + "x" * 40},
        json={"agent_version": "x", "reported_at": "not-a-date", "health": {}},
    )

    assert response.status_code == 422
    assert response.headers.get("x-request-id")
    assert response.json()["error"]["code"] == "validation_error"
    assert response.json()["error"]["details"]


def test_endpoint_routes_are_rate_limited_per_client(engine, settings) -> None:  # type: ignore[no-untyped-def]
    from fastapi.testclient import TestClient

    from cut_clms_api.main import create_app
    from cut_clms_api.settings import Settings

    limited_settings = Settings(
        database_url=settings.database_url,
        environment="test",
        rate_limit_requests=1,
        rate_limit_window_seconds=60,
    )
    with TestClient(create_app(limited_settings, engine)) as limited_client:
        first = limited_client.post("/api/v1/endpoints/heartbeat", json={})
        second = limited_client.post("/api/v1/endpoints/heartbeat", json={})

    assert first.status_code == 422
    assert second.status_code == 429
    assert second.headers["retry-after"]
    assert second.json()["error"]["code"] == "rate_limited"
