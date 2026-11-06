import platform

from cut_clms_endpoint_agent.inventory.models import (
    CollectorResult,
    OperatingSystemInfo,
)


def collect_operating_system() -> CollectorResult[OperatingSystemInfo]:
    return CollectorResult(
        data=OperatingSystemInfo(
            name=platform.system() or "Unknown",
            release=platform.release() or "Unknown",
            version=platform.version() or "Unknown",
            architecture=platform.machine() or "Unknown",
        )
    )
