"""
FHIR Progress Note Ledger Encapsulation (Spec §5 row 4 — *Provider Legal
Malpractice Liability*).

When a clinician approves a flag, the system fires a FHIR write-back payload
that documents the preventative outreach directly inside the native EHR
chart as a legal shield: "we showed you, you acted, here is the artifact".

We use a FHIR R4 ``DocumentReference`` resource — the canonical container
for non-Observation clinical documents. The note body is a base64-encoded
plain-text narrative; production setups may swap for a structured
``Composition`` resource with sections.
"""

from __future__ import annotations

import base64
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class RiskSummary:
    patient_id: str
    head: str                       # "respiratory" | "cardiovascular" | "metabolic"
    volatility_delta: float
    forecast_probability: float
    horizon_hours: int
    top_drivers: list[str]          # XAI bullets — top SHAP/IG channels


def build_progress_note(
    *,
    summary: RiskSummary,
    recommendations: list[str],
    clinician_id: str,
    approved_at: datetime | None = None,
) -> dict:
    """Return a FHIR R4 ``DocumentReference`` resource ready to POST."""
    approved_at = approved_at or datetime.now(timezone.utc)
    narrative = _render_narrative(summary, recommendations, clinician_id, approved_at)
    encoded = base64.b64encode(narrative.encode("utf-8")).decode("ascii")

    return {
        "resourceType": "DocumentReference",
        "id": str(uuid.uuid4()),
        "status": "current",
        "docStatus": "final",
        "type": {
            "coding": [{
                "system": "http://loinc.org",
                "code": "11488-4",            # Consult note (preventive)
                "display": "Consult note",
            }],
        },
        "category": [{
            "coding": [{
                "system": "http://hl7.org/fhir/us/core/CodeSystem/us-core-documentreference-category",
                "code": "clinical-note",
            }],
        }],
        "subject": {"reference": f"Patient/{summary.patient_id}"},
        "date": approved_at.isoformat(),
        "author": [{"reference": f"Practitioner/{clinician_id}"}],
        "description": (
            f"ClimaHealth proactive outreach — {summary.head} risk "
            f"Δ={summary.volatility_delta:.2f} over {summary.horizon_hours}h horizon"
        ),
        "content": [{
            "attachment": {
                "contentType": "text/plain",
                "data": encoded,
                "title": "ClimaHealth Preventive Outreach Note",
            },
        }],
        "context": {
            "related": [{
                "identifier": {
                    "system": "https://climahealth.app/alert-id",
                    "value": f"alert-{summary.patient_id}-{summary.head}-{int(approved_at.timestamp())}",
                },
            }],
        },
    }


def _render_narrative(
    summary: RiskSummary,
    recommendations: list[str],
    clinician_id: str,
    approved_at: datetime,
) -> str:
    drivers = "\n  ".join(f"• {d}" for d in summary.top_drivers) or "  (none recorded)"
    recs = "\n  ".join(f"• {r}" for r in recommendations) or "  (none recorded)"
    return (
        "ClimaHealth Proactive Preventive Outreach\n"
        "=========================================\n"
        f"Approved by: Practitioner/{clinician_id}\n"
        f"Approved at: {approved_at.isoformat()}\n"
        f"Patient:     Patient/{summary.patient_id}\n"
        f"Head:        {summary.head}\n"
        f"Δ Volatility:  {summary.volatility_delta:.3f}\n"
        f"P({summary.head} acute, {summary.horizon_hours}h): {summary.forecast_probability:.3f}\n\n"
        "Top model drivers (Integrated Gradients):\n"
        f"  {drivers}\n\n"
        "Approved actions:\n"
        f"  {recs}\n"
    )


if __name__ == "__main__":
    summary = RiskSummary(
        patient_id="PT-0001",
        head="respiratory",
        volatility_delta=0.34,
        forecast_probability=0.62,
        horizon_hours=72,
        top_drivers=[
            "Outdoor PM2.5 forecast 78 µg/m³ vs seasonal 22 µg/m³",
            "Patient SC=0.51 (older housing, limited HVAC)",
            "Recent SpO2 drift 96→92 over past 14d",
        ],
    )
    note = build_progress_note(
        summary=summary,
        recommendations=[
            "Send 48h preventive SMS in Spanish — stay indoors during peak ozone.",
            "Schedule telehealth check on 2026-05-31 if symptoms emerge.",
        ],
        clinician_id="PR-7791",
    )
    import json
    print(json.dumps(note, indent=2)[:900])
