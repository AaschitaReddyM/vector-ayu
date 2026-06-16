# VAYU — Improvements for Later (Post-Buildathon Roadmap)

This document outlines high-impact technical, clinical, and architectural improvements to transition VAYU from a high-fidelity prototype to a production-grade clinical triage platform.

---

## 🧠 1. Model Architecture & ML Enhancements

### 1.1 Multi-Horizon Risk Trajectories
* **Current**: The TFT skeleton predicts a single scalar risk score representing the cumulative probability of an acute event in the next 72 hours.
* **Later**: Train the model to output a step-by-step forecast vector ($t_1$ through $t_{72}$). This allows the clinician dashboard to plot a continuous, hourly-resolved risk trajectory curve for each patient, highlighting the exact hour risk peaks.

### 1.2 Quantile Loss Prediction
* **Current**: Task heads output point-estimates for binary classification.
* **Later**: Transition from standard BCE loss to multi-quantile loss (e.g., 10th, 50th, 90th percentiles). This quantifies predictive uncertainty, allowing clinical teams to distinguish between high-confidence risk spikes and high-variance baseline swings.

### 1.3 Uncertainty-Weighted Multi-Task Loss
* **Current**: Loss weights for the 3 heads are statically defined ($\alpha=1.0$, $\beta=5.0$, $\gamma=2.0$).
* **Later**: Implement homoscedastic uncertainty loss weight scaling (Kendall et al.). This dynamically adjusts the task weights during gradient descent based on the relative task noise, preventing one dominant head from stalling convergence on the others.

### 1.4 Swapping to Full PyTorch-Forecasting
* **Current**: Custom lightweight PyTorch skeleton designed for CPU/MPS speed and shape-stability.
* **Later**: Swap the backend skeleton with `pytorch_forecasting.TemporalFusionTransformer` to gain native support for complex covariate types (static categoricals, time-varying knowns, time-varying unknowns) and built-in visualization tools for attention weights.

---

## 🌐 2. Data Engineering & Exposure Modeling

### 2.1 Machine-Learned Indoor Shielding Coefficient (SC)
* **Current**: SC is computed via a weighted rule-based formula based on static local ZIP code statistics.
* **Later**: Train a Gradient-Boosted Regressor (XGBoost/CatBoost) on FEMA HAZUS and Census American Community Survey (ACS) datasets to predict a patient's shielding coefficient based on building age, material composition, canopy coverage, and central HVAC distributions.

### 2.2 Live Geofencing & Telemetry
* **Current**: Pipeline relies on the patient's billing ZIP code centroid for spatiotemporal matching.
* **Later**: Integrate live, privacy-safe GPS telemetry (e.g., geohashed location buckets from a patient-facing mobile application). This ensures that if a patient travels outside of a wildfire smoke plume (e.g., for work), their exposure metrics update dynamically to prevent alert fatigue.

### 2.3 Indoor Air Quality Sensor Fusion
* **Current**: Indoor proxy is purely modeled via software signals (GPS, Wi-Fi connectivity, steps).
* **Later**: Fuse real-time indoor air quality measurements from consumer smart-home devices (e.g., PurpleAir, Ecobee, Dyson API) directly into the attenuation equation when available.

---

## 🏥 3. FHIR & Clinical Workflow Integration

### 3.1 SMART-on-FHIR Observation Ingestion
* **Current**: Ingests static mock observations (3 seed patients).
* **Later**: Implement query parameterization to fetch full historical labs (e.g., HbA1c observations, FEV1 spirometry reports, cardiac panels) from the host EHR, automatically converting raw values into normalized z-score inputs for the TFT.

### 3.2 CDS Hooks Integration
* **Current**: Standalone provider dashboard.
* **Later**: Integrate VAYU alerts directly into the EHR chart using **CDS Hooks** (e.g., a `patient-view` hook that displays the VAYU climate risk banner directly inside Epic/Cerner when a clinician opens a patient's chart, suggesting preventative inhaler updates).

---

## 💬 4. Conversational & Agentic Outreach

### 4.1 Two-Way RAG Outreach Agent
* **Current**: Proactive, bilingual templates rendered with custom alert text.
* **Later**: Wire the outreach endpoint to a Large Language Model (LLM) equipped with Retrieval-Augmented Generation (RAG). Patients who receive an SMS warning can reply with questions (e.g., *"Where can I get a HEPA filter?"* or *"Should I double my dosage?"*), and the agent will reply with safe, clinical-guardrail-enforced guidance drawing from CDC and clinical guidelines.

### 4.2 Voice Call Telephony (CallFort / Retell AI)
* **Current**: Deferred Track B patients are added to a decorative manual call queue.
* **Later**: Integrate a conversational Voice AI agent that automatically calls Track B patients who require manual follow-up. The agent checks for symptoms, transcripts the conversation, extracts clinical keywords, and writes the summary directly back to the EHR progress note.

---

## 🛠️ 5. MLOps & Production Engineering

### 5.1 Model Drift & Climate Shift Monitoring
* **Current**: No model tracking.
* **Later**: Implement data drift monitors (e.g., Evidently AI) to check if ambient climate inputs (like summer heatwaves exceeding 110°F) drift away from the historical Dallas EPA data used during pre-training, triggering alert flags for model retraining.

### 5.2 Structured Logging & Observability
* **Current**: Simple terminal print statements.
* **Later**: Implement OpenTelemetry and structured JSON logging. Export metrics (model inference latency, token-bucket deferrals, SMS click-rates) to Prometheus/Grafana or Datadog for system-wide health observability.
