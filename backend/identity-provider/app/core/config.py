from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    JWT_SECRET: str = "4fadb06a4a6619c03eb863c43e93b82065364e26ae2a94b73b177221bd6b23c6"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXP_MINUTES: int = 60

    DATABASE_URL: str = "postgresql://cafeteria:cafeteria_pass@postgres:5432/cafeteria_db"

    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379

    RATE_LIMIT_MAX_ATTEMPTS: int = 3
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    # Comma-separated list of allowed CORS origins.
    # Example: "http://localhost:3000,https://myapp.example.com"
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _parse_cors_origins(cls, v: object) -> List[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v  # already a list (e.g. from a .env file with JSON syntax)

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
