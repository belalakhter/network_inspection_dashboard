from __future__ import annotations

import threading
from collections import deque
from datetime import datetime, timedelta, timezone
from time import sleep
from typing import Deque, List

from app.services.buffer import RollingFlowBuffer
from app.static.collectors import build_flow_collector
from app.config import Settings
from app.schemas import DashboardResponse, FlowRecord, SuspiciousFlow, ThreatScorePoint
from model.dataset import FEATURE_NAMES
from model.train import ModelTrainer


class BackgroundOrchestrator:
    def __init__(self, flow_buffer: RollingFlowBuffer, settings: Settings) -> None:
        self.buffer = flow_buffer
        self.settings = settings
        self.collect_interval_seconds = settings.capture_interval_seconds
        self.retrain_interval_seconds = settings.retrain_interval_seconds
        self.collector = build_flow_collector(settings)
        self.collector_mode = self.collector.mode
        self.trainer = ModelTrainer(
            input_size=len(FEATURE_NAMES) + 2,
            min_train_samples=settings.bootstrap_flow_count,
        )
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._threat_history: Deque[ThreatScorePoint] = deque(maxlen=180)
        self._last_retrain_started_at = datetime.now(timezone.utc)
        self._last_capture_at: datetime | None = None
        self._last_capture_flow_count = 0

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, name="flow-worker", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)

    def dashboard_snapshot(self) -> DashboardResponse:
        flows = self.buffer.latest_flows(limit=50)
        scores = self.trainer.score_flows(flows)
        suspicious: List[SuspiciousFlow] = []

        for flow, score in zip(flows, scores):
            if score < 0.75:
                continue
            suspicious.append(
                SuspiciousFlow(
                    timestamp=flow.timestamp,
                    src_ip=flow.src_ip,
                    dst_ip=flow.dst_ip,
                    protocol=flow.protocol,
                    application=flow.application,
                    anomaly_score=score,
                    confidence=min(score / 3.0, 1.0),
                    reason=self._reason_for_flow(flow, score),
                )
            )

        threat_score = min(100.0, max((max(scores) if scores else 0.0) * 35.0, 0.0))
        health_message = "Everything looks normal"
        if threat_score >= 60:
            health_message = "Threat activity is elevated"
        elif threat_score >= 30:
            health_message = "Unusual activity detected"

        return DashboardResponse(
            summary={
                "active_connections": len(self.buffer),
                "inbound_bytes": self.buffer.inbound_bytes(),
                "outbound_bytes": self.buffer.outbound_bytes(),
                "top_applications": self.buffer.application_ranking(),
                "health_message": health_message,
                "threat_score": threat_score,
                "suspicious_connection_count": len(suspicious),
            },
            threat_history=list(self._threat_history),
            suspicious_connections=suspicious[:10],
            training_status=self.trainer.status(
                buffer_flow_count=len(self.buffer),
                next_retrain_in_seconds=self._seconds_until_retrain(),
                collector_mode=self.collector_mode,
                last_capture_at=self._last_capture_at,
                last_capture_flow_count=self._last_capture_flow_count,
            ),
        )

    def _run_loop(self) -> None:
        last_collection = datetime.now(timezone.utc) - timedelta(seconds=self.collect_interval_seconds)
        while not self._stop_event.is_set():
            now = datetime.now(timezone.utc)
            if (now - last_collection).total_seconds() >= self.collect_interval_seconds:
                flows = self.collector.collect_batch(captured_at=now)
                if flows:
                    self.buffer.add_flows(flows)
                self._last_capture_at = now
                self._last_capture_flow_count = len(flows)
                last_collection = now

            if (now - self._last_retrain_started_at).total_seconds() >= self.retrain_interval_seconds:
                self._retrain()

            dashboard = self.dashboard_snapshot()
            self._threat_history.append(
                ThreatScorePoint(timestamp=now, score=dashboard.summary.threat_score)
            )
            sleep(1)

    def _retrain(self) -> None:
        self._last_retrain_started_at = datetime.now(timezone.utc)
        flows = self.buffer.snapshot().flows
        self.trainer.train(flows=flows, epochs=self.settings.retrain_epochs)

    def _seconds_until_retrain(self) -> int:
        elapsed = (datetime.now(timezone.utc) - self._last_retrain_started_at).total_seconds()
        return int(self.retrain_interval_seconds - elapsed)

    def _reason_for_flow(self, flow: FlowRecord, score: float) -> str:
        if flow.syn_packets >= 8:
            return "Connection pattern looks scan-like with elevated SYN activity"
        if flow.src_to_dst_bytes > flow.dst_to_src_bytes * 3:
            return "Outbound traffic is much higher than the recent baseline"
        if score >= 1.5:
            return "Model reconstruction error suggests a new or rare traffic pattern"
        return "Traffic behavior is outside the learned normal range"
