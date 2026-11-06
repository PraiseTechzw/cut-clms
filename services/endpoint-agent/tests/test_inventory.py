from datetime import UTC

from cut_clms_endpoint_agent import inventory as inventory_module
from cut_clms_endpoint_agent.inventory.models import (
    CollectorResult,
    CpuInfo,
    DeviceIdentity,
    HardwareInfo,
    OperatingSystemInfo,
    SystemHealth,
)


def test_collect_inventory_aggregates_all_collectors(monkeypatch) -> None:
    monkeypatch.setattr(
        inventory_module,
        "collect_identity",
        lambda: CollectorResult(data=DeviceIdentity(device_id="abc", hostname="lab")),
    )
    monkeypatch.setattr(
        inventory_module,
        "collect_operating_system",
        lambda: CollectorResult(
            data=OperatingSystemInfo(
                name="Linux", release="6", version="build", architecture="x86_64"
            )
        ),
    )
    monkeypatch.setattr(
        inventory_module,
        "collect_hardware",
        lambda: CollectorResult(
            data=HardwareInfo(
                cpu=CpuInfo(model=None, physical_cores=None, logical_cores=None),
                total_memory_bytes=None,
                storage=[],
                manufacturer=None,
                model=None,
                serial_number=None,
            )
        ),
    )
    monkeypatch.setattr(inventory_module, "collect_software", lambda: CollectorResult(data=[]))
    monkeypatch.setattr(inventory_module, "collect_network", lambda: CollectorResult(data=[]))
    monkeypatch.setattr(
        inventory_module,
        "collect_health",
        lambda: CollectorResult(
            data=SystemHealth(
                cpu_utilization_percent=None,
                memory_utilization_percent=None,
                disks=[],
                uptime_seconds=None,
                agent_status="healthy",
                last_successful_communication_at=None,
            )
        ),
    )

    inventory = inventory_module.collect_inventory()

    assert inventory.identity.device_id == "abc"
    assert inventory.schema_version == 1
    assert inventory.collected_at.tzinfo == UTC
    assert inventory.warnings == []
