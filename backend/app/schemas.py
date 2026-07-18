"""Pydantic response models -- these drive the auto-generated /docs schema
and are the single source of truth for the API contract (see API_CONTRACT.md,
which documents exactly this shape)."""
from typing import List

from pydantic import BaseModel, Field
class AiopsSummary(BaseModel):
    raw_count: int
    host_count: int
    hosts: List[str]


class EngineIncidentMemberOut(BaseModel):
    alert_id: str
    timestamp: str
    host: str
    metric: str
    severity: str
    value: float
    root_score: float
    is_root: bool


class EngineIncidentOut(BaseModel):
    incident_id: int
    host: str
    root_metric: str
    severity: str
    root_alert_id: str
    root_timestamp: str
    root_value: float
    root_score: float
    alert_count: int
    suppressed_count: int
    members: List[EngineIncidentMemberOut] = Field(default_factory=list, description="every raw alert folded into this incident, in timestamp order; empty unless include_members=true was passed")


class EngineMetricsOut(BaseModel):
    raw_count: int
    incident_count: int
    suppressed_count: int
    reduction_pct: float
    host_count: int


class EngineRunResponse(BaseModel):
    incidents: List[EngineIncidentOut]
    metrics: EngineMetricsOut


class SampleAlertOut(BaseModel):
    alert_id: str
    timestamp: str = Field(description="ISO 8601 UTC timestamp")
    host: str
    metric: str
    value: float = Field(description="the real metric reading that triggered this alert")
    severity: str = Field(description="Critical | Warning | Info")
    message: str


class AiopsSampleResponse(BaseModel):
    alerts: List[SampleAlertOut]
    count: int
