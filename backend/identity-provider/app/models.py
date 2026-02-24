from pydantic import BaseModel


class LoginRequest(BaseModel):
    student_id: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class HealthResponse(BaseModel):
    status: str
    redis: str


class MetricsResponse(BaseModel):
    total_login_attempts: int
    failed_attempts: int
    rate_limit_blocks: int
    average_response_time_ms: float
