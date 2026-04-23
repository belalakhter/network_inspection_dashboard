from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional, Sequence

import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

from app.schemas import FlowRecord, TrainingStatus
from model.dataset import (
    NormalizationStats,
    build_feature_tensor,
    fit_normalization,
    normalize_tensor,
)
from model.model import LSTMAutoencoder


@dataclass
class TrainingResult:
    trained_at: datetime
    epochs_completed: int
    latest_loss: float
    best_loss: float
    model_version: int
    sample_count: int


class ModelTrainer:
    def __init__(
        self,
        input_size: int,
        hidden_size: int = 32,
        latent_size: int = 16,
        min_train_samples: int = 8,
    ) -> None:
        self.device = torch.device("cpu")
        self.model = LSTMAutoencoder(
            input_size=input_size,
            hidden_size=hidden_size,
            latent_size=latent_size,
        ).to(self.device)
        self.criterion = nn.MSELoss()
        self.min_train_samples = min_train_samples
        self.normalization = NormalizationStats(
            mean=torch.zeros(input_size),
            std=torch.ones(input_size),
        )
        self.model_version = 0
        self.best_loss: Optional[float] = None
        self.last_result: Optional[TrainingResult] = None

    def train(self, flows: Sequence[FlowRecord], epochs: int = 5, batch_size: int = 32) -> Optional[TrainingResult]:
        if len(flows) < self.min_train_samples:
            return None

        tensor = build_feature_tensor(flows)
        self.normalization = fit_normalization(tensor)
        normalized = normalize_tensor(tensor, self.normalization)
        dataset = TensorDataset(normalized, normalized)
        loader = DataLoader(dataset, batch_size=min(batch_size, len(dataset)), shuffle=True)

        optimizer = torch.optim.Adam(self.model.parameters(), lr=1e-3)
        latest_loss = 0.0

        self.model.train()
        for _ in range(epochs):
            epoch_loss = 0.0
            for batch_inputs, batch_targets in loader:
                batch_inputs = batch_inputs.to(self.device)
                batch_targets = batch_targets.to(self.device)
                optimizer.zero_grad()
                outputs = self.model(batch_inputs)
                loss = self.criterion(outputs, batch_targets)
                loss.backward()
                optimizer.step()
                epoch_loss += loss.item()
            latest_loss = epoch_loss / max(len(loader), 1)

        self.model_version += 1
        if self.best_loss is None or latest_loss < self.best_loss:
            self.best_loss = latest_loss

        self.last_result = TrainingResult(
            trained_at=datetime.now(timezone.utc),
            epochs_completed=epochs,
            latest_loss=latest_loss,
            best_loss=self.best_loss,
            model_version=self.model_version,
            sample_count=len(flows),
        )
        return self.last_result

    def score_flows(self, flows: Sequence[FlowRecord]) -> List[float]:
        if not flows:
            return []

        tensor = build_feature_tensor(flows)
        normalized = normalize_tensor(tensor, self.normalization).to(self.device)
        self.model.eval()
        with torch.no_grad():
            reconstruction = self.model(normalized)
            losses = ((reconstruction - normalized) ** 2).mean(dim=(1, 2))
        return losses.cpu().tolist()

    def status(
        self,
        buffer_flow_count: int,
        next_retrain_in_seconds: int,
        collector_mode: str,
        last_capture_at: datetime | None = None,
        last_capture_flow_count: int = 0,
    ) -> TrainingStatus:
        if self.last_result is None:
            return TrainingStatus(
                buffer_flow_count=buffer_flow_count,
                next_retrain_in_seconds=max(next_retrain_in_seconds, 0),
                collector_mode=collector_mode,
                last_capture_at=last_capture_at,
                last_capture_flow_count=last_capture_flow_count,
                bootstrap_completed=False,
            )

        return TrainingStatus(
            last_trained_at=self.last_result.trained_at,
            epochs_completed=self.last_result.epochs_completed,
            latest_loss=self.last_result.latest_loss,
            best_loss=self.last_result.best_loss,
            model_version=self.last_result.model_version,
            buffer_flow_count=buffer_flow_count,
            next_retrain_in_seconds=max(next_retrain_in_seconds, 0),
            collector_mode=collector_mode,
            last_capture_at=last_capture_at,
            last_capture_flow_count=last_capture_flow_count,
            bootstrap_completed=True,
        )
