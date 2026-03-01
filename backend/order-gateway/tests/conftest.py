"""
Pytest configuration for order-gateway tests.

Environment variables are set here — at collection time — before any app
module is imported, so pydantic-settings can resolve them without a real
.env file or live infrastructure.
"""
import os

# Required by app/config.py — must be set before the first import of any app module.
# Key is >= 32 bytes to satisfy HS256 minimum key-length recommendations.
os.environ.setdefault("JWT_SECRET", "test-secret-for-pytest-at-least-32-bytes!")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("REDIS_HOST", "localhost")
os.environ.setdefault("REDIS_PORT", "6379")
os.environ.setdefault("STOCK_SERVICE_URL", "http://stock-service:8001")
os.environ.setdefault("KITCHEN_QUEUE_URL", "http://kitchen-service:8002")
os.environ.setdefault("GATEWAY_TIMEOUT_MS", "2000")
