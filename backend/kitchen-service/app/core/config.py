import os


DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "postgresql://cafeteria:cafeteria_pass@postgres:5432/cafeteria_db",
)

RABBITMQ_URL: str = os.getenv(
    "RABBITMQ_URL",
    "amqp://guest:guest@rabbitmq:5672/",
)
