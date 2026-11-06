from collections.abc import Generator
from typing import cast

from fastapi import Request
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from cut_clms_api.settings import Settings, get_settings


def get_app_settings(request: Request) -> Settings:
    return cast(Settings, request.app.state.settings)


def create_database_engine(settings: Settings | None = None) -> Engine:
    active_settings = settings or get_settings()
    options: dict[str, object] = {"pool_pre_ping": True}
    if active_settings.database_url.startswith("sqlite"):
        options["connect_args"] = {"check_same_thread": False}
    return create_engine(active_settings.database_url, **options)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db_session(request: Request) -> Generator[Session, None, None]:
    factory: sessionmaker[Session] = request.app.state.session_factory
    with factory() as session:
        yield session


def check_database(engine: Engine) -> None:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
