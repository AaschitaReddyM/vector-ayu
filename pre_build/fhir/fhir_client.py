"""
FHIR Client (Spec §6 — Fast Healthcare Interoperability Resources).

The platform queries the EHR for clean, repeatable arrays:

  • Patient — identity
  • Observation — clinical lab histories and historical vitals
  • MedicationRequest — prescription profiles

This module ships:
  1. Slim dataclasses matching FHIR R4 shape (only the fields we use).
  2. A protocol-style ``FhirClient`` interface.
  3. A ``MockFhirClient`` that yields realistic synthetic resources so the
     pipeline runs end-to-end without a live EHR.

Day 1 of the buildathon, swap ``MockFhirClient`` for a ``LiveFhirClient``
that hits ``{iss}/Patient/{id}`` etc. with the SMART bearer — the rest of
the codebase doesn't change.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


# ── FHIR R4 dataclasses (slim) ─────────────────────────────────────────────

@dataclass(frozen=True)
class Patient:
    id: str
    given_name: str
    family_name: str
    birth_date: str        # ISO 8601 (YYYY-MM-DD)
    gender: str            # "male" | "female" | "other" | "unknown"
    postal_code: str       # demographic ZIP — feeds H3 lookup when no geo consent
    primary_language: str = "en"

    @property
    def display_name(self) -> str:
        return f"{self.given_name} {self.family_name}"


@dataclass(frozen=True)
class Observation:
    id: str
    patient_id: str
    code: str              # LOINC code, e.g. "59408-5" (SpO2)
    display: str           # human label
    value: float
    unit: str
    effective_datetime: str  # ISO 8601
    category: str = "vital-signs"


@dataclass(frozen=True)
class MedicationRequest:
    id: str
    patient_id: str
    medication_display: str
    rxnorm_code: str
    dosage_text: str
    status: str = "active"


# ── Protocol ───────────────────────────────────────────────────────────────

class FhirClient(Protocol):
    def fetch_patient(self, patient_id: str) -> Patient: ...
    def fetch_observations(
        self,
        patient_id: str,
        category: str | None = None,
        limit: int = 50,
    ) -> list[Observation]: ...
    def fetch_medications(self, patient_id: str) -> list[MedicationRequest]: ...


# ── Mock implementation ────────────────────────────────────────────────────

@dataclass
class MockFhirClient:
    """Returns deterministic synthetic FHIR resources for demos."""
    seed_patients: dict[str, Patient] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.seed_patients:
            self.seed_patients = {p.id: p for p in _DEFAULT_PATIENTS}

    def fetch_patient(self, patient_id: str) -> Patient:
        if patient_id not in self.seed_patients:
            raise KeyError(f"patient {patient_id} not found")
        return self.seed_patients[patient_id]

    def fetch_observations(
        self,
        patient_id: str,
        category: str | None = None,
        limit: int = 50,
    ) -> list[Observation]:
        obs = _OBSERVATIONS_BY_PATIENT.get(patient_id, [])
        if category:
            obs = [o for o in obs if o.category == category]
        return obs[:limit]

    def fetch_medications(self, patient_id: str) -> list[MedicationRequest]:
        return list(_MEDS_BY_PATIENT.get(patient_id, []))


# ── Seed data ──────────────────────────────────────────────────────────────

_FIRST = ["Eleanor", "Maria", "James", "Aisha", "Robert", "Lin", "Carlos", "Patricia", "Devon", "Yusuf", "Hannah", "Marcus"]
_LAST = ["Vance", "Hernandez", "Okonkwo", "Patel", "Chen", "Rodriguez", "Williams", "Nguyen", "Brooks", "Al-Sayed", "Johnson", "Reyes"]

_DEFAULT_PATIENTS: list[Patient] = []
for i in range(12):
    _DEFAULT_PATIENTS.append(Patient(
        id=f"PT-{i+1:04d}",
        given_name=_FIRST[i],
        family_name=_LAST[i],
        birth_date=f"19{40+i}-0{(i%9)+1}-1{i%9}",
        gender="male" if i % 3 == 0 else "female",
        postal_code=f"752{i:02d}",
        primary_language="es" if i % 4 == 0 else "en"
    ))

_OBSERVATIONS_BY_PATIENT: dict[str, list[Observation]] = {
    "PT-0001": [
        Observation(id="OBS-1-1", patient_id="PT-0001",
                    code="59408-5", display="SpO2 (pulse ox)", value=92.0,
                    unit="%", effective_datetime="2026-05-28T08:15:00-05:00"),
        Observation(id="OBS-1-2", patient_id="PT-0001",
                    code="8867-4", display="Heart rate", value=88.0,
                    unit="bpm", effective_datetime="2026-05-28T08:15:00-05:00"),
        Observation(id="OBS-1-3", patient_id="PT-0001",
                    code="2339-0", display="Glucose (fasting)", value=148.0,
                    unit="mg/dL", effective_datetime="2026-05-25T07:00:00-05:00",
                    category="laboratory"),
    ],
    "PT-0002": [
        Observation(id="OBS-2-1", patient_id="PT-0002",
                    code="8480-6", display="Systolic BP", value=148.0,
                    unit="mmHg", effective_datetime="2026-05-27T17:42:00-05:00"),
        Observation(id="OBS-2-2", patient_id="PT-0002",
                    code="8462-4", display="Diastolic BP", value=92.0,
                    unit="mmHg", effective_datetime="2026-05-27T17:42:00-05:00"),
    ],
    "PT-0003": [
        Observation(id="OBS-3-1", patient_id="PT-0003",
                    code="2339-0", display="Glucose (fasting)", value=132.0,
                    unit="mg/dL", effective_datetime="2026-05-26T07:30:00-05:00",
                    category="laboratory"),
    ],
}

_MEDS_BY_PATIENT: dict[str, list[MedicationRequest]] = {
    "PT-0001": [
        MedicationRequest(id="MR-1-1", patient_id="PT-0001",
                          medication_display="Albuterol HFA inhaler",
                          rxnorm_code="329498", dosage_text="2 puffs q4h prn"),
        MedicationRequest(id="MR-1-2", patient_id="PT-0001",
                          medication_display="Metformin 1000 mg",
                          rxnorm_code="860975", dosage_text="1 tab BID"),
    ],
    "PT-0002": [
        MedicationRequest(id="MR-2-1", patient_id="PT-0002",
                          medication_display="Lisinopril 20 mg",
                          rxnorm_code="314076", dosage_text="1 tab daily"),
        MedicationRequest(id="MR-2-2", patient_id="PT-0002",
                          medication_display="Atorvastatin 40 mg",
                          rxnorm_code="617314", dosage_text="1 tab qhs"),
    ],
}


if __name__ == "__main__":
    client = MockFhirClient()
    p = client.fetch_patient("PT-0001")
    print(f"  patient : {p.display_name}  dob={p.birth_date}  zip={p.postal_code}")
    for o in client.fetch_observations("PT-0001"):
        print(f"  obs     : {o.display:25s} = {o.value} {o.unit}  ({o.effective_datetime})")
    for m in client.fetch_medications("PT-0001"):
        print(f"  med     : {m.medication_display:35s} dose='{m.dosage_text}'")
