from cut_clms_api.settings import Settings, get_settings


def test_settings_read_cut_api_prefixed_env_vars() -> None:
    settings = Settings(
        database_url="postgresql+psycopg://user:secret@db:5432/cut_clms",
        environment="test",
    )

    assert settings.database_url == "postgresql+psycopg://user:secret@db:5432/cut_clms"
    assert settings.environment == "test"


def test_production_requires_external_auth_verification_configuration() -> None:
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        Settings(environment="prod")


def test_settings_have_safe_local_defaults() -> None:
    settings = Settings()

    assert settings.environment == "local"
    assert settings.database_url.startswith("postgresql+psycopg://cut_clms:")
    assert settings.port == 8000


def test_settings_are_cached_until_cleared(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    first = get_settings()
    monkeypatch.setenv("CUT_API_PORT", "9999")
    second = get_settings()

    assert second is first

    get_settings.cache_clear()
    third = get_settings()

    assert third.port == 9999
