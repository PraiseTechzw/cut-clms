import socket
from types import SimpleNamespace

import psutil

from cut_clms_endpoint_agent.inventory.collectors import network


def test_collects_ip_mac_and_status(monkeypatch) -> None:
    monkeypatch.setattr(
        network.psutil,
        "net_if_addrs",
        lambda: {
            "eth0": [
                SimpleNamespace(
                    family=socket.AF_INET,
                    address="192.0.2.1",
                    netmask="255.255.255.0",
                ),
                SimpleNamespace(
                    family=network.psutil.AF_LINK,
                    address="aa:bb:cc:dd:ee:ff",
                    netmask=None,
                ),
            ]
        },
    )
    monkeypatch.setattr(
        network.psutil, "net_if_stats", lambda: {"eth0": SimpleNamespace(isup=True)}
    )

    result = network.collect_network()

    assert result.data[0].name == "eth0"
    assert result.data[0].mac_address == "aa:bb:cc:dd:ee:ff"
    assert result.data[0].addresses[0].family == "ipv4"
    assert result.data[0].is_up is True


def test_interface_enumeration_failure_is_reported(monkeypatch) -> None:
    monkeypatch.setattr(
        network.psutil,
        "net_if_addrs",
        lambda: (_ for _ in ()).throw(psutil.AccessDenied()),
    )

    result = network.collect_network()

    assert result.data == []
    assert result.warnings[0].code == "interfaces_unavailable"
