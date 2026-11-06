import time

import psutil

from cut_clms_endpoint_agent.inventory.models import (
    CollectorResult,
    DiskHealth,
    InventoryWarning,
    SystemHealth,
)


def collect_health() -> CollectorResult[SystemHealth]:
    warnings: list[InventoryWarning] = []
    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
    except (OSError, psutil.Error):
        cpu_percent = None
        warnings.append(
            InventoryWarning(
                collector="health",
                code="cpu_utilization_unavailable",
                message="CPU utilization could not be measured.",
            )
        )
    try:
        memory_percent = psutil.virtual_memory().percent
    except (OSError, psutil.Error):
        memory_percent = None
        warnings.append(
            InventoryWarning(
                collector="health",
                code="memory_utilization_unavailable",
                message="Memory utilization could not be measured.",
            )
        )
    try:
        boot_time = psutil.boot_time()
        uptime = max(0.0, time.time() - boot_time)
    except (OSError, psutil.Error):
        uptime = None
        warnings.append(
            InventoryWarning(
                collector="health",
                code="uptime_unavailable",
                message="System uptime could not be measured.",
            )
        )

    disks: list[DiskHealth] = []
    try:
        partitions = psutil.disk_partitions(all=False)
    except (OSError, psutil.Error):
        partitions = []
        warnings.append(
            InventoryWarning(
                collector="health",
                code="disk_health_unavailable",
                message="Disk utilization could not be collected.",
            )
        )
    seen_mountpoints: set[str] = set()
    for partition in partitions:
        if partition.mountpoint in seen_mountpoints:
            continue
        seen_mountpoints.add(partition.mountpoint)
        try:
            usage = psutil.disk_usage(partition.mountpoint)
        except (OSError, psutil.Error):
            warnings.append(
                InventoryWarning(
                    collector="health",
                    code="disk_health_mount_unavailable",
                    message=f"Disk health could not be read for {partition.mountpoint}.",
                )
            )
            continue
        disks.append(
            DiskHealth(
                mountpoint=partition.mountpoint,
                utilization_percent=usage.percent,
                available_bytes=usage.free,
            )
        )

    return CollectorResult(
        data=SystemHealth(
            cpu_utilization_percent=cpu_percent,
            memory_utilization_percent=memory_percent,
            disks=disks,
            uptime_seconds=uptime,
            agent_status="healthy",
            last_successful_communication_at=None,
        ),
        warnings=warnings,
    )
