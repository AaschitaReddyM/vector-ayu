"""
Token-Bucket Triage Constrainer (Spec §5 row 2 — *Extreme Clinician Alert Fatigue*).

Regional environmental shifts affect large geographic zones, triggering
thousands of simultaneous patient flags. Doctors mute systems that page them
for everything. We enforce a constrained-optimization gate that analyzes a
clinic's operational capacity and limits total daily warnings to the
top 2–5% of highest-risk actionable deltas.

Implementation: a per-clinic token bucket. Each clinic has a daily token
budget set from its operational capacity. When a tranche of patient flags
arrives, we sort by Climate Volatility Delta and emit the top-K that fit
within the remaining bucket — the rest fall back to the cold queue.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable


@dataclass(frozen=True)
class PatientFlag:
    """A candidate triage flag emitted by the TFT for a single patient."""
    patient_id: str
    volatility_delta: float   # higher = more dangerous, the sort key
    risk_total: float         # underlying probability of acute event
    head: str                 # which head fired (respiratory/cardio/metabolic)
    payload: dict = field(default_factory=dict)


@dataclass
class TokenBucketDecision:
    accepted: list[PatientFlag]
    deferred: list[PatientFlag]
    capacity_used: int
    capacity_remaining: int


class TokenBucketConstrainer:
    """
    Restrict downstream alert volume to a daily quota.

    Parameters
    ----------
    panel_size : int
        Total active patients in the clinic's panel.
    top_fraction : float
        Fraction of the panel allowed through per day. Spec says 2–5%
        (0.02–0.05); default 0.05 (5%) — relax to 0.02 for fragile clinics.
    floor : int
        Always allow at least this many flags through, regardless of
        panel size, so tiny clinics still get value.
    """

    def __init__(self, panel_size: int, top_fraction: float = 0.05, floor: int = 5) -> None:
        if not 0 < top_fraction <= 1:
            raise ValueError("top_fraction must be in (0, 1]")
        if panel_size <= 0:
            raise ValueError("panel_size must be > 0")
        self.panel_size = panel_size
        self.top_fraction = top_fraction
        self.floor = floor
        self._tokens_today = self.daily_budget()

    def daily_budget(self) -> int:
        """The per-day cap derived from panel size."""
        return max(self.floor, int(round(self.panel_size * self.top_fraction)))

    def reset_day(self) -> None:
        """Call at midnight to refill the bucket."""
        self._tokens_today = self.daily_budget()

    @property
    def tokens_remaining(self) -> int:
        return self._tokens_today

    def constrain(self, flags: Iterable[PatientFlag]) -> TokenBucketDecision:
        """
        Apply the token-bucket gate to a batch of candidate flags.

        Highest ``volatility_delta`` wins; ties broken by ``risk_total``.
        """
        ordered = sorted(
            flags,
            key=lambda f: (f.volatility_delta, f.risk_total),
            reverse=True,
        )
        budget = self._tokens_today
        accepted = ordered[:budget]
        deferred = ordered[budget:]
        self._tokens_today = max(0, budget - len(accepted))
        return TokenBucketDecision(
            accepted=accepted,
            deferred=deferred,
            capacity_used=len(accepted),
            capacity_remaining=self._tokens_today,
        )


if __name__ == "__main__":
    import random
    random.seed(0)
    flags = [
        PatientFlag(
            patient_id=f"PT-{i:04d}",
            volatility_delta=random.uniform(0, 1),
            risk_total=random.uniform(0, 1),
            head=random.choice(("respiratory", "cardiovascular", "metabolic")),
        )
        for i in range(420)
    ]
    constrainer = TokenBucketConstrainer(panel_size=420, top_fraction=0.05)
    decision = constrainer.constrain(flags)
    print(f"  budget          : {constrainer.daily_budget()}")
    print(f"  accepted        : {decision.capacity_used} / deferred : {len(decision.deferred)}")
    print(f"  top-3 accepted  :")
    for f in decision.accepted[:3]:
        print(f"    {f.patient_id} Δ={f.volatility_delta:.3f} risk={f.risk_total:.3f} head={f.head}")
