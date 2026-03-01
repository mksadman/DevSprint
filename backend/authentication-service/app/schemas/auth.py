from __future__ import annotations

from typing import Literal, Annotated
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    student_id: Annotated[str, Field(min_length=1)]
    password: Annotated[str, Field(min_length=1)]


class LoginResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"


class AuthErrorResponse(BaseModel):
    detail: str


class HealthResponse(BaseModel):
    status: str
    redis: str


class MetricsResponse(BaseModel):
    total_login_attempts: Annotated[int, Field(ge=0)]
    failed_attempts: Annotated[int, Field(ge=0)]
    rate_limit_blocks: Annotated[int, Field(ge=0)]
    average_response_time_ms: Annotated[float, Field(ge=0)]
