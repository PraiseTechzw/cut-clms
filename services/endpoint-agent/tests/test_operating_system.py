from cut_clms_endpoint_agent.inventory.collectors import operating_system


def test_collects_platform_information(monkeypatch) -> None:
    monkeypatch.setattr(operating_system.platform, "system", lambda: "Linux")
    monkeypatch.setattr(operating_system.platform, "release", lambda: "6.8")
    monkeypatch.setattr(operating_system.platform, "version", lambda: "kernel build")
    monkeypatch.setattr(operating_system.platform, "machine", lambda: "x86_64")

    result = operating_system.collect_operating_system()

    assert result.data.model_dump() == {
        "name": "Linux",
        "release": "6.8",
        "version": "kernel build",
        "architecture": "x86_64",
    }
