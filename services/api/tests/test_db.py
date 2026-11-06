import cut_clms_api


def test_engine_connects_and_selects_one(settings) -> None:  # type: ignore[no-untyped-def]
    from sqlalchemy import text

    from cut_clms_api.db import create_database_engine

    engine = create_database_engine(settings)

    try:
        with engine.connect() as connection:
            assert connection.execute(text("SELECT 1")).scalar() == 1
    finally:
        engine.dispose()


def test_package_version_is_exposed() -> None:
    assert cut_clms_api.__version__
