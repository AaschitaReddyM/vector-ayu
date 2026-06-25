from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List

from pre_build.api.schemas import (
    PatientSchema, PatientDetailResponse, RunPipelineResponse,
    TriageDecisionResponse
)
from pre_build.api.services import (
    get_all_patients, get_patient_detail, run_patient_pipeline, get_triage_queue
)

app = FastAPI(title="VAYU Predictive Triage API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/patients", response_model=List[PatientSchema])
async def list_patients():
    """Retrieve a list of all mock patients."""
    patients = get_all_patients()
    return [p.__dict__ | {"display_name": p.display_name} for p in patients]

@app.get("/api/patients/{patient_id}", response_model=PatientDetailResponse)
async def patient_details(patient_id: str):
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
async def trigger_pipeline(patient_id: str):
    """Run the VAYU 7-stage pipeline for a given patient."""
    try:
        return run_patient_pipeline(patient_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Patient not found")

@app.get("/api/triage/queue", response_model=TriageDecisionResponse)
async def triage_queue():
    """Get the token-bucket constrained triage queue."""
    decision = get_triage_queue()
    return {
        "accepted": [f.__dict__ for f in decision.accepted],
        "deferred": [f.__dict__ for f in decision.deferred],
        "capacity_used": decision.capacity_used,
        "capacity_remaining": decision.capacity_remaining
    }


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
