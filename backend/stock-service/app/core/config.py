import os


DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "postgresql://cafeteria:cafeteria_pass@postgres:5432/cafeteria_db",
)

JWT_SECRET: str = os.getenv("JWT_SECRET", "super-secret-hackathon-key")
JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
