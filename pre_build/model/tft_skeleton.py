"""
Temporal Fusion Transformer skeleton (Spec §2 step 4, §3.4, §4).

Per spec §9.1.3, the goal of this pre-build artifact is to *confirm input/
output dimension paths are stable* — not to train production weights. The
forward pass below runs end-to-end on synthetic tensors so the buildathon
team can plug in real EHR + climate streams on Day 1 without re-shaping.

Architecture
------------
Inputs are split into three logical streams (spec §8 "binds static EHR
clinical profiles alongside time-varying dynamic environmental arrays"):

    static_x         : (B, S_static)        — SDOH, demographics, comorbidities
    temporal_clinical_x : (B, T, C_clin)    — wearable + CGM + observations
    temporal_environmental_x : (B, T, C_env) — H3-cell exposure vector × time

A Variable Selection layer per stream gates which inputs matter, a shared
LSTM encoder produces the hidden temporal representation, and an attention
block re-weights the time axis. The pooled representation is then fed into
three task heads (respiratory / cardiovascular / metabolic) — the
multi-task split per spec §3.4.

This is a lightweight TFT-shaped skeleton, not the full pytorch-forecasting
implementation; swapping in `pytorch_forecasting.TemporalFusionTransformer`
later keeps the same I/O contract.
"""

from __future__ import annotations

from dataclasses import dataclass

import torch
import torch.nn as nn


# ── Config ─────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class TFTConfig:
    # Input dimensions
    static_input_dim: int = 16        # static SDOH + demographics + Shielding Coeff
    clinical_input_dim: int = 12      # HR, SpO2, CGM, BP, temp, ...
    environmental_input_dim: int = 8  # PM2.5, ozone, AQI, pollen, temp, humidity, UV, wind
    # Sequence
    horizon_hours: int = 72           # spec §2: 72-hour triage window
    # Architecture
    hidden_dim: int = 64
    lstm_layers: int = 2
    attn_heads: int = 4
    dropout: float = 0.1


# ── Building blocks ────────────────────────────────────────────────────────

class GatedResidualNetwork(nn.Module):
    """GRN — the TFT's signature non-linearity, used inside variable selection
    and after attention. (Lim et al., 2019.)"""

    def __init__(self, input_dim: int, hidden_dim: int, dropout: float = 0.1) -> None:
        super().__init__()
        self.fc1 = nn.Linear(input_dim, hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, hidden_dim)
        self.gate = nn.Linear(hidden_dim, hidden_dim)
        self.skip = nn.Linear(input_dim, hidden_dim) if input_dim != hidden_dim else nn.Identity()
        self.dropout = nn.Dropout(dropout)
        self.layernorm = nn.LayerNorm(hidden_dim)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        h = torch.relu(self.fc1(x))
        h = self.dropout(self.fc2(h))
        gate = torch.sigmoid(self.gate(h))
        return self.layernorm(self.skip(x) + gate * h)


