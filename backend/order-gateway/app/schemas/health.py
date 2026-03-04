from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    redis: str
    stock_service: str
