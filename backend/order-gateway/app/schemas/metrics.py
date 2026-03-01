from typing import Annotated
from pydantic import BaseModel, Field


class MetricsResponse(BaseModel):
    total_orders: Annotated[int, Field(ge=0)]
    successful_orders: Annotated[int, Field(ge=0)]
    rejected_orders: Annotated[int, Field(ge=0)]
    auth_failures: Annotated[int, Field(ge=0)]
    cache_short_circuits: Annotated[int, Field(ge=0)]
    downstream_failures: Annotated[int, Field(ge=0)]
    average_response_time_ms: Annotated[float, Field(ge=0)]
