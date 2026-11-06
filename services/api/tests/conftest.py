from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from cut_clms_api.db import create_database_engine
from cut_clms_api.models import Base
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
def engine(settings: Settings) -> Iterator[Engine]:
    database_engine = create_database_engine(settings)
    Base.metadata.create_all(database_engine)
    yield database_engine
    Base.metadata.drop_all(database_engine)
    database_engine.dispose()


@pytest.fixture
def client(settings: Settings, engine: Engine) -> Iterator[TestClient]:
    from cut_clms_api.main import create_app

    app = create_app(settings, engine)

    with TestClient(app) as test_client:
        yield test_client
