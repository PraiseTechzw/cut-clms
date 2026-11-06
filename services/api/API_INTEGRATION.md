# Endpoint API contract, v1

The API contract is versioned under `/api/v1`. OpenAPI is available at
`/openapi.json`; `uv run --directory services/api python -m
cut_clms_api.openapi_export --output openapi.json` writes a stable JSON schema.
The inventory request matches the local `DeviceInventory` model in
`services/endpoint-agent`.

All three endpoints are rate limited. Errors use this shape:

```json
{
  "error": {
    "code": "validation_error",
    "message": "Request validation failed",
    "details": []
  },
  "request_id": "uuid"
}
```

## Enroll

`POST /api/v1/endpoints/enroll`

Header: `X-Enrollment-Token: <one-time token>`

Request body:

```json
{
  "agent_version": "0.1.0",
  "inventory": {
    "schema_version": 1,
    "collected_at": "2026-11-06T15:00:00Z",
    "identity": {
      "device_id": "<64 lowercase hex characters>",
      "hostname": "lab-pc-01"
    },
    "operating_system": {
      "name": "Linux",
      "release": "6.8.0",
      "version": "distribution version",
      "architecture": "x86_64"
    },
    "hardware": {
      "cpu": {
        "model": "CPU model",
        "physical_cores": 4,
        "logical_cores": 8
      },
      "total_memory_bytes": 17179869184,
      "storage": [],
      "manufacturer": null,
      "model": null,
      "serial_number": null
    },
    "installed_software": [],
    "network_interfaces": [],
    "health": {
      "cpu_utilization_percent": 4.5,
      "memory_utilization_percent": 30.0,
      "disks": [],
      "uptime_seconds": 3600,
      "agent_status": "healthy",
      "last_successful_communication_at": null
    },
    "warnings": []
  }
}
```

Success: `201 Created`.

```json
{
  "endpoint_id": "uuid",
  "device_credential": "<random bearer credential; shown once>",
  "credential_type": "Bearer"
}
```

Enrollment tokens are random, institution-scoped, expire, and can be consumed
once. Provision them with the operator CLI. Enrolled `device_id` values must
be unique among active endpoints. If a successful response is lost, an
operator can revoke that endpoint with the CLI, issue a fresh token for the
same institution, and enroll again. Re-enrollment rotates the credential and
retains the endpoint's inventory history.

## Heartbeat

`POST /api/v1/endpoints/heartbeat`

Header: `Authorization: Bearer <device_credential>`

```json
{
  "agent_version": "0.1.0",
  "reported_at": "2026-11-06T15:05:00Z",
  "health": {
    "cpu_utilization_percent": 6.0,
    "memory_utilization_percent": 31.0,
    "disks": [],
    "uptime_seconds": 3900,
    "agent_status": "healthy",
    "last_successful_communication_at": null
  }
}
```

Success: `200 OK`, with `{"status": "accepted", "received_at": "...Z"}`.

## Inventory update

`POST /api/v1/endpoints/inventory`

Header: `Authorization: Bearer <device_credential>`.

Body: the complete stage-one inventory object shown in the enrollment example
(without the `agent_version` wrapper). The submitted device ID must match the
authenticated endpoint. The API stores an inventory snapshot, software rows,
and a health sample in one database transaction.

Success: `200 OK`, with `{"status": "accepted", "received_at": "...Z"}`.

## Authentication boundaries

- The bootstrap token is sent only in the enrollment header; its SHA-256 hash
  is stored in the database.
- Enrollment returns a per-device random credential. Only its SHA-256 hash is
  stored. Heartbeat/inventory requests must use HTTPS and a bearer credential.
- Device credential lookup also checks revocation state. No device-facing
  route can select a different institution or endpoint.
- Human users are separate database identities from endpoints. Human JWT
  verification accepts RS256 tokens only and requires `sub`, `iss`, `aud`, and
  `institution_id`; configure an external identity provider's public key,
  issuer, and audience. No passwords or human JWT signing keys are stored here.

## Not included in this contract

There are no command execution, update delivery, remote shell, human login,
human endpoint-list, or administrator APIs in this endpoint integration stage.
No API paths are invented beyond enrollment, heartbeat, and inventory
submission. Human collection/list APIs and their pagination/filtering remain
for a later business-platform stage.
