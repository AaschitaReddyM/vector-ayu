"""
XAI Attributions (Spec §4 — *Explainable AI (XAI) breakdown powered by SHAP
core libraries*; Spec §8 — Captum / SHAP Core Library).

Every flag on the 72-Hour Provider Triage Dashboard embeds a SHAP-style
breakdown so clinicians know *why* the model fired. We use Captum's
IntegratedGradients (the canonical PyTorch attribution method, gradient-
based equivalent of KernelSHAP for differentiable models) to attribute a
head's logit back to its three input streams: static, clinical, environmental.

Returned shape mirrors the input — clinicians get a per-channel,
per-time-step heatmap they can hover for plain-English labels.
"""

from __future__ import annotations

from dataclasses import dataclass

import torch
import torch.nn as nn
from captum.attr import IntegratedGradients


HEADS: tuple[str, ...] = ("respiratory", "cardiovascular", "metabolic")


class _HeadWrapper(nn.Module):
    """Turn the multi-output TFT into a scalar-output module per head, so
    Captum can attribute against a single target without ambiguity."""

    def __init__(self, model: nn.Module, head: str) -> None:
        super().__init__()
        self.model = model
        self.head = head

    def forward(
        self,
        static_x: torch.Tensor,
        clinical_x: torch.Tensor,
        environmental_x: torch.Tensor,
    ) -> torch.Tensor:
        out = self.model(static_x, clinical_x, environmental_x)
        return out[self.head]


@dataclass
class AttributionBundle:
    head: str
    static: torch.Tensor          # (B, S)
    clinical: torch.Tensor        # (B, T, C_clin)
    environmental: torch.Tensor   # (B, T, C_env)
    convergence_delta: torch.Tensor  # IG completeness check

    def per_channel_summary(self) -> dict[str, dict[str, float]]:
        """Reduce to per-channel magnitudes — what the dashboard tooltips show."""
        def _summary(t: torch.Tensor) -> list[float]:
            # mean absolute attribution per channel, averaged across batch.
            return t.abs().mean(dim=tuple(range(t.ndim - 1))).cpu().tolist()
        return {
            "static": {f"s{i}": v for i, v in enumerate(_summary(self.static))},
            "clinical": {f"c{i}": v for i, v in enumerate(_summary(self.clinical))},
            "environmental": {f"e{i}": v for i, v in enumerate(_summary(self.environmental))},
        }


def attribute_head(
    model: nn.Module,
    head: str,
    static_x: torch.Tensor,
    clinical_x: torch.Tensor,
    environmental_x: torch.Tensor,
    n_steps: int = 32,
) -> AttributionBundle:
    """Run Integrated Gradients for one TFT head and return the attribution bundle."""
    if head not in HEADS:
        raise ValueError(f"unknown head '{head}'")

    wrapper = _HeadWrapper(model, head).eval()
    ig = IntegratedGradients(wrapper)

    # Baselines: zero tensors — the canonical IG baseline for tabular/temporal data.
    baselines = (
        torch.zeros_like(static_x),
        torch.zeros_like(clinical_x),
        torch.zeros_like(environmental_x),
    )
    attributions, delta = ig.attribute(
        inputs=(static_x, clinical_x, environmental_x),
        baselines=baselines,
        n_steps=n_steps,
        return_convergence_delta=True,
    )
    return AttributionBundle(
        head=head,
        static=attributions[0].detach(),
        clinical=attributions[1].detach(),
        environmental=attributions[2].detach(),
        convergence_delta=delta.detach(),
    )


if __name__ == "__main__":
    from pre_build.model import TFTConfig, TFTSkeleton

    cfg = TFTConfig()
    model = TFTSkeleton(cfg).eval()
    static = torch.randn(2, cfg.static_input_dim)
    clin = torch.randn(2, cfg.horizon_hours, cfg.clinical_input_dim)
    env = torch.randn(2, cfg.horizon_hours, cfg.environmental_input_dim)
    bundle = attribute_head(model, "cardiovascular", static, clin, env, n_steps=16)
    summary = bundle.per_channel_summary()
    print(f"  IG convergence delta: {bundle.convergence_delta.tolist()}")
    print(f"  static channels    : {summary['static']}")
    print(f"  top-3 environmental: ", end="")
    print(sorted(summary["environmental"].items(), key=lambda x: -x[1])[:3])
