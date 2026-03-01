import os


DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "postgresql://cafeteria:cafeteria_pass@postgres:5432/cafeteria_db",
)

NOTIFICATION_SERVICE_URL: str = os.getenv(
    "NOTIFICATION_SERVICE_URL",
    "http://notification-service:8000",
)
