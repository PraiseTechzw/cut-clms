from types import SimpleNamespace

from cut_clms_endpoint_agent.inventory.collectors import hardware


def test_collects_hardware_and_storage(monkeypatch) -> None:
    monkeypatch.setattr(hardware.platform, "processor", lambda: "Example CPU")
    monkeypatch.setattr(hardware.platform, "system", lambda: "Linux")
    monkeypatch.setattr(hardware, "_read_dmi_value", lambda name: f"test-{name}")
    monkeypatch.setattr(hardware.psutil, "virtual_memory", lambda: SimpleNamespace(total=8192))
    monkeypatch.setattr(hardware.psutil, "cpu_count", lambda logical: 8 if logical else 4)
    monkeypatch.setattr(
        hardware.psutil,
        "disk_partitions",
        lambda all=False: [
            SimpleNamespace(device="/dev/sda1", mountpoint="/", fstype="ext4"),
            SimpleNamespace(device="/dev/sda1", mountpoint="/", fstype="ext4"),
        ],
    )
    monkeypatch.setattr(
        hardware.psutil,
        "disk_usage",
        lambda _path: SimpleNamespace(total=100, used=40, free=60, percent=40),
    )

    result = hardware.collect_hardware()

    assert result.data.cpu.model == "Example CPU"
    assert result.data.cpu.physical_cores == 4
    assert result.data.cpu.logical_cores == 8
    assert result.data.total_memory_bytes == 8192
    assert len(result.data.storage) == 1
    assert result.data.storage[0].free_bytes == 60
    assert result.data.serial_number == "test-product_serial"


def test_inaccessible_storage_is_reported(monkeypatch) -> None:
    monkeypatch.setattr(hardware.platform, "processor", lambda: "")
    monkeypatch.setattr(hardware.platform, "system", lambda: "Windows")
    monkeypatch.setattr(hardware.psutil, "virtual_memory", lambda: SimpleNamespace(total=0))
    monkeypatch.setattr(hardware.psutil, "cpu_count", lambda logical: None)
    monkeypatch.setattr(
        hardware.psutil,
        "disk_partitions",
        lambda all=False: [SimpleNamespace(device="D:", mountpoint="D:\\", fstype="NTFS")],
    )
    monkeypatch.setattr(
        hardware.psutil,
        "disk_usage",
        lambda _path: (_ for _ in ()).throw(PermissionError),
    )

    result = hardware.collect_hardware()

    assert result.data.storage == []
    assert result.warnings[0].code == "storage_mount_unavailable"
