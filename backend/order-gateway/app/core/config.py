from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", env_ignore_empty=True)

    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_PASSWORD: str = ""
    STOCK_SERVICE_URL: str
    RABBITMQ_URL: str = "amqp://guest:guest@rabbitmq:5672/"
    INTERNAL_API_KEY: str = "internal-service-key-2026"
    GATEWAY_TIMEOUT_MS: int
    TESTING: bool = False

    # Comma-separated list of allowed CORS origins.
    # Example: "http://localhost:3000,https://myapp.example.com"
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _parse_cors_origins(cls, v: object) -> List[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v  # already a list (e.g. from a .env file with JSON syntax)

    @field_validator("REDIS_PORT")
    @classmethod
    def port_valid(cls, v: int) -> int:
        if not (1 <= v <= 65535):
            raise ValueError("REDIS_PORT must be between 1 and 65535")
        return v

    @field_validator("GATEWAY_TIMEOUT_MS")
    @classmethod
    def timeout_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("GATEWAY_TIMEOUT_MS must be a positive integer")
        return v


settings = Settings()
