from datetime import UTC, datetime

from cut_clms_endpoint_agent.inventory.collectors.hardware import collect_hardware
from cut_clms_endpoint_agent.inventory.collectors.health import collect_health
from cut_clms_endpoint_agent.inventory.collectors.identity import collect_identity
from cut_clms_endpoint_agent.inventory.collectors.network import collect_network
from cut_clms_endpoint_agent.inventory.collectors.operating_system import collect_operating_system
from cut_clms_endpoint_agent.inventory.collectors.software import collect_software
from cut_clms_endpoint_agent.inventory.models import DeviceInventory


def collect_inventory() -> DeviceInventory:
    identity = collect_identity()
    operating_system = collect_operating_system()
    hardware = collect_hardware()
    software = collect_software()
    network = collect_network()
    health = collect_health()

    return DeviceInventory(
        collected_at=datetime.now(UTC),
        identity=identity.data,
        operating_system=operating_system.data,
        hardware=hardware.data,
        installed_software=software.data,
        network_interfaces=network.data,
        health=health.data,
        warnings=[
            *identity.warnings,
            *operating_system.warnings,
            *hardware.warnings,
            *software.warnings,
            *network.warnings,
            *health.warnings,
        ],
    )
