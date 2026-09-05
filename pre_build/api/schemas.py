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
    has_smart_home: bool = False

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

class DriverSchema(BaseModel):
    label: str
    stream: str
    value: float

class RunPipelineResponse(BaseModel):
    patient: PatientSchema
    h3_cell: str
    indoor_proxy: bool
    shielding_coefficient: float
    risk: RiskForecast
    top_drivers: List[DriverSchema]
    triage_rank: Optional[int]
    outreach_track: str
    fhir_note_id: str
    drafted_sms: Optional[str] = None
    iot_shielding: Optional[Dict[str, Any]] = None


class SimulationOverrides(BaseModel):
    spo2: Optional[float] = None
    systolic_bp: Optional[float] = None
    custom_aqi: Optional[int] = None

# ── Stored-record schemas (history reads straight from Supabase) ────────────

class RiskScoreRecord(BaseModel):
    id: str
    patient_id: str
    probabilities: Optional[Dict[str, float]] = None
    climate_volatility_delta: Optional[Dict[str, float]] = None
    combined_delta: Optional[float] = None
    top_head: Optional[str] = None
    scored_at: Optional[str] = None
    created_at: Optional[str] = None

class TriageRecord(BaseModel):
    id: str
    patient_id: str
    risk_total: Optional[float] = None
    head: Optional[str] = None
    status: str
    triage_date: Optional[str] = None
    created_at: Optional[str] = None

class OutreachLogRecord(BaseModel):
    id: str
    patient_id: str
    track: Optional[str] = None
    message_content: Optional[str] = None
    sent_at: Optional[str] = None
    created_at: Optional[str] = None
