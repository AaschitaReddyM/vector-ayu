"""Data-access helpers for VAYU's Supabase tables.

Thin wrappers around the service-role client so ``api/services.py`` stays
readable. Reads return domain objects (FHIR ``Patient``); writes accept the
plain values the pipeline already produces.

All functions raise on hard errors; callers that want the demo to survive a
transient DB problem should wrap writes in try/except (see services.py).
"""

from __future__ import annotations

from datetime import datetime, timezone, date

from pre_build.db import get_service_supabase
from pre_build.fhir.fhir_client import Patient


# ── Reads ──────────────────────────────────────────────────────────────────

def fetch_patients() -> list[Patient]:
    """Return all patients from Supabase as FHIR ``Patient`` objects."""
    client = get_service_supabase()
    resp = client.table("patients").select("*").order("id").execute()
    patients: list[Patient] = []
    for row in resp.data or []:
        patients.append(
            Patient(
                id=row["id"],
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
    client = get_service_supabase()
    q = client.table("risk_scores").select("*")
    if patient_id:
        q = q.eq("patient_id", patient_id)
    return q.order("scored_at", desc=True).limit(limit).execute().data or []


def fetch_triage_entries(
    patient_id: str | None = None,
    status: str | None = None,
    limit: int = 50,
) -> list[dict]:
    """Persisted triage decisions, newest first. Filter by patient and/or status."""
    client = get_service_supabase()
    q = client.table("triage_queue").select("*")
    if patient_id:
        q = q.eq("patient_id", patient_id)
    if status:
        q = q.eq("status", status)
    return q.order("created_at", desc=True).limit(limit).execute().data or []


def fetch_outreach_logs(patient_id: str | None = None, limit: int = 50) -> list[dict]:
    """Outreach audit log, newest first. Optionally filtered by patient."""
    client = get_service_supabase()
    q = client.table("outreach_logs").select("*")
    if patient_id:
        q = q.eq("patient_id", patient_id)
    return q.order("sent_at", desc=True).limit(limit).execute().data or []


# ── Writes ─────────────────────────────────────────────────────────────────

def save_risk_score(
    patient_id: str,
    probabilities: dict,
    climate_volatility_delta: dict,
    combined_delta: float,
    top_head: str,
    scored_at: datetime | None = None,
) -> dict:
    client = get_service_supabase()
    row = {
        "patient_id": patient_id,
        "probabilities": probabilities,
        "climate_volatility_delta": climate_volatility_delta,
        "combined_delta": combined_delta,
        "top_head": top_head,
        "scored_at": (scored_at or datetime.now(timezone.utc)).isoformat(),
    }
    return client.table("risk_scores").insert(row).execute().data


def save_triage_entry(
    patient_id: str,
    risk_total: float,
    head: str,
    status: str,
    triage_date: date | None = None,
) -> dict:
    client = get_service_supabase()
    row = {
        "patient_id": patient_id,
        "risk_total": risk_total,
        "head": head,
        "status": status,
        "triage_date": (triage_date or date.today()).isoformat(),
    }
    return client.table("triage_queue").insert(row).execute().data


def save_outreach_log(
    patient_id: str,
    track: str,
    message_content: str,
    sent_at: datetime | None = None,
) -> dict:
    client = get_service_supabase()
    row = {
        "patient_id": patient_id,
        "track": track,
        "message_content": message_content,
        "sent_at": (sent_at or datetime.now(timezone.utc)).isoformat(),
    }
    return client.table("outreach_logs").insert(row).execute().data
