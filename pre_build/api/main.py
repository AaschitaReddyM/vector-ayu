from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional

from pre_build.api.schemas import (
    PatientSchema, PatientDetailResponse, RunPipelineResponse,
    TriageDecisionResponse, SimulationOverrides,
    RiskScoreRecord, TriageRecord, OutreachLogRecord
)
from pre_build.api.services import (
    get_all_patients, get_patient_detail, run_patient_pipeline, get_triage_queue, run_autonomous_cron, reset_triage_and_set_region
)
from pre_build.db import repository

app = FastAPI(title="VAYU Predictive Triage API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/patients", response_model=List[PatientSchema])
def list_patients():
    """Retrieve a list of all mock patients."""
    patients = get_all_patients()
    return [p.__dict__ | {"display_name": p.display_name} for p in patients]

@app.get("/api/patients/{patient_id}", response_model=PatientDetailResponse)
def patient_details(patient_id: str):
    """Retrieve details, observations, and medications for a specific patient."""
    try:
        patient, obs, meds = get_patient_detail(patient_id)
        return {
            "patient": patient.__dict__ | {"display_name": patient.display_name},
            "observations": [o.__dict__ for o in obs],
            "medications": [m.__dict__ for m in meds]
        }
    except KeyError:
        raise HTTPException(status_code=404, detail="Patient not found")

@app.post("/api/pipeline/run/{patient_id}", response_model=RunPipelineResponse)
def trigger_pipeline(patient_id: str, anomaly_type: Optional[str] = None, overrides: Optional[SimulationOverrides] = None):
    """Run the VAYU 7-stage pipeline for a given patient."""
    try:
        return run_patient_pipeline(patient_id, anomaly_type, overrides)
    except KeyError:
        raise HTTPException(status_code=404, detail="Patient not found")

@app.get("/api/triage/queue", response_model=TriageDecisionResponse)
def triage_queue():
    """Get the token-bucket constrained triage queue."""
    decision = get_triage_queue()
    return {
        "accepted": [f.__dict__ for f in decision.accepted],
        "deferred": [f.__dict__ for f in decision.deferred],
        "capacity_used": decision.capacity_used,
        "capacity_remaining": decision.capacity_remaining
    }

from pydantic import BaseModel
class SessionRequest(BaseModel):
    region: str

@app.post("/api/session")
def set_session(req: SessionRequest):
    """Reset the mock triage flags and set the region (dallas or new_delhi)"""
    reset_triage_and_set_region(req.region)
    return {"status": "ok", "region": req.region}

@app.post("/api/cron/scan-climate")
def trigger_autonomous_cron(anomaly_type: Optional[str] = None):
    """Simulate a Google Cloud Scheduler hitting this endpoint every hour."""
    try:
        return run_autonomous_cron(anomaly_type)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Plan-named convenience aliases (thin wrappers over the same service layer).
# These match the route names referenced by the `version 1/` frontend plan:
#   GET /patients, GET /risk-scores, GET /triage-queue
# No duplicated logic — they delegate to the handlers/services above.
# The risk-scores pipeline remains DYNAMIC (Stages 1-7 run per request).
# ---------------------------------------------------------------------------

@app.get("/patients", response_model=List[PatientSchema])
async def list_patients_alias():
    """Alias of GET /api/patients."""
    return await list_patients()


@app.get("/risk-scores", response_model=RunPipelineResponse)
async def risk_scores_alias(patient_id: str):
    """Alias for the dynamic pipeline run. Pass ?patient_id=PT-0001.

    Runs Stages 1-4 (EHR fetch, exposure attenuation, TFT inference,
    climate volatility delta) plus triage/XAI/outreach, live per request.
    """
    try:
        return run_patient_pipeline(patient_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Patient not found")


@app.get("/triage-queue", response_model=TriageDecisionResponse)
async def triage_queue_alias():
    """Alias of GET /api/triage/queue."""
    return await triage_queue()


# ---------------------------------------------------------------------------
# History reads — pull stored records back out of Supabase for the frontend.
# All are newest-first and accept an optional ?patient_id= filter.
# ---------------------------------------------------------------------------

@app.get("/history/risk-scores", response_model=List[RiskScoreRecord])
async def history_risk_scores(patient_id: Optional[str] = None, limit: int = 50):
    """Stored risk-score forecasts. Filter with ?patient_id=PT-0001."""
    return repository.fetch_risk_scores(patient_id, limit)


@app.get("/history/triage", response_model=List[TriageRecord])
async def history_triage(
    patient_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
):
    """Persisted triage decisions. Filter by ?patient_id= and/or ?status=."""
    return repository.fetch_triage_entries(patient_id, status, limit)


@app.get("/history/outreach", response_model=List[OutreachLogRecord])
async def history_outreach(patient_id: Optional[str] = None, limit: int = 50):
    """Outreach audit log. Filter with ?patient_id=PT-0001."""
    return repository.fetch_outreach_logs(patient_id, limit)
