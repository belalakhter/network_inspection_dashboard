from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Sequence

import torch

from app.schemas import FlowRecord


FEATURE_NAMES: List[str] = [
    "duration_ms",
    "src_to_dst_bytes",
    "dst_to_src_bytes",
    "src_to_dst_packets",
    "dst_to_src_packets",
    "syn_packets",
    "fin_packets",
    "rst_packets",
    "avg_packet_size",
]

PROTOCOL_TO_ID = {"tcp": 0.0, "udp": 1.0, "icmp": 2.0, "other": 3.0}
APP_TO_ID = {
    "http": 0.0,
    "https": 1.0,
    "dns": 2.0,
    "ssh": 3.0,
    "tls": 4.0,
    "unknown": 5.0,
}


@dataclass
class NormalizationStats:
    mean: torch.Tensor
    std: torch.Tensor


def _safe_lookup(value: str, mapping: dict[str, float], fallback: float) -> float:
    return mapping.get(value.lower(), fallback)


def flow_to_feature_vector(flow: FlowRecord) -> List[float]:
    return [
        flow.duration_ms,
        float(flow.src_to_dst_bytes),
        float(flow.dst_to_src_bytes),
        float(flow.src_to_dst_packets),
        float(flow.dst_to_src_packets),
        float(flow.syn_packets),
        float(flow.fin_packets),
        float(flow.rst_packets),
        flow.avg_packet_size,
        _safe_lookup(flow.protocol, PROTOCOL_TO_ID, PROTOCOL_TO_ID["other"]),
        _safe_lookup(flow.application, APP_TO_ID, APP_TO_ID["unknown"]),
    ]


def build_feature_tensor(flows: Sequence[FlowRecord]) -> torch.Tensor:
    if not flows:
        return torch.empty((0, 1, len(FEATURE_NAMES) + 2), dtype=torch.float32)

    vectors = [flow_to_feature_vector(flow) for flow in flows]
    tensor = torch.tensor(vectors, dtype=torch.float32)
    return tensor.unsqueeze(1)


def fit_normalization(tensor: torch.Tensor) -> NormalizationStats:
    if tensor.numel() == 0:
        feature_count = tensor.shape[-1] if tensor.dim() >= 1 else len(FEATURE_NAMES) + 2
        zeros = torch.zeros(feature_count, dtype=torch.float32)
        ones = torch.ones(feature_count, dtype=torch.float32)
        return NormalizationStats(mean=zeros, std=ones)

    flat = tensor.reshape(-1, tensor.shape[-1])
    mean = flat.mean(dim=0)
    std = flat.std(dim=0).clamp_min(1e-6)
    return NormalizationStats(mean=mean, std=std)


def normalize_tensor(tensor: torch.Tensor, stats: NormalizationStats) -> torch.Tensor:
    if tensor.numel() == 0:
        return tensor
    return (tensor - stats.mean) / stats.std
