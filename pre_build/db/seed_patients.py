"""Seed the Supabase ``patients`` table from MockFhirClient synthetic data.

Usage (from the project root, with a populated .env):

    python -m pre_build.db.seed_patients

Uses the service-role client so it can write regardless of RLS. Idempotent —
re-running upserts on the primary key ('PT-0001', ...) instead of duplicating.
"""

from __future__ import annotations

from pre_build.db import get_service_supabase
from pre_build.fhir.fhir_client import MockFhirClient, Patient


def patient_to_row(p: Patient) -> dict:
    return {
        "id": p.id,                          # text PK, e.g. 'PT-0001'
        "given_name": p.given_name,
        "family_name": p.family_name,
        "birth_date": p.birth_date,
        "gender": p.gender,
        "postal_code": p.postal_code,
        "primary_language": p.primary_language,
    }


def main() -> None:
    client = get_service_supabase()
    fhir = MockFhirClient()

    rows = [patient_to_row(p) for p in fhir.seed_patients.values()]
    resp = client.table("patients").upsert(rows, on_conflict="id").execute()

    seeded = resp.data or []
    print(f"Seeded {len(seeded)} patient(s) into Supabase:")
    for r in seeded:
        print(f"  {r['id']}  {r.get('given_name', '')} {r.get('family_name', '')}")


if __name__ == "__main__":
    main()
