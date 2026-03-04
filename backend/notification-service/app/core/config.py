import os


DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "postgresql://cafeteria:cafeteria_pass@postgres:5432/cafeteria_db",
)

RABBITMQ_URL: str = os.getenv(
    "RABBITMQ_URL",
    "amqp://guest:guest@rabbitmq:5672/",
)

REDIS_URL: str = os.getenv(
    "REDIS_URL",
    "redis://redis:6379/0",
)

JWT_SECRET: str = os.getenv(
    "JWT_SECRET",
    "super-secret-hackathon-key",
)

JWT_ALGORITHM: str = os.getenv(
    "JWT_ALGORITHM",
    "HS256",
)
