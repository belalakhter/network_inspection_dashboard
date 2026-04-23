from __future__ import annotations

import random
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import List

from app.config import Settings
from app.schemas import FlowRecord


class FlowCollector(ABC):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @property
    @abstractmethod
    def mode(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def collect_batch(self, captured_at: datetime | None = None) -> List[FlowRecord]:
        raise NotImplementedError


class SyntheticFlowCollector(FlowCollector):
    @property
    def mode(self) -> str:
        return "synthetic"

    def collect_batch(self, captured_at: datetime | None = None) -> List[FlowRecord]:
        now = captured_at or datetime.now(timezone.utc)
        batch_size = random.randint(3, 8)
        return [self._build_flow(now) for _ in range(batch_size)]

    def _build_flow(self, captured_at: datetime) -> FlowRecord:
        applications = ["HTTP", "HTTPS", "DNS", "SSH", "TLS"]
        protocols = {"HTTP": "TCP", "HTTPS": "TCP", "DNS": "UDP", "SSH": "TCP", "TLS": "TCP"}
        application = random.choice(applications)
        src_bytes = random.randint(500, 15000)
        dst_bytes = random.randint(200, 20000)
        duration_ms = random.uniform(20, 4000)
        syn_packets = random.randint(0, 4)
        rst_packets = 0 if application != "SSH" else random.randint(0, 2)
        avg_packet_size = (src_bytes + dst_bytes) / max(random.randint(4, 40), 1)

        if random.random() < 0.08:
            src_bytes *= random.randint(3, 8)
            duration_ms = random.uniform(5, 100)
            syn_packets = random.randint(8, 20)
            rst_packets = random.randint(1, 4)

        return FlowRecord(
            timestamp=captured_at,
            src_ip=f"10.0.0.{random.randint(2, 240)}",
            dst_ip=f"34.120.{random.randint(1, 200)}.{random.randint(2, 240)}",
            src_port=random.randint(1024, 65535),
            dst_port=random.choice([53, 80, 443, 22, 8080]),
            protocol=protocols[application],
            application=application,
            duration_ms=duration_ms,
            src_to_dst_bytes=src_bytes,
            dst_to_src_bytes=dst_bytes,
            src_to_dst_packets=random.randint(2, 60),
            dst_to_src_packets=random.randint(1, 45),
            syn_packets=syn_packets,
            fin_packets=random.randint(0, 3),
            rst_packets=rst_packets,
            avg_packet_size=avg_packet_size,
        )


class NFStreamFlowCollector(FlowCollector):
    def __init__(self, settings: Settings) -> None:
        super().__init__(settings)
        try:
            from nfstream import NFStreamer
        except ImportError as exc:  # pragma: no cover - depends on optional package
            raise RuntimeError(
                "nfstream is not installed. Install it or set FLOW_COLLECTOR_MODE=synthetic."
            ) from exc
        self._streamer_cls = NFStreamer

    @property
    def mode(self) -> str:
        return "nfstream"

    def collect_batch(self, captured_at: datetime | None = None) -> List[FlowRecord]:
        now = captured_at or datetime.now(timezone.utc)
        streamer = self._streamer_cls(
            source=self.settings.capture_source,
            statistical_analysis=True,
            idle_timeout=self.settings.capture_interval_seconds,
            active_timeout=self.settings.capture_interval_seconds,
        )
        flows: List[FlowRecord] = []
        for flow in streamer:
            flows.append(self._map_flow(flow=flow, captured_at=now))
        return flows

    def _map_flow(self, flow: object, captured_at: datetime) -> FlowRecord:
        application_name = getattr(flow, "application_name", "") or "Unknown"
        protocol_name = getattr(flow, "protocol", "") or "other"
        src_bytes = int(getattr(flow, "src2dst_bytes", 0) or 0)
        dst_bytes = int(getattr(flow, "dst2src_bytes", 0) or 0)
        src_packets = int(getattr(flow, "src2dst_packets", 0) or 0)
        dst_packets = int(getattr(flow, "dst2src_packets", 0) or 0)
        packet_total = max(src_packets + dst_packets, 1)
        avg_packet_size = float(src_bytes + dst_bytes) / packet_total

        return FlowRecord(
            timestamp=captured_at,
            src_ip=str(getattr(flow, "src_ip", "0.0.0.0")),
            dst_ip=str(getattr(flow, "dst_ip", "0.0.0.0")),
            src_port=int(getattr(flow, "src_port", 0) or 0),
            dst_port=int(getattr(flow, "dst_port", 0) or 0),
            protocol=str(protocol_name).upper(),
            application=str(application_name).upper(),
            duration_ms=float(getattr(flow, "bidirectional_duration_ms", 0.0) or 0.0),
            src_to_dst_bytes=src_bytes,
            dst_to_src_bytes=dst_bytes,
            src_to_dst_packets=src_packets,
            dst_to_src_packets=dst_packets,
            syn_packets=int(getattr(flow, "bidirectional_syn_packets", 0) or 0),
            fin_packets=int(getattr(flow, "bidirectional_fin_packets", 0) or 0),
            rst_packets=int(getattr(flow, "src2dst_rst_packets", 0) or 0),
            avg_packet_size=avg_packet_size,
        )


def build_flow_collector(settings: Settings) -> FlowCollector:
    if settings.collector_mode == "nfstream":
        return NFStreamFlowCollector(settings)
    return SyntheticFlowCollector(settings)
