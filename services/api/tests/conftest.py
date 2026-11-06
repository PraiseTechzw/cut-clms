from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from cut_clms_api.settings import Settings, get_settings


@pytest.fixture
def settings(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Settings:
    """Per-test settings backed by a throwaway SQLite database file."""
    db_file = tmp_path / "test.db"

    monkeypatch.setenv("CUT_API_DATABASE_URL", f"sqlite:///{db_file}")
    monkeypatch.setenv("CUT_API_ENVIRONMENT", "test")
    get_settings.cache_clear()

    return get_settings()


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    from cut_clms_api.main import create_app

    with TestClient(create_app()) as test_client:
        yield test_client
