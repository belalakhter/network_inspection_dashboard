from __future__ import annotations

from collections import Counter, deque
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Deque, Iterable, List

from app.schemas import BufferSnapshot, FlowRecord


class RollingFlowBuffer:
    def __init__(self, window_minutes: int = 30) -> None:
        self.window_minutes = window_minutes
        self._flows: Deque[FlowRecord] = deque()
        self._lock = Lock()

    def add_flow(self, flow: FlowRecord) -> None:
        with self._lock:
            self._flows.append(flow)
            self._prune_locked(reference_time=flow.timestamp)

    def add_flows(self, flows: Iterable[FlowRecord]) -> None:
        with self._lock:
            for flow in flows:
                self._flows.append(flow)
            self._prune_locked(reference_time=datetime.now(timezone.utc))

    def snapshot(self) -> BufferSnapshot:
        with self._lock:
            self._prune_locked(reference_time=datetime.now(timezone.utc))
            flows = list(self._flows)
        return BufferSnapshot(
            window_minutes=self.window_minutes,
            flow_count=len(flows),
            captured_at=datetime.now(timezone.utc),
            flows=flows,
        )

    def latest_flows(self, limit: int = 50) -> List[FlowRecord]:
        with self._lock:
            self._prune_locked(reference_time=datetime.now(timezone.utc))
            return list(self._flows)[-limit:]

    def application_ranking(self, limit: int = 5) -> List[str]:
        with self._lock:
            self._prune_locked(reference_time=datetime.now(timezone.utc))
            counts = Counter(flow.application for flow in self._flows)
        return [name for name, _ in counts.most_common(limit)]

    def outbound_bytes(self) -> int:
        with self._lock:
            self._prune_locked(reference_time=datetime.now(timezone.utc))
            return sum(flow.src_to_dst_bytes for flow in self._flows)

    def inbound_bytes(self) -> int:
        with self._lock:
            self._prune_locked(reference_time=datetime.now(timezone.utc))
            return sum(flow.dst_to_src_bytes for flow in self._flows)

    def __len__(self) -> int:
        with self._lock:
            self._prune_locked(reference_time=datetime.now(timezone.utc))
            return len(self._flows)

    def _prune_locked(self, reference_time: datetime) -> None:
        cutoff = reference_time - timedelta(minutes=self.window_minutes)
        while self._flows and self._flows[0].timestamp < cutoff:
            self._flows.popleft()
