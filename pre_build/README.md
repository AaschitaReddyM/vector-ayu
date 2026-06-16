# ClimaHealth — Backend Pipeline Core (`pre_build`)

This directory houses the 7-stage Python pipeline that ingests EHR patient profiles, maps them spatiotemporally to environmental exposures, runs risk predictions, triage gates notifications, calculates explainability drivers, and triggers proactive outreach.

---

## 📂 Directory Structure & Module Guide

| Directory / Module | Key Files | Stage | Role |
| :--- | :--- | :--- | :--- |
| **`fhir/`** | `fhir_client.py`, `progress_note.py`, `smart_oauth.py` | Stage 1 & 7 | Handles SMART-on-FHIR client auth, mock patient observations, and LOINC progress note write-back. |
| **`spatial/`** | `h3_ingestion.py`, `texas_zip_centroids.py` | Stage 2 | Hashes coordinates/ZIP codes into H3 Hex indices (resolution 7) to join with location-based climate forecasts. |
| **`exposure/`** | `attenuation.py`, `indoor_proxy.py`, `shielding_coefficient.py` | Stage 3 | Classifies indoor/outdoor status and applies ZIP canopy/building-envelope attenuation coefficients. |
| **`model/`** | `tft_skeleton.py`, `multitask_loss.py`, `catboost_fallback.py`, `train_tft.py` | Stage 4 | **Core AI Engine**: Contains the Temporal Fusion Transformer architecture, CatBoost fallback ensemble, and PyTorch MPS-optimized training loops. |
| **`triage/`** | `token_bucket.py`, `volatility_delta.py` | Stage 5 | Daily token-bucket constrainer sorting alerts by environmental risk delta to match clinic staff capacity. |
| **`explain/`** | `attributions.py`, `channel_labels.py`, `export_for_dashboard.py` | Stage 6 | Performs Captum Integrated Gradients (IG) backpropagation to extract and output top environmental drivers. |
| **`consent/`** | `dual_track.py` | Stage 7 | Gated routing deciding whether patients receive auto-SMS alerts (Track A) or manual calls (Track B). |
| **`outreach/`** | `sms_template.py` | Stage 7 | Renders billing-safe bilingual proactive health advisories for high-risk climate events. |

---

## ⚙️ Dependencies

Ensure you install all backend requirements using:
```bash
python3 -m pip install -r requirements.txt
```
*Note: If you are using a Homebrew or system-managed Python on macOS and receive an environment block error, you can use:*
```bash
python3 -m pip install --user --break-system-packages -r requirements.txt
```

---

## 🏃 Execution Commands

Run all scripts from the workspace root directory:

### Run the Demo Pipeline (Ingestion through Outreach)
```bash
python3 -m pre_build.demo_pipeline
```

### Run Model Training (calibrating weights on synthetic data)
```bash
python3 -m pre_build.model.train_tft
```

### Run Integrated Gradients Attribution & Export Dashboard JSON
```bash
python3 -m pre_build.explain.export_for_dashboard --engine ig
```

### Run the Full Verification Smoke Tests
```bash
python3 -m pre_build.smoke_test
```
