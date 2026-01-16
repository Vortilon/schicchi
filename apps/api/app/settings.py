from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    webhook_secret: str

    alpaca_key: str | None = None
    alpaca_secret: str | None = None
    alpaca_base_url: str = "https://paper-api.alpaca.markets"
    alpaca_data_url: str = "https://data.alpaca.markets"

    cors_origins: str = "http://localhost:3000"
    log_level: str = "info"

    @field_validator("alpaca_base_url", "alpaca_data_url")
    @classmethod
    def _normalize_alpaca_urls(cls, v: str) -> str:
        # Users sometimes paste the full REST base including "/v2".
        # Alpaca SDKs typically expect the host base and will append versioned paths themselves.
        v = v.rstrip("/")
        if v.endswith("/v2"):
            v = v[: -len("/v2")]
        return v


settings = Settings()

