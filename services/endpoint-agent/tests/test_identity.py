import hashlib
import sys
from pathlib import Path
from types import ModuleType

from cut_clms_endpoint_agent.inventory.collectors import identity


def test_linux_machine_id_is_hashed(monkeypatch, tmp_path: Path) -> None:
    machine_id_path = tmp_path / "machine-id"
    machine_id_path.write_text("machine-secret\n", encoding="utf-8")
    monkeypatch.setattr(identity.platform, "system", lambda: "Linux")
    monkeypatch.setattr(identity.platform, "node", lambda: "lab-01")
    monkeypatch.setattr(
        identity,
        "Path",
        lambda path: machine_id_path if str(path) == "/etc/machine-id" else Path(path),
    )

    result = identity.collect_identity()

    assert result.data.hostname == "lab-01"
    assert result.data.device_id == hashlib.sha256(b"cut-cea:v1:machine-secret").hexdigest()
    assert "machine-secret" not in result.model_dump_json()


def test_windows_machine_guid_is_hashed(monkeypatch) -> None:
    registry = ModuleType("winreg")
    registry.HKEY_LOCAL_MACHINE = object()
    registry.KEY_READ = 1
    registry.KEY_WOW64_64KEY = 2

    class Key:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

    registry.OpenKey = lambda *_args: Key()
    registry.QueryValueEx = lambda *_args: ("windows-guid", 1)
    monkeypatch.setitem(sys.modules, "winreg", registry)
    monkeypatch.setattr(identity.platform, "system", lambda: "Windows")
    monkeypatch.setattr(identity.platform, "node", lambda: "lab-win")

    result = identity.collect_identity()

    assert result.data.hostname == "lab-win"
    assert result.data.device_id == hashlib.sha256(b"cut-cea:v1:windows-guid").hexdigest()
    assert "windows-guid" not in result.model_dump_json()


def test_unsupported_platform_reports_unavailable_identifier(monkeypatch) -> None:
    monkeypatch.setattr(identity.platform, "system", lambda: "FreeBSD")
    monkeypatch.setattr(identity.platform, "node", lambda: "other")

    result = identity.collect_identity()

    assert result.data.device_id is None
    assert result.warnings[0].code == "stable_identifier_unavailable"
