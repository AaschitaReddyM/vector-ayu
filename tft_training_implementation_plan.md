# TFT Model Training Plan — Pre-Buildathon (June 16–17)

> [!NOTE]
> Train the TFT skeleton with epidemiologically-calibrated synthetic data before the event so it produces **clinically meaningful predictions** instead of random outputs.

---

## The Situation

| What Exists | Status |
|-------------|--------|
| TFT architecture ([tft_skeleton.py](file:///Users/manid/private/climahealth-1/pre_build/model/tft_skeleton.py)) | ✅ Complete — GRN, Variable Selection, LSTM, Multi-head Attention, 3 task heads |
| Multi-task loss ([multitask_loss.py](file:///Users/manid/private/climahealth-1/pre_build/model/multitask_loss.py)) | ✅ Complete — α=1.0, β=5.0, γ=2.0 weighted BCE |
| CatBoost fallback ([catboost_fallback.py](file:///Users/manid/private/climahealth-1/pre_build/model/catboost_fallback.py)) | ✅ Complete — trains in seconds |
| Synthetic data generation ([option1_real_aqi_ablation.py](file:///Users/manid/private/climahealth-1/ablation_study/option1_real_aqi_ablation.py)) | ✅ Complete — 2,847 patients, EPA-calibrated AQI, published effect sizes |
| Brief calibration pass ([export_for_dashboard.py](file:///Users/manid/private/climahealth-1/pre_build/explain/export_for_dashboard.py) `_calibrate_model()`) | ✅ Exists — 25 epochs, 1,024 samples (too small for real training) |
| Model weights | ✅ Trained & Calibrated |
| Real EHR data | ❌ **None** — no access to patient records |

---

## Proposed Changes

### [train_tft.py](file:///Users/manid/private/climahealth-1/pre_build/model/train_tft.py)

A complete training script that:

1. **Generates 3-stream TFT training data** — adapts the ablation study's patient generator to produce `(static, clinical_temporal, environmental_temporal)` tensors matching the TFT's exact input contract
2. **Trains with proper ML rigor** — train/val split, early stopping, learning rate scheduling, gradient clipping
3. **Multi-task loss** — uses the existing `MultiTaskLoss` with α/β/γ priority knobs
4. **Saves checkpoint** — `pre_build/model/tft_trained.pt` (weights + config)
5. **Logs metrics** — per-head AUC, loss curves, best validation metrics

#### Data Generation Strategy

Reuse the ablation study's epidemiological model but reshape for the TFT's 3-stream input:

| TFT Input | Shape | Source |
|-----------|-------|--------|
| `static_x` | `(N, 16)` | Age, sex, COPD stage, FEV1%, smoking, comorbidities, shielding, etc. — from ablation's patient generator |
| `temporal_clinical_x` | `(N, 72, 12)` | Synthetic SpO2, HR, HRV, BP, glucose, respiratory rate — with clinically-realistic temporal trends |
| `temporal_environmental_x` | `(N, 72, 8)` | PM2.5, ozone, AQI, pollen, temp, humidity, UV, wind — from the ablation's EPA-calibrated distributions |
| Labels | `dict{head: (N,)}` | Binary exacerbation per head — from the ablation's logistic outcome model extended to 3 heads |

#### Training Configuration

```python
# Matches the existing TFTConfig defaults
static_input_dim:        16
clinical_input_dim:      12
environmental_input_dim: 8
horizon_hours:           72
hidden_dim:              64
lstm_layers:             2
attn_heads:              4
dropout:                 0.1

# Training hyperparameters
n_patients:              2847      # match dashboard
n_days_per_patient:      30        # 30 monitoring windows each
batch_size:              256       # optimized for Apple M1 Pro GPU cores
learning_rate:           1e-3      # with cosine annealing
weight_decay:            1e-4
early_stopping_patience: 8
gradient_clip:           1.0

# Loss weights (from multitask_loss.py)
alpha:                   1.0       # respiratory
beta:                    5.0       # cardiovascular (5x priority)
gamma:                   2.0       # metabolic
```

---

## Verification Plan & Results

### Automated Verification Tasks
```bash
# 1. Train the model
python3 -m pre_build.model.train_tft

# 2. Verify checkpoint loads and produces reasonable predictions
python3 -m pre_build.demo_pipeline

# 3. Run IG attributions with trained model
python3 -m pre_build.explain.export_for_dashboard --engine ig

# 4. Run existing smoke tests (should still pass)
python3 -m pre_build.smoke_test
```
