"""Data-access helpers for VAYU's Firestore collections.

Replaces the old Supabase implementation.
"""

from __future__ import annotations

from datetime import datetime, timezone, date

from pre_build.db.firestore_client import get_firestore_client
from pre_build.fhir.fhir_client import Patient


# ── Reads ──────────────────────────────────────────────────────────────────

def fetch_patients() -> list[Patient]:
    """Return all patients from Firestore as FHIR ``Patient`` objects."""
    db = get_firestore_client()
    docs = db.collection("patients").stream()
    patients: list[Patient] = []
    for doc in docs:
        row = doc.to_dict()
        patients.append(
            Patient(
                id=doc.id,
                given_name=row.get("given_name") or "",
                family_name=row.get("family_name") or "",
                birth_date=row.get("birth_date") or "",
                gender=row.get("gender") or "unknown",
                postal_code=row.get("postal_code") or "",
                primary_language=row.get("primary_language") or "en",
            )
        )
    return patients


def fetch_risk_scores(patient_id: str | None = None, limit: int = 50) -> list[dict]:
    """Stored risk scores, newest first. Optionally filtered by patient."""
    db = get_firestore_client()
    query = db.collection("risk_scores").order_by("scored_at", direction=firestore.Query.DESCENDING).limit(limit)
    if patient_id:
        query = query.where("patient_id", "==", patient_id)
    return [doc.to_dict() for doc in query.stream()]


def fetch_triage_entries(
    patient_id: str | None = None,
    status: str | None = None,
    limit: int = 50,
) -> list[dict]:
    """Persisted triage decisions, newest first. Filter by patient and/or status."""
    db = get_firestore_client()
    query = db.collection("triage_queue").order_by("created_at", direction=firestore.Query.DESCENDING).limit(limit)
    if patient_id:
        query = query.where("patient_id", "==", patient_id)
    if status:
        query = query.where("status", "==", status)
    return [doc.to_dict() for doc in query.stream()]


def fetch_outreach_logs(patient_id: str | None = None, limit: int = 50) -> list[dict]:
    """Outreach audit log, newest first. Optionally filtered by patient."""
    db = get_firestore_client()
    query = db.collection("outreach_logs").order_by("sent_at", direction=firestore.Query.DESCENDING).limit(limit)
    if patient_id:
        query = query.where("patient_id", "==", patient_id)
    return [doc.to_dict() for doc in query.stream()]


# ── Writes ─────────────────────────────────────────────────────────────────

def save_risk_score(
    patient_id: str,
    probabilities: dict,
    climate_volatility_delta: dict,
    combined_delta: float,
    top_head: str,
    scored_at: datetime | None = None,
) -> dict:
    db = get_firestore_client()
    row = {
        "patient_id": patient_id,
        "probabilities": probabilities,
        "climate_volatility_delta": climate_volatility_delta,
        "combined_delta": combined_delta,
        "top_head": top_head,
        "scored_at": (scored_at or datetime.now(timezone.utc)).isoformat(),
    }
    _, ref = db.collection("risk_scores").add(row)
    return row


def save_triage_entry(
    patient_id: str,
    risk_total: float,
    head: str,
    status: str,
    triage_date: date | None = None,
) -> dict:
    db = get_firestore_client()
    row = {
        "patient_id": patient_id,
        "risk_total": risk_total,
        "head": head,
        "status": status,
        "triage_date": (triage_date or date.today()).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    _, ref = db.collection("triage_queue").add(row)
    return row


def save_outreach_log(
    patient_id: str,
    track: str,
    message_content: str,
    sent_at: datetime | None = None,
) -> dict:
    db = get_firestore_client()
    row = {
        "patient_id": patient_id,
        "track": track,
        "message_content": message_content,
        "sent_at": (sent_at or datetime.now(timezone.utc)).isoformat(),
    }
    _, ref = db.collection("outreach_logs").add(row)
    return row
