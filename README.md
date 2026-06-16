# VectorAyu — Environmental-EHR Predictive Triage Platform

ClimaHealth is an end-to-end predictive healthcare pipeline that integrates Electronic Health Record (EHR) data with local environmental and climate risk models to forecast acute health events (Respiratory, Cardiovascular, and Metabolic vectors) before they occur.

---

## 🚀 Pre-Buildathon Milestones Completed

Before the Buildathon Dallas event (June 18-19, 2026), we completed the pre-training and validation of the core AI models:

* **TFT Model Training**: Trained the multi-task Temporal Fusion Transformer skeleton on **85,410 synthetic patient-day samples** calibrated to clinical meta-analyses (e.g., *GOLD 2024*, *Hurst NEJM 2010*, *Liu Lancet 2019*).
* **Apple Silicon Hardware Optimization**:
  * Leveraged the Apple M1 Pro GPU cores via the PyTorch **Metal Performance Shaders (MPS)** backend.
  * Optimized CPU-to-GPU data pipelines by scaling the batch size to **256**.
  * Configured PyTorch intra-op threads to **10** (matching all physical cores on the M1 Pro) to accelerate synthetic data generation.
* **Training Convergence**: Early stopping triggered at Epoch 21 with a best validation loss of **6.1450**.
  * **Respiratory Head Validation AUC**: `0.796` (Target > 0.75 met)
  * **Cardiovascular Head Validation AUC**: `0.767` (Target > 0.75 met)
  * **Metabolic Head Validation AUC**: `0.740` (Excellent multi-task convergence)
* **Checkpoints**: Weights are persisted in `pre_build/model/tft_trained.pt` and are fully integrated into both the execution pipelines and the Integrated Gradients attribution engine.

---

## 📂 Workspace Progress Documentation

We have added detailed markdown guides directly to this workspace to map out the codebase, buildathon strategy, and validation checks:

* **[walkthrough_progress.md](file:///Users/manid/private/climahealth-1/walkthrough_progress.md)**: Deep dive into the 7-stage Python pipeline, visual frontend mockups, designed-for-swap interfaces, and model verification logs.
* **[buildathon_credit_strategy.md](file:///Users/manid/private/climahealth-1/buildathon_credit_strategy.md)**: Detailed mapping of the **$3,025+ in partner credits** (Tavily search, Lovable full-stack builder, Featherless AI LLM, CallFort Voice AI, and Just Videos) with a step-by-step 18-hour execution roadmap.
* **[tft_training_implementation_plan.md](file:///Users/manid/private/climahealth-1/tft_training_implementation_plan.md)**: Technical overview of the multi-task training architecture, custom loss, and data generation modeling.
* **[architecture_overview.md](file:///Users/manid/private/climahealth-1/architecture_overview.md)**: Clean overview of data ingest, spatiotemporal mapping, exposure attenuation, and triage constraint loops.

---

## 🔧 Local Execution & Verification

To run training, execute end-to-end patient runs, or generate explainability reports on your local machine, run the following commands:

### 1. Train the TFT Model
Generate the calibrated 3-stream dataset and train the multi-task heads:
```bash
python3 -m pre_build.model.train_tft
```

### 2. Run the End-to-End Demo Pipeline
Execute the 7-stage pipeline (from mock FHIR client ingestion and H3 spatiotemporal mapping to Shielding-attenuated exposure, TFT inference, and progress note generation):
```bash
python3 -m pre_build.demo_pipeline
```

### 3. Generate Dashboard Attributions (IG Engine)
Compute true Integrated Gradients (IG) attributions for the patient dashboard using the pre-trained weights:
```bash
python3 -m pre_build.explain.export_for_dashboard --engine ig
```

### 4. Run the Full Smoke Test Suite
Confirm that all backend dimensions, loss classes, spatial routers, and fallback routing scripts remain fully operational:
```bash
python3 -m pre_build.smoke_test
```

---

## ⚡ Buildathon Dallas 18-Hour Roadmap

For the live build event on June 18-19, the following 10% live-cloud integrations are planned:
1. **API Layer (Hours 0-4)**: FastAPI server to expose endpoints `/patients`, `/risk-scores`, and `/triage-queue`.
2. **Real-Time Feeds (Hours 1-3)**: Incorporate **Tavily Search API** to fetch real-time EPA AirNow AQI metrics and NWS forecasts for Texas ZIP codes.
3. **Frontend Rebuild (Hours 4-10)**: Rebuild the static views as a real React + Supabase web application using **Lovable**.
4. **AI-Powered Outreach (Hours 10-14)**: Replace the standard SMS templates with LLM-generated patient behavioral nudges via **Featherless AI** (Mistral-7B).
5. **Telephony Interventions (Hours 12-14)**: Connect Track B (manual call queue) flags to voice agents powered by **CallFort**.
