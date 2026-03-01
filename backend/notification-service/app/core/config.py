import os


DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "postgresql://cafeteria:cafeteria_pass@postgres:5432/cafeteria_db",
)
