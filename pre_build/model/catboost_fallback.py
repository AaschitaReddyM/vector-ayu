"""
CatBoost fallback (Spec §5 row 5 — *Hierarchical Graceful Pipeline Degradation*).

When the wearable telemetry stream goes null ($NaN$) — the patient forgot to
charge their watch, their CGM patch fell off, the API blipped — the TFT path
cannot run cleanly. We fall back to a CatBoost ensemble that consumes only
the always-available signals:

  • Static EHR profile (demographics, comorbidities, last labs)
  • Climate / H3-cell exposure vector

CatBoost is chosen because (a) it natively handles missing values and
categorical features, (b) it matches the user's prior capstone (Health-Mate
hit 88.14% with CatBoost — see ``draft 1.docx``), and (c) it trains in
seconds on CPU, which matters when the buildathon clock is ticking.

The class is structured so the same call site can route to either the TFT
or the fallback based on input completeness.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np

try:
    from catboost import CatBoostClassifier
    _CATBOOST_AVAILABLE = True
except ImportError:  # keep the skeleton importable even before deps land
    CatBoostClassifier = None  # type: ignore[assignment,misc]
    _CATBOOST_AVAILABLE = False


HEADS = ("respiratory", "cardiovascular", "metabolic")


@dataclass(frozen=True)
class CatBoostConfig:
    iterations: int = 500
    depth: int = 6
    learning_rate: float = 0.05
    loss_function: str = "Logloss"
    eval_metric: str = "AUC"
    random_seed: int = 42
    verbose: int = 0


class CatBoostFallback:
    """
    Three independent CatBoost binary classifiers (one per clinical head).

    Why not multi-output? CatBoost doesn't natively support multi-task in the
    same way TFT does, but per-head models trained on the same feature matrix
    are functionally equivalent for the graceful-degradation use case — and
    each can carry its own class weight to match the α/β/γ priority of the
    TFT loss.
    """

    def __init__(
        self,
        cfg: CatBoostConfig = CatBoostConfig(),
        cat_features: Sequence[int] | None = None,
    ) -> None:
        if not _CATBOOST_AVAILABLE:
            raise ImportError(
                "catboost is not installed. `pip install catboost` to enable the fallback."
            )
        self.cfg = cfg
        self.cat_features = list(cat_features) if cat_features else None
        self.models: dict[str, CatBoostClassifier] = {}

    @staticmethod
    def _build_feature_matrix(
        static_x: np.ndarray,           # (N, S)
        environmental_x: np.ndarray,    # (N, T, C_env) — collapsed to (N, C_env*stats)
    ) -> np.ndarray:
        """Flatten time-varying environmental data into per-window statistics.

        For the fallback we collapse the 72-hour environmental window into
        (mean, max, std) per channel — cheap, robust, and avoids exploding
        feature width.
        """
        if environmental_x.ndim != 3:
            raise ValueError("environmental_x must be (N, T, C_env)")
        env_mean = environmental_x.mean(axis=1)
        env_max = environmental_x.max(axis=1)
        env_std = environmental_x.std(axis=1)
        return np.concatenate([static_x, env_mean, env_max, env_std], axis=1)

    def fit(
        self,
        static_x: np.ndarray,
        environmental_x: np.ndarray,
        targets: dict[str, np.ndarray],
        class_weights: dict[str, list[float]] | None = None,
    ) -> "CatBoostFallback":
        x = self._build_feature_matrix(static_x, environmental_x)
        for head in HEADS:
            if head not in targets:
                raise KeyError(f"missing target for head '{head}'")
            model = CatBoostClassifier(
                iterations=self.cfg.iterations,
                depth=self.cfg.depth,
                learning_rate=self.cfg.learning_rate,
                loss_function=self.cfg.loss_function,
                eval_metric=self.cfg.eval_metric,
                random_seed=self.cfg.random_seed,
                verbose=self.cfg.verbose,
                class_weights=(class_weights or {}).get(head),
            )
            model.fit(x, targets[head], cat_features=self.cat_features)
            self.models[head] = model
        return self

    def predict_proba(
        self,
        static_x: np.ndarray,
        environmental_x: np.ndarray,
    ) -> dict[str, np.ndarray]:
        if not self.models:
            raise RuntimeError("fallback model has not been fitted yet")
        x = self._build_feature_matrix(static_x, environmental_x)
        return {head: self.models[head].predict_proba(x)[:, 1] for head in HEADS}


# ── Routing helper ─────────────────────────────────────────────────────────

def should_use_fallback(
    temporal_clinical_x: np.ndarray,
    nan_threshold: float = 0.5,
) -> bool:
    """
    Decide whether to take the TFT path or the CatBoost fallback for a batch.

    Per spec §5 row 5, the fallback kicks in when streaming telemetry shows
    null values. We treat the batch as degraded if more than
    ``nan_threshold`` of the clinical tensor is NaN.
    """
    if temporal_clinical_x.size == 0:
        return True
    nan_frac = float(np.isnan(temporal_clinical_x).mean())
    return nan_frac >= nan_threshold


# ── CLI smoke test ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    rng = np.random.default_rng(0)
    n, t, s, c_env = 200, 72, 16, 8

    static_x = rng.normal(size=(n, s)).astype(np.float32)
    env_x = rng.normal(size=(n, t, c_env)).astype(np.float32)

    # Plant a weak signal: head=respiratory correlates with environmental ch0 mean.
    y_resp = (env_x.mean(axis=1)[:, 0] + rng.normal(0, 0.5, n) > 0).astype(np.int8)
    y_card = (static_x[:, 0] + rng.normal(0, 0.5, n) > 0).astype(np.int8)
    y_meta = (static_x[:, 1] - env_x.mean(axis=1)[:, 1] + rng.normal(0, 0.5, n) > 0).astype(np.int8)

    fb = CatBoostFallback(CatBoostConfig(iterations=100))
    fb.fit(
        static_x,
        env_x,
        {"respiratory": y_resp, "cardiovascular": y_card, "metabolic": y_meta},
    )

    proba = fb.predict_proba(static_x[:5], env_x[:5])
    for head, p in proba.items():
        print(f"  head={head:16s} sample_probs={np.round(p, 3).tolist()}")
