import subprocess
import sys
from types import ModuleType

from cut_clms_endpoint_agent.inventory.collectors import software


def test_linux_dpkg_inventory_is_parsed(monkeypatch) -> None:
    monkeypatch.setattr(software.platform, "system", lambda: "Linux")
    monkeypatch.setattr(
        software.shutil,
        "which",
        lambda name: "/usr/bin/dpkg-query" if name == "dpkg-query" else None,
    )
    monkeypatch.setattr(
        software.subprocess,
        "run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess(
            args=["dpkg-query"], returncode=0, stdout="sample\t1.2\n", stderr=""
        ),
    )

    result = software.collect_software()

    assert [(item.name, item.version) for item in result.data] == [("sample", "1.2")]
    assert result.warnings == []


def test_linux_package_query_failure_is_reported(monkeypatch) -> None:
    monkeypatch.setattr(software.platform, "system", lambda: "Linux")
    monkeypatch.setattr(software.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(
        software.subprocess,
        "run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess(
            args=["dpkg-query"], returncode=1, stdout="", stderr="failure"
        ),
    )

    result = software.collect_software()

    assert result.data == []
    assert result.warnings[0].code == "package_query_failed"


def test_unsupported_platform_returns_warning(monkeypatch) -> None:
    monkeypatch.setattr(software.platform, "system", lambda: "Darwin")

    result = software.collect_software()

    assert result.data == []
    assert result.warnings[0].code == "platform_unsupported"


def test_windows_registry_inventory_is_collected(monkeypatch) -> None:
    registry = ModuleType("winreg")
    registry.HKEY_LOCAL_MACHINE = object()

    class Key:
        def __init__(self, values=None):
            self.values = values or {}

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

    def open_key(_root, path):
        if path != "example-app":
            return Key()
        return Key({"DisplayName": "Example App", "Publisher": "CUT"})

    def query_value(key, name):
        if name not in key.values:
            raise OSError("value not found")
        return key.values[name], 1

    registry.OpenKey = open_key
    registry.QueryInfoKey = lambda _key: (1 if _key.values == {} else 0, 0, 0)
    registry.EnumKey = lambda *_args: "example-app"
    registry.QueryValueEx = query_value
    monkeypatch.setitem(sys.modules, "winreg", registry)
    monkeypatch.setattr(software.platform, "system", lambda: "Windows")

    result = software.collect_software()

    assert result.data == [
        software.InstalledSoftware(name="Example App", version=None, publisher="CUT")
    ]
