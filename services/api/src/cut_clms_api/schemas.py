from __future__ import annotations

import re
from datetime import datetime
from ipaddress import ip_address
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class APIModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class APIErrorDetail(APIModel):
    location: list[str | int]
    message: str
    type: str


class APIError(APIModel):
    code: str
    message: str
    details: list[APIErrorDetail] | None


class APIErrorResponse(APIModel):
    error: APIError
    request_id: str


class DeviceIdentityPayload(APIModel):
    device_id: str | None = Field(pattern=r"^[a-f0-9]{64}$")
    hostname: str = Field(min_length=1, max_length=255)


class OperatingSystemPayload(APIModel):
    name: str = Field(min_length=1, max_length=100)
    release: str = Field(min_length=1, max_length=200)
    version: str = Field(min_length=1, max_length=500)
    architecture: str = Field(min_length=1, max_length=100)


class CpuPayload(APIModel):
    model: str | None = Field(default=None, max_length=500)
    physical_cores: int | None = Field(default=None, ge=1, le=4096)
    logical_cores: int | None = Field(default=None, ge=1, le=8192)


class StoragePayload(APIModel):
    device: str = Field(max_length=500)
    mountpoint: str = Field(max_length=1000)
    filesystem: str = Field(max_length=100)
    total_bytes: int = Field(ge=0)
    used_bytes: int = Field(ge=0)
    free_bytes: int = Field(ge=0)


class HardwarePayload(APIModel):
    cpu: CpuPayload
    total_memory_bytes: int | None = Field(default=None, ge=0)
    storage: list[StoragePayload] = Field(max_length=256)
    manufacturer: str | None = Field(default=None, max_length=300)
    model: str | None = Field(default=None, max_length=300)
    serial_number: str | None = Field(default=None, max_length=300)


class InstalledSoftwarePayload(APIModel):
    name: str = Field(min_length=1, max_length=500)
    version: str | None = Field(default=None, max_length=200)
    publisher: str | None = Field(default=None, max_length=300)


class NetworkAddressPayload(APIModel):
    address: str = Field(min_length=1, max_length=128)
    family: Literal["ipv4", "ipv6", "other"]
    netmask: str | None = Field(default=None, max_length=128)

    @field_validator("address", "netmask")
    @classmethod
    def validate_ip_address(cls, value: str | None) -> str | None:
        if value is not None:
            ip_address(value.split("%", maxsplit=1)[0])
        return value


class NetworkInterfacePayload(APIModel):
    name: str = Field(min_length=1, max_length=255)
    mac_address: str | None = Field(default=None, max_length=64)
    addresses: list[NetworkAddressPayload] = Field(max_length=128)
    is_up: bool | None = None

    @field_validator("mac_address")
    @classmethod
    def validate_mac_address(cls, value: str | None) -> str | None:
        if value is not None and not re.fullmatch(r"[0-9A-Fa-f:.-]{1,64}", value):
            raise ValueError("invalid MAC address")
        return value


class DiskHealthPayload(APIModel):
    mountpoint: str = Field(max_length=1000)
    utilization_percent: float = Field(ge=0, le=100)
    available_bytes: int = Field(ge=0)


class HealthPayload(APIModel):
    cpu_utilization_percent: float | None = Field(default=None, ge=0, le=100)
    memory_utilization_percent: float | None = Field(default=None, ge=0, le=100)
    disks: list[DiskHealthPayload] = Field(max_length=256)
    uptime_seconds: float | None = Field(default=None, ge=0)
    agent_status: Literal["healthy", "degraded", "unhealthy"]
    last_successful_communication_at: datetime | None = None


class InventoryWarningPayload(APIModel):
    collector: str = Field(min_length=1, max_length=100)
    code: str = Field(min_length=1, max_length=100)
    message: str = Field(min_length=1, max_length=1000)


class InventoryPayload(APIModel):
    schema_version: Literal[1]
    collected_at: datetime
    identity: DeviceIdentityPayload
    operating_system: OperatingSystemPayload
    hardware: HardwarePayload
    installed_software: list[InstalledSoftwarePayload] = Field(max_length=20_000)
    network_interfaces: list[NetworkInterfacePayload] = Field(max_length=256)
    health: HealthPayload
    warnings: list[InventoryWarningPayload] = Field(
        default_factory=list, max_length=1000
    )

    @field_validator("collected_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("collected_at must include a timezone")
        return value

    @model_validator(mode="after")
    def validate_storage_capacity(self) -> InventoryPayload:
        for storage in self.hardware.storage:
            if storage.used_bytes + storage.free_bytes > storage.total_bytes:
                raise ValueError("storage used and free capacity cannot exceed total")
        return self


class EnrollmentRequest(APIModel):
    agent_version: str = Field(min_length=1, max_length=64)
    inventory: InventoryPayload


class EnrollmentResponse(APIModel):
    endpoint_id: UUID
    device_credential: str
    credential_type: Literal["Bearer"] = "Bearer"


class HeartbeatRequest(APIModel):
    agent_version: str = Field(min_length=1, max_length=64)
    reported_at: datetime
    health: HealthPayload

    @field_validator("reported_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("reported_at must include a timezone")
        return value


class AcceptedResponse(APIModel):
    status: Literal["accepted"] = "accepted"
    received_at: datetime
