from __future__ import annotations

import platform
import shutil
import subprocess
from importlib import import_module
from typing import Protocol, cast

from cut_clms_endpoint_agent.inventory.models import (
    CollectorResult,
    InstalledSoftware,
    InventoryWarning,
)


class _RegistryKey(Protocol):
    def __enter__(self) -> _RegistryKey: ...

    def __exit__(self, *args: object) -> None: ...


class _WindowsRegistry(Protocol):
    HKEY_LOCAL_MACHINE: object
    KEY_READ: int
    KEY_WOW64_64KEY: int

    def OpenKey(
        self, key: object, sub_key: str, reserved: int = 0, access: int = 0
    ) -> _RegistryKey: ...

    def QueryInfoKey(self, key: _RegistryKey) -> tuple[int, int, int]: ...

    def EnumKey(self, key: _RegistryKey, index: int) -> str: ...

    def QueryValueEx(self, key: _RegistryKey, name: str) -> tuple[object, int]: ...


def _parse_package_output(output: str) -> list[InstalledSoftware]:
    software = []
    for line in output.splitlines():
        name, separator, version = line.partition("\t")
        if separator and name.strip() and version.strip():
            software.append(InstalledSoftware(name=name.strip(), version=version.strip()))
    return software


def _collect_linux_software() -> CollectorResult[list[InstalledSoftware]]:
    for executable, arguments in (
        ("dpkg-query", ["-W", "-f=${Package}\\t${Version}\\n"]),
        ("rpm", ["-qa", "--qf", "%{NAME}\\t%{VERSION}-%{RELEASE}\\n"]),
    ):
        command = shutil.which(executable)
        if command is None:
            continue
        try:
            result = subprocess.run(
                [command, *arguments],
                capture_output=True,
                check=False,
                text=True,
                timeout=20,
            )
        except (OSError, subprocess.TimeoutExpired):
            return CollectorResult(
                data=[],
                warnings=[
                    InventoryWarning(
                        collector="software",
                        code="package_query_failed",
                        message=f"The {executable} package inventory query failed.",
                    )
                ],
            )
        if result.returncode != 0:
            return CollectorResult(
                data=[],
                warnings=[
                    InventoryWarning(
                        collector="software",
                        code="package_query_failed",
                        message=f"The {executable} package inventory query returned an error.",
                    )
                ],
            )
        return CollectorResult(data=_parse_package_output(result.stdout))

    return CollectorResult(
        data=[],
        warnings=[
            InventoryWarning(
                collector="software",
                code="package_manager_unsupported",
                message="No supported Linux package manager query tool was found.",
            )
        ],
    )


def _registry_software() -> CollectorResult[list[InstalledSoftware]]:
    try:
        winreg = cast(_WindowsRegistry, import_module("winreg"))
    except ImportError:
        return CollectorResult(
            data=[],
            warnings=[
                InventoryWarning(
                    collector="software",
                    code="windows_registry_unavailable",
                    message="Windows installed-software registry is unavailable.",
                )
            ],
        )

    paths = (
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
    )
    software: dict[tuple[str, str | None], InstalledSoftware] = {}
    warnings: list[InventoryWarning] = []
    for path in paths:
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path) as root:
                subkey_count = winreg.QueryInfoKey(root)[0]
                for index in range(subkey_count):
                    try:
                        subkey_name = winreg.EnumKey(root, index)
                        with winreg.OpenKey(root, subkey_name) as entry:
                            name = _query_registry_string(winreg, entry, "DisplayName")
                            version = _query_registry_string(winreg, entry, "DisplayVersion")
                            publisher = _query_registry_string(winreg, entry, "Publisher")
                            if name:
                                software[(name, version)] = InstalledSoftware(
                                    name=name,
                                    version=version,
                                    publisher=publisher,
                                )
                    except OSError:
                        warnings.append(
                            InventoryWarning(
                                collector="software",
                                code="windows_software_entry_unavailable",
                                message="An installed-software registry entry could not be read.",
                            )
                        )
                        continue
        except OSError:
            warnings.append(
                InventoryWarning(
                    collector="software",
                    code="windows_registry_read_failed",
                    message="An installed-software registry key could not be read.",
                )
            )
    return CollectorResult(
        data=sorted(
            software.values(),
            key=lambda item: (item.name.casefold(), item.version or ""),
        ),
        warnings=warnings,
    )


def _query_registry_string(winreg: _WindowsRegistry, key: _RegistryKey, name: str) -> str | None:
    try:
        value, _ = winreg.QueryValueEx(key, name)
    except OSError:
        return None
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def collect_software() -> CollectorResult[list[InstalledSoftware]]:
    system = platform.system()
    if system == "Linux":
        return _collect_linux_software()
    if system == "Windows":
        return _registry_software()
    return CollectorResult(
        data=[],
        warnings=[
            InventoryWarning(
                collector="software",
                code="platform_unsupported",
                message=(
                    f"Installed-software inventory is not implemented for {system or 'Unknown'}."
                ),
            )
        ],
    )
