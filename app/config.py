from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    buffer_window_minutes: int = 30
    capture_interval_seconds: int = 300
    retrain_interval_seconds: int = 1800
    collector_mode: str = "synthetic"
    capture_source: str = "eth0"
    bootstrap_flow_count: int = 12
    retrain_epochs: int = 5

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            buffer_window_minutes=int(os.getenv("FLOW_BUFFER_WINDOW_MINUTES", "30")),
            capture_interval_seconds=int(os.getenv("FLOW_CAPTURE_INTERVAL_SECONDS", "300")),
            retrain_interval_seconds=int(os.getenv("MODEL_RETRAIN_INTERVAL_SECONDS", "1800")),
            collector_mode=os.getenv("FLOW_COLLECTOR_MODE", "synthetic").strip().lower(),
            capture_source=os.getenv("FLOW_CAPTURE_SOURCE", "eth0").strip(),
            bootstrap_flow_count=int(os.getenv("FLOW_BOOTSTRAP_COUNT", "12")),
            retrain_epochs=int(os.getenv("MODEL_RETRAIN_EPOCHS", "5")),
        )
