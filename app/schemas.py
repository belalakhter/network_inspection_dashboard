from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class FlowRecord(BaseModel):
    timestamp: datetime
    src_ip: str
    dst_ip: str
    src_port: int
    dst_port: int
    protocol: str
    application: str
    duration_ms: float = Field(ge=0)
    src_to_dst_bytes: int = Field(ge=0)
    dst_to_src_bytes: int = Field(ge=0)
    src_to_dst_packets: int = Field(ge=0)
    dst_to_src_packets: int = Field(ge=0)
    syn_packets: int = Field(ge=0)
    fin_packets: int = Field(ge=0)
    rst_packets: int = Field(ge=0)
    avg_packet_size: float = Field(ge=0)
    label: Optional[str] = None
    anomaly_score: Optional[float] = None
    flagged_reason: Optional[str] = None


class BufferSnapshot(BaseModel):
    window_minutes: int
    flow_count: int
    captured_at: datetime
    flows: List[FlowRecord]


class ThreatScorePoint(BaseModel):
    timestamp: datetime
    score: float = Field(ge=0, le=100)


class TrainingStatus(BaseModel):
    last_trained_at: Optional[datetime] = None
    epochs_completed: int = 0
    latest_loss: Optional[float] = None
    best_loss: Optional[float] = None
    model_version: int = 0
    buffer_flow_count: int = 0
    next_retrain_in_seconds: int = 0
    collector_mode: str = "synthetic"
    last_capture_at: Optional[datetime] = None
    last_capture_flow_count: int = 0
    bootstrap_completed: bool = False


class DashboardSummary(BaseModel):
    active_connections: int = Field(ge=0)
    inbound_bytes: int = Field(ge=0)
    outbound_bytes: int = Field(ge=0)
    top_applications: List[str]
    health_message: str
    threat_score: float = Field(ge=0, le=100)
    suspicious_connection_count: int = Field(ge=0)


class SuspiciousFlow(BaseModel):
    timestamp: datetime
    src_ip: str
    dst_ip: str
    protocol: str
    application: str
    anomaly_score: float
    confidence: float = Field(ge=0, le=1)
    reason: str


class DashboardResponse(BaseModel):
    summary: DashboardSummary
    threat_history: List[ThreatScorePoint]
    suspicious_connections: List[SuspiciousFlow]
    training_status: TrainingStatus
