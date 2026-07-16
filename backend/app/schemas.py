"""Pydantic response models -- these drive the auto-generated /docs schema
and are the single source of truth for the API contract (see API_CONTRACT.md,
which documents exactly this shape)."""
from typing import List, Optional

from pydantic import BaseModel, Field


class AlertOut(BaseModel):
    id: str
    timestamp: str = Field(description="ISO 8601 UTC timestamp")
    timestamp_unix: float
    service: str
    severity: str = Field(description="critical | warning | info")
    severity_rank: int
    message: str
    source: str = Field(description="synthetic | dataset")


class RawAlertsResponse(BaseModel):
    alerts: List[AlertOut]
    count: int


class ClusterOut(BaseModel):
    cluster_id: str
    root_cause: AlertOut
    suppressed: List[AlertOut]
    size: int
    time_span_seconds: float
    explanation: str


class WeightsOut(BaseModel):
    alpha: float
    beta: float
    gamma: float


class MetricsOut(BaseModel):
    raw_count: int
    cluster_count: int
    noise_count: int
    suppressed_count: int
    reduction_pct: float
    embedding_backend: str
    weights_used: Optional[WeightsOut] = None


class CorrelatedResponse(BaseModel):
    clusters: List[ClusterOut]
    noise: List[AlertOut]
    metrics: MetricsOut
