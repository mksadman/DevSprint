from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXP_MINUTES: int = 60

    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379

    RATE_LIMIT_MAX_ATTEMPTS: int = 3
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
