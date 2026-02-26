from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # JWT
    JWT_SECRET: str = "supersecretkey-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_MINUTES: int = 60

    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    # Rate limiting
    RATE_LIMIT_MAX_ATTEMPTS: int = 3
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
