from __future__ import annotations

from functools import lru_cache

from pydantic import SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CUT_API_", extra="ignore")

    database_url: str = "postgresql+psycopg://cut_clms:@localhost:5432/cut_clms"
    environment: str = "local"
    host: str = "127.0.0.1"
    port: int = 8000
    auth_public_key: SecretStr | None = None
    auth_issuer: str | None = None
    auth_audience: str | None = None
    rate_limit_requests: int = 60
    rate_limit_window_seconds: int = 60

    @field_validator("environment")
    @classmethod
    def supported_environment(cls, value: str) -> str:
        if value not in {"local", "test", "staging", "prod"}:
            raise ValueError("environment must be local, test, staging, or prod")
        return value

    @field_validator("rate_limit_requests", "rate_limit_window_seconds")
    @classmethod
    def positive_rate_limit_setting(cls, value: int) -> int:
        if value < 1:
            raise ValueError("rate-limit settings must be positive")
        return value

    @model_validator(mode="after")
    def validate_auth_key(self) -> Settings:
        if self.environment == "prod" and (
            not self.auth_public_key or not self.auth_issuer or not self.auth_audience
        ):
            raise ValueError(
                "CUT_API_AUTH_PUBLIC_KEY, CUT_API_AUTH_ISSUER and "
                "CUT_API_AUTH_AUDIENCE are required in prod"
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
