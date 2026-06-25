from pydantic import BaseModel
from typing import List, Dict, Optional, Any

class ObservationSchema(BaseModel):
    id: str
    code: str
    display: str
    value: float
    unit: str
    effective_datetime: str
    category: str

class MedicationSchema(BaseModel):
    id: str
    medication_display: str
    rxnorm_code: str
    dosage_text: str
    status: str

class PatientSchema(BaseModel):
    id: str
    given_name: str
    family_name: str
    birth_date: str
    gender: str
    postal_code: str
    primary_language: str
    display_name: str

class PatientDetailResponse(BaseModel):
    patient: PatientSchema
    observations: List[ObservationSchema]
    medications: List[MedicationSchema]

class RiskForecast(BaseModel):
    probabilities: Dict[str, float]
    climate_volatility_delta: Dict[str, float]
    combined_delta: float
    top_head: str

class TriageQueueItem(BaseModel):
    patient_id: str
    volatility_delta: float
    risk_total: float
    head: str

class TriageDecisionResponse(BaseModel):
    accepted: List[TriageQueueItem]
    deferred: List[TriageQueueItem]
    capacity_used: int
    capacity_remaining: int

class RunPipelineResponse(BaseModel):
    patient: PatientSchema
    h3_cell: str
    indoor_proxy: bool
    shielding_coefficient: float
    risk: RiskForecast
    top_drivers: List[str]
    triage_rank: Optional[int]
    outreach_track: str
    fhir_note_id: str
