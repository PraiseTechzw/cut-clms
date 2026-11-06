from types import SimpleNamespace

from cut_clms_endpoint_agent.inventory.collectors import health


def test_collects_utilization_disks_and_uptime(monkeypatch) -> None:
    monkeypatch.setattr(health.psutil, "cpu_percent", lambda interval: 25.0)
    monkeypatch.setattr(health.psutil, "virtual_memory", lambda: SimpleNamespace(percent=50))
    monkeypatch.setattr(health.time, "time", lambda: 1000.0)
    monkeypatch.setattr(health.psutil, "boot_time", lambda: 900.0)
    monkeypatch.setattr(
        health.psutil,
        "disk_partitions",
        lambda all=False: [SimpleNamespace(mountpoint="/")],
    )
    monkeypatch.setattr(
        health.psutil,
        "disk_usage",
        lambda _path: SimpleNamespace(total=100, used=40, free=60, percent=40),
    )

    result = health.collect_health()

    assert result.data.cpu_utilization_percent == 25.0
    assert result.data.memory_utilization_percent == 50.0
    assert result.data.uptime_seconds == 100.0
    assert result.data.disks[0].available_bytes == 60
    assert result.data.last_successful_communication_at is None
    assert result.warnings == []


def test_unavailable_cpu_is_reported(monkeypatch) -> None:
    monkeypatch.setattr(
        health.psutil, "cpu_percent", lambda interval: (_ for _ in ()).throw(OSError())
    )
    monkeypatch.setattr(health.psutil, "virtual_memory", lambda: SimpleNamespace(percent=1))
    monkeypatch.setattr(health.psutil, "boot_time", lambda: 0.0)
    monkeypatch.setattr(health.psutil, "disk_partitions", lambda all=False: [])
    monkeypatch.setattr(health.time, "time", lambda: 1.0)

    result = health.collect_health()

    assert result.data.cpu_utilization_percent is None
    assert result.warnings[0].code == "cpu_utilization_unavailable"
