from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class InventoryWarning(BaseModel):
    collector: str
    code: str
    message: str


class CollectorResult[T](BaseModel):
    data: T
    warnings: list[InventoryWarning] = Field(default_factory=list)


class DeviceIdentity(BaseModel):
    device_id: str | None
    hostname: str


class OperatingSystemInfo(BaseModel):
    name: str
    release: str
    version: str
    architecture: str


class CpuInfo(BaseModel):
    model: str | None
    physical_cores: int | None
    logical_cores: int | None


class StorageDevice(BaseModel):
    device: str
    mountpoint: str
    filesystem: str
    total_bytes: int
    used_bytes: int
    free_bytes: int


class HardwareInfo(BaseModel):
    cpu: CpuInfo
    total_memory_bytes: int | None
    storage: list[StorageDevice]
    manufacturer: str | None
    model: str | None
    serial_number: str | None


class InstalledSoftware(BaseModel):
    name: str
    version: str | None
    publisher: str | None = None


class NetworkAddress(BaseModel):
    address: str
    family: str
    netmask: str | None = None


class NetworkInterface(BaseModel):
    name: str
    mac_address: str | None
    addresses: list[NetworkAddress]
    is_up: bool | None


class DiskHealth(BaseModel):
    mountpoint: str
    utilization_percent: float
    available_bytes: int


class SystemHealth(BaseModel):
    cpu_utilization_percent: float | None
    memory_utilization_percent: float | None
    disks: list[DiskHealth]
    uptime_seconds: float | None
    agent_status: str
    last_successful_communication_at: datetime | None


class DeviceInventory(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: int = 1
    collected_at: datetime
    identity: DeviceIdentity
    operating_system: OperatingSystemInfo
    hardware: HardwareInfo
    installed_software: list[InstalledSoftware]
    network_interfaces: list[NetworkInterface]
    health: SystemHealth
    warnings: list[InventoryWarning] = Field(default_factory=list)
