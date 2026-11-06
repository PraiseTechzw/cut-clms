import platform
import re
from pathlib import Path

import psutil

from cut_clms_endpoint_agent.inventory.models import (
    CollectorResult,
    CpuInfo,
    HardwareInfo,
    InventoryWarning,
    StorageDevice,
)


def _cpu_model() -> str | None:
    model = platform.processor().strip()
    if model:
        return model
    if platform.system() != "Linux":
        return None

    try:
        cpu_info = Path("/proc/cpuinfo").read_text(encoding="utf-8")
    except (OSError, psutil.Error):
        return None
    match = re.search(r"^(?:model name|Hardware)\s*:\s*(.+)$", cpu_info, re.MULTILINE)
    return match.group(1).strip() if match else None


def _read_dmi_value(name: str) -> str | None:
    try:
        value = Path("/sys/class/dmi/id", name).read_text(encoding="utf-8").strip()
    except (OSError, psutil.Error):
        return None
    return value or None


def collect_hardware() -> CollectorResult[HardwareInfo]:
    warnings: list[InventoryWarning] = []
    try:
        total_memory = psutil.virtual_memory().total
    except (OSError, psutil.Error):
        total_memory = None
        warnings.append(
            InventoryWarning(
                collector="hardware",
                code="memory_unavailable",
                message="Total memory could not be read.",
            )
        )

    storage: list[StorageDevice] = []
    try:
        partitions = psutil.disk_partitions(all=False)
    except OSError:
        partitions = []
        warnings.append(
            InventoryWarning(
                collector="hardware",
                code="storage_unavailable",
                message="Mounted storage devices could not be listed.",
            )
        )

    seen_mountpoints: set[str] = set()
    for partition in partitions:
        if partition.mountpoint in seen_mountpoints:
            continue
        seen_mountpoints.add(partition.mountpoint)
        try:
            usage = psutil.disk_usage(partition.mountpoint)
        except OSError:
            warnings.append(
                InventoryWarning(
                    collector="hardware",
                    code="storage_mount_unavailable",
                    message=f"Storage capacity could not be read for {partition.mountpoint}.",
                )
            )
            continue
        storage.append(
            StorageDevice(
                device=partition.device,
                mountpoint=partition.mountpoint,
                filesystem=partition.fstype,
                total_bytes=usage.total,
                used_bytes=usage.used,
                free_bytes=usage.free,
            )
        )

    is_linux = platform.system() == "Linux"
    return CollectorResult(
        data=HardwareInfo(
            cpu=CpuInfo(
                model=_cpu_model() or None,
                physical_cores=psutil.cpu_count(logical=False),
                logical_cores=psutil.cpu_count(logical=True),
            ),
            total_memory_bytes=total_memory,
            storage=storage,
            manufacturer=_read_dmi_value("sys_vendor") if is_linux else None,
            model=_read_dmi_value("product_name") if is_linux else None,
            serial_number=_read_dmi_value("product_serial") if is_linux else None,
        ),
        warnings=warnings,
    )
