import socket

import psutil

from cut_clms_endpoint_agent.inventory.models import (
    CollectorResult,
    InventoryWarning,
    NetworkAddress,
    NetworkInterface,
)


def _address_family(family: int) -> str:
    if family == socket.AF_INET:
        return "ipv4"
    if family == socket.AF_INET6:
        return "ipv6"
    return "other"


def collect_network() -> CollectorResult[list[NetworkInterface]]:
    try:
        interfaces = psutil.net_if_addrs()
    except (OSError, psutil.Error):
        return CollectorResult(
            data=[],
            warnings=[
                InventoryWarning(
                    collector="network",
                    code="interfaces_unavailable",
                    message="Network interfaces could not be listed.",
                )
            ],
        )

    try:
        stats = psutil.net_if_stats()
    except (OSError, psutil.Error):
        stats = {}
        warnings = [
            InventoryWarning(
                collector="network",
                code="interface_status_unavailable",
                message="Network interface status could not be read.",
            )
        ]
    else:
        warnings = []

    link_families = {
        getattr(psutil, "AF_LINK", -1),
        getattr(socket, "AF_PACKET", -1),
        getattr(socket, "AF_LINK", -1),
    }
    results = []
    for name, addresses in sorted(interfaces.items()):
        mac_address = None
        ip_addresses = []
        for address in addresses:
            if address.family in link_families:
                if address.address and not mac_address:
                    mac_address = address.address
            elif address.family in (socket.AF_INET, socket.AF_INET6):
                ip_addresses.append(
                    NetworkAddress(
                        address=address.address.split("%", maxsplit=1)[0],
                        family=_address_family(address.family),
                        netmask=address.netmask,
                    )
                )
        interface_stats = stats.get(name)
        results.append(
            NetworkInterface(
                name=name,
                mac_address=mac_address,
                addresses=ip_addresses,
                is_up=interface_stats.isup if interface_stats else None,
            )
        )

    return CollectorResult(data=results, warnings=warnings)
