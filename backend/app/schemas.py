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
    ai_scoring_enabled: bool = Field(default=False, description="whether the optional AI-similarity blend contributed to correlation scoring on this run")


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


class PreprocessWeightsOut(BaseModel):
    alpha: float
    beta: float
    gamma: float


class CompositeDistanceStatsOut(BaseModel):
    min: float
    max: float
    mean: float


class PreprocessSummaryOut(BaseModel):
    preprocessing_id: str
    alert_count: int
    embedding_backend: str = Field(description="sentence-transformers/all-MiniLM-L6-v2, or tfidf-fallback")
    embedding_dimensions: int
    weights: PreprocessWeightsOut
    composite_distance_stats: CompositeDistanceStatsOut


class PreprocessMatricesOut(BaseModel):
    preprocessing_id: str
    alert_count: int
    embeddings: List[List[float]]
    semantic_distance: List[List[float]]
    temporal_distance: List[List[float]]
    host_distance: List[List[float]]
    composite_distance: List[List[float]]
    weights: PreprocessWeightsOut


class PreprocessAlertOut(BaseModel):
    alert_id: str
    timestamp: int = Field(description="ms epoch, as stored in the demo slice CSV")
    host: str
    metric: str
    value: float
    severity: str
    message: str
    source: str


class SimilarAlertEntryOut(BaseModel):
    alert: PreprocessAlertOut
    semantic_similarity: float = Field(description="1 - semantic_distance")
    temporal_score: float = Field(description="1 - temporal_distance")
    host_score: float = Field(description="1 - host_distance")
    composite_score: float = Field(description="1 - composite_distance; what a future clustering step would consume")


class SimilarAlertsResponse(BaseModel):
    alert: PreprocessAlertOut
    most_similar: List[SimilarAlertEntryOut]
