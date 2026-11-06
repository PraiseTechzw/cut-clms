from __future__ import annotations

import hashlib
import platform
from importlib import import_module
from pathlib import Path
from typing import Protocol, cast

from cut_clms_endpoint_agent.inventory.models import (
    CollectorResult,
    DeviceIdentity,
    InventoryWarning,
)


class _RegistryKey(Protocol):
    def __enter__(self) -> _RegistryKey: ...

    def __exit__(self, *args: object) -> None: ...


class _MachineGuidRegistry(Protocol):
    HKEY_LOCAL_MACHINE: object
    KEY_READ: int
    KEY_WOW64_64KEY: int

    def OpenKey(
        self, key: object, sub_key: str, reserved: int = 0, access: int = 0
    ) -> _RegistryKey: ...

    def QueryValueEx(self, key: _RegistryKey, name: str) -> tuple[object, int]: ...


def _read_machine_id() -> str | None:
    if platform.system() == "Linux":
        for path in (Path("/etc/machine-id"), Path("/var/lib/dbus/machine-id")):
            try:
                machine_id = path.read_text(encoding="utf-8").strip()
            except FileNotFoundError:
                continue
            except OSError:
                continue
            if machine_id:
                return machine_id
        return None

    if platform.system() == "Windows":
        try:
            winreg = cast(_MachineGuidRegistry, import_module("winreg"))
        except ImportError:
            return None

        try:
            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Cryptography",
                0,
                winreg.KEY_READ | winreg.KEY_WOW64_64KEY,
            ) as key:
                value, _ = winreg.QueryValueEx(key, "MachineGuid")
        except OSError:
            return None
        return str(value).strip() or None

    return None


def collect_identity() -> CollectorResult[DeviceIdentity]:
    machine_id = _read_machine_id()
    warnings: list[InventoryWarning] = []
    device_id = None
    if machine_id:
        device_id = hashlib.sha256(f"cut-cea:v1:{machine_id}".encode()).hexdigest()
    else:
        warnings.append(
            InventoryWarning(
                collector="identity",
                code="stable_identifier_unavailable",
                message="No supported machine identifier was readable; device_id is null.",
            )
        )

    return CollectorResult(
        data=DeviceIdentity(device_id=device_id, hostname=platform.node()),
        warnings=warnings,
    )
