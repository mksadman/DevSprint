from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    REDIS_HOST: str
    REDIS_PORT: int
    STOCK_SERVICE_URL: str
    KITCHEN_QUEUE_URL: str
    GATEWAY_TIMEOUT_MS: int

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