class VariableSelection(nn.Module):
    """Soft per-feature gating so the model learns which channels matter at
    each step. Produces a single `hidden_dim` vector per time step."""

    def __init__(self, input_dim: int, hidden_dim: int, dropout: float = 0.1) -> None:
        super().__init__()
        self.weight_net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, input_dim),
            nn.Softmax(dim=-1),
        )
        self.feature_grn = GatedResidualNetwork(input_dim, hidden_dim, dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        weights = self.weight_net(x)
        gated = x * weights
        return self.feature_grn(gated)


# ── Backbone ───────────────────────────────────────────────────────────────

class TFTSkeleton(nn.Module):
    """
    Temporal Fusion Transformer skeleton with three clinical task heads.

    Returns a dict of logits (one per head). Use `MultiTaskLoss` from
    ``multitask_loss.py`` to combine them with the α/β/γ priority knobs.
    """

    def __init__(self, cfg: TFTConfig = TFTConfig()) -> None:
        super().__init__()
        self.cfg = cfg

        self.static_vsn = VariableSelection(cfg.static_input_dim, cfg.hidden_dim, cfg.dropout)
        self.clinical_vsn = VariableSelection(cfg.clinical_input_dim, cfg.hidden_dim, cfg.dropout)
        self.enviro_vsn = VariableSelection(cfg.environmental_input_dim, cfg.hidden_dim, cfg.dropout)

        # Fuse clinical + environmental into a single temporal stream before LSTM.
        self.temporal_fuse = GatedResidualNetwork(
            2 * cfg.hidden_dim, cfg.hidden_dim, cfg.dropout
        )

        # Static context biases the LSTM initial state.
        self.static_to_h0 = nn.Linear(cfg.hidden_dim, cfg.hidden_dim * cfg.lstm_layers)
        self.static_to_c0 = nn.Linear(cfg.hidden_dim, cfg.hidden_dim * cfg.lstm_layers)

        self.encoder = nn.LSTM(
            input_size=cfg.hidden_dim,
            hidden_size=cfg.hidden_dim,
            num_layers=cfg.lstm_layers,
            batch_first=True,
            dropout=cfg.dropout if cfg.lstm_layers > 1 else 0.0,
        )

        self.attn = nn.MultiheadAttention(
            embed_dim=cfg.hidden_dim,
            num_heads=cfg.attn_heads,
            dropout=cfg.dropout,
            batch_first=True,
        )
        self.post_attn = GatedResidualNetwork(cfg.hidden_dim, cfg.hidden_dim, cfg.dropout)

        # Multi-task heads — spec §4 (Multi-Task Prediction Heads).
        self.head_respiratory = self._make_head(cfg.hidden_dim, cfg.dropout)
        self.head_cardiovascular = self._make_head(cfg.hidden_dim, cfg.dropout)
        self.head_metabolic = self._make_head(cfg.hidden_dim, cfg.dropout)

    @staticmethod
    def _make_head(hidden_dim: int, dropout: float) -> nn.Module:
        return nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim // 2, 1),  # logit; sigmoid lives in the loss
        )

    def forward(
        self,
        static_x: torch.Tensor,                # (B, static_input_dim)
        temporal_clinical_x: torch.Tensor,     # (B, T, clinical_input_dim)
        temporal_environmental_x: torch.Tensor,  # (B, T, env_input_dim)
    ) -> dict[str, torch.Tensor]:
        b, t, _ = temporal_clinical_x.shape

        # 1. Variable selection on each stream.
        static_ctx = self.static_vsn(static_x)                          # (B, H)
        clin_seq = self.clinical_vsn(temporal_clinical_x)               # (B, T, H)
        env_seq = self.enviro_vsn(temporal_environmental_x)             # (B, T, H)

        # 2. Fuse clinical + environmental at each step.
        fused = self.temporal_fuse(torch.cat([clin_seq, env_seq], dim=-1))  # (B, T, H)

        # 3. Seed LSTM state from static context.
        h0 = self.static_to_h0(static_ctx).view(
            self.cfg.lstm_layers, b, self.cfg.hidden_dim
        ).contiguous()
        c0 = self.static_to_c0(static_ctx).view(
            self.cfg.lstm_layers, b, self.cfg.hidden_dim
        ).contiguous()
        enc, _ = self.encoder(fused, (h0, c0))                          # (B, T, H)

        # 4. Self-attention over time.
        attn_out, _ = self.attn(enc, enc, enc, need_weights=False)
        attn_out = self.post_attn(attn_out)

        # 5. Pool the horizon (last step is the 72-hour-ahead representation).
        pooled = attn_out[:, -1, :]                                     # (B, H)

        return {
            "respiratory": self.head_respiratory(pooled).squeeze(-1),
            "cardiovascular": self.head_cardiovascular(pooled).squeeze(-1),
            "metabolic": self.head_metabolic(pooled).squeeze(-1),
        }


# ── CLI smoke test ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    cfg = TFTConfig()
    model = TFTSkeleton(cfg)

    batch = 4
    static_x = torch.randn(batch, cfg.static_input_dim)
    clinical_x = torch.randn(batch, cfg.horizon_hours, cfg.clinical_input_dim)
    environmental_x = torch.randn(batch, cfg.horizon_hours, cfg.environmental_input_dim)

    logits = model(static_x, clinical_x, environmental_x)
    for head, t in logits.items():
        print(f"  head={head:16s} shape={tuple(t.shape)}  range=[{t.min():.3f}, {t.max():.3f}]")

    n_params = sum(p.numel() for p in model.parameters())
    print(f"  total params: {n_params:,}")
