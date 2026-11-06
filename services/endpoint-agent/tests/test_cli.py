import json

from cut_clms_endpoint_agent import cli
from cut_clms_endpoint_agent.inventory.models import (
    CpuInfo,
    DeviceIdentity,
    DeviceInventory,
    HardwareInfo,
    OperatingSystemInfo,
    SystemHealth,
)


def test_inventory_command_outputs_json(monkeypatch, capsys) -> None:
    inventory = DeviceInventory(
        collected_at="2026-01-01T00:00:00Z",
        identity=DeviceIdentity(device_id="device", hostname="lab"),
        operating_system=OperatingSystemInfo(
            name="Linux", release="6", version="build", architecture="x86_64"
        ),
        hardware=HardwareInfo(
            cpu=CpuInfo(model=None, physical_cores=None, logical_cores=None),
            total_memory_bytes=None,
            storage=[],
            manufacturer=None,
            model=None,
            serial_number=None,
        ),
        installed_software=[],
        network_interfaces=[],
        health=SystemHealth(
            cpu_utilization_percent=None,
            memory_utilization_percent=None,
            disks=[],
            uptime_seconds=None,
            agent_status="healthy",
            last_successful_communication_at=None,
        ),
    )
    monkeypatch.setattr(cli, "collect_inventory", lambda: inventory)
    monkeypatch.setattr("sys.argv", ["cut-cea", "inventory"])

    assert cli.main() == 0
    assert json.loads(capsys.readouterr().out)["identity"]["hostname"] == "lab"
