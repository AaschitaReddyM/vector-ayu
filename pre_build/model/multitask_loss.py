"""
Multi-task loss (Spec §3.4).

    L_total = α · L_respiratory + β · L_cardiovascular + γ · L_metabolic

The α, β, γ "Priority Knobs" let us bias training toward the heads where
clinical false-negatives are most costly (cardiac > respiratory > metabolic
by default, mirroring the spec's plain-English breakdown).

Each head outputs a logit; ground-truth is binary (acute event in the
prediction horizon). We use BCEWithLogitsLoss with per-head positive-class
weighting to handle the heavy class imbalance of acute events.
"""

from __future__ import annotations

from dataclasses import dataclass

import torch
import torch.nn as nn


@dataclass(frozen=True)
class MultiTaskWeights:
    alpha: float = 1.0   # respiratory
    beta: float = 5.0    # cardiovascular — spec calls this out as 5x weight
    gamma: float = 2.0   # metabolic

    def as_tensor(self, device: torch.device | str = "cpu") -> torch.Tensor:
        return torch.tensor(
            [self.alpha, self.beta, self.gamma],
            dtype=torch.float32,
            device=device,
        )


class MultiTaskLoss(nn.Module):
    """
    Computes per-head BCE-with-logits loss, then a weighted sum.

    Returns a dict with the total + each component so the training loop can
    log them independently (essential for tuning α/β/γ).
    """

    def __init__(
        self,
        weights: MultiTaskWeights = MultiTaskWeights(),
        pos_weight_respiratory: float | None = None,
        pos_weight_cardiovascular: float | None = None,
        pos_weight_metabolic: float | None = None,
    ) -> None:
        super().__init__()
        self.weights = weights
        self.bce_resp = self._make_bce(pos_weight_respiratory)
        self.bce_card = self._make_bce(pos_weight_cardiovascular)
        self.bce_meta = self._make_bce(pos_weight_metabolic)

    @staticmethod
    def _make_bce(pos_weight: float | None) -> nn.BCEWithLogitsLoss:
        if pos_weight is None:
            return nn.BCEWithLogitsLoss()
        return nn.BCEWithLogitsLoss(pos_weight=torch.tensor([pos_weight]))

    def forward(
        self,
        logits: dict[str, torch.Tensor],
        targets: dict[str, torch.Tensor],
    ) -> dict[str, torch.Tensor]:
        l_resp = self.bce_resp(logits["respiratory"], targets["respiratory"].float())
        l_card = self.bce_card(logits["cardiovascular"], targets["cardiovascular"].float())
        l_meta = self.bce_meta(logits["metabolic"], targets["metabolic"].float())

        total = (
            self.weights.alpha * l_resp
            + self.weights.beta * l_card
            + self.weights.gamma * l_meta
        )
        return {
            "total": total,
            "respiratory": l_resp.detach(),
            "cardiovascular": l_card.detach(),
            "metabolic": l_meta.detach(),
        }
