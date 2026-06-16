"""
╔══════════════════════════════════════════════════════════════════════╗
║  CLIMAHEALTH ABLATION STUDY — OPTION 2                             ║
║  Fully Synthetic Data with Controlled Effect Sizes                 ║
║                                                                    ║
║  Purpose: Validate the same hypothesis with fully synthetic data   ║
║  where we KNOW the ground truth effect sizes, to confirm that      ║
║  the ML pipeline correctly recovers them.                          ║
║                                                                    ║
║  Key difference from Option 1:                                     ║
║  - Environmental data is also synthetic (not real EPA data)        ║
║  - Effect sizes are explicitly controlled                          ║
║  - This acts as a "sanity check" that the methodology is sound     ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import json
import warnings
from pathlib import Path

warnings.filterwarnings('ignore')

OUTPUT_DIR = Path(__file__).parent / "results"
OUTPUT_DIR.mkdir(exist_ok=True)

print("=" * 70)
print("  CLIMAHEALTH ABLATION STUDY — OPTION 2")
print("  Fully Synthetic Data with Controlled Effect Sizes")
print("=" * 70)

# ╔══════════════════════════════════════════════════════════════════╗
# ║  STEP 1: Generate Fully Synthetic Environmental Data            ║
# ╚══════════════════════════════════════════════════════════════════╝

print("\n[STEP 1] Generating synthetic environmental data...")

np.random.seed(123)  # Different seed from Option 1
n_days = 730  # 2 years

dates = pd.date_range("2023-01-01", periods=n_days, freq="D")
day_of_year = np.array([(d.timetuple().tm_yday) for d in dates])

# Synthetic AQI — simplified seasonal pattern
summer_peak = 20 * np.sin(2 * np.pi * (day_of_year % 365 - 90) / 365)
base_aqi = 45 + np.maximum(summer_peak, 0)
aqi_noise = np.random.normal(0, 12, n_days)

# Add random spikes
spike_days = np.random.choice(n_days, size=40, replace=False)
spikes = np.zeros(n_days)
for sd in spike_days:
    for offset in range(np.random.randint(1, 3)):
        if sd + offset < n_days:
            spikes[sd + offset] += np.random.uniform(60, 130)

aqi = np.clip(base_aqi + aqi_noise + spikes, 5, 280).astype(int)

# Temperature — simple sinusoidal
temperature = 65 + 25 * np.sin(2 * np.pi * (day_of_year % 365 - 110) / 365)
temperature += np.random.normal(0, 5, n_days)

# PM2.5 — correlated with AQI
pm25 = 3 + 0.11 * aqi + np.random.normal(0, 2.5, n_days)
pm25 = np.clip(pm25, 1, 70)

# Ozone
ozone = 35 + 0.25 * np.maximum(temperature - 60, 0) + np.random.normal(0, 7, n_days)
ozone = np.clip(ozone, 5, 110)

# Barometric pressure
barometric = 29.92 + np.random.normal(0, 0.15, n_days)
baro_change = np.diff(barometric, prepend=barometric[0])

# Humidity
humidity = 55 + 15 * np.sin(2 * np.pi * (day_of_year % 365 - 50) / 365)
humidity += np.random.normal(0, 8, n_days)
humidity = np.clip(humidity, 15, 95)

# Heat index
heat_index = np.where(temperature > 80, temperature + 0.4 * (humidity - 40) * 0.1, temperature)

env_df = pd.DataFrame({
    "date": dates,
    "aqi": aqi,
    "pm25": pm25,
    "ozone_ppb": ozone,
    "temperature_f": temperature,
    "heat_index": heat_index,
    "humidity_pct": humidity,
    "barometric_inhg": barometric,
    "baro_change": baro_change,
})

# Add lags
for lag in [1, 2, 3]:
    env_df[f"aqi_lag_{lag}d"] = env_df["aqi"].shift(lag).fillna(env_df["aqi"].mean())
    env_df[f"pm25_lag_{lag}d"] = env_df["pm25"].shift(lag).fillna(env_df["pm25"].mean())
    env_df[f"temp_lag_{lag}d"] = env_df["temperature_f"].shift(lag).fillna(env_df["temperature_f"].mean())

env_df["aqi_3d_avg"] = env_df["aqi"].rolling(3, min_periods=1).mean()
env_df["aqi_7d_avg"] = env_df["aqi"].rolling(7, min_periods=1).mean()
env_df["pm25_3d_avg"] = env_df["pm25"].rolling(3, min_periods=1).mean()

print(f"  ✓ Generated {n_days} days of synthetic environmental data")
print(f"    AQI range: {aqi.min()} - {aqi.max()}, Mean: {aqi.mean():.1f}")

# ╔══════════════════════════════════════════════════════════════════╗
# ║  STEP 2: Generate Synthetic Patient Cohort                      ║
# ╚══════════════════════════════════════════════════════════════════╝

print("\n[STEP 2] Generating synthetic patient cohort...")

np.random.seed(123)
N_PATIENTS = 2847

ages = np.clip(np.random.normal(67, 10, N_PATIENTS), 40, 95).astype(int)
sex = np.random.choice([0, 1], N_PATIENTS, p=[0.46, 0.54])
copd_stage = np.random.choice([1, 2, 3, 4], N_PATIENTS, p=[0.26, 0.38, 0.24, 0.12])

fev1_means = {1: 85, 2: 60, 3: 40, 4: 25}
fev1 = np.array([np.clip(np.random.normal(fev1_means[s], 8), 10, 100) for s in copd_stage])

smoking_years = np.clip(20 + copd_stage * 8 + np.random.normal(0, 10, N_PATIENTS), 0, 80)
current_smoker = np.random.choice([0, 1], N_PATIENTS, p=[0.65, 0.35])
prior_exacerbations = np.random.poisson(lam=0.5 + copd_stage * 0.5, size=N_PATIENTS)
prior_er = np.random.poisson(lam=0.2 + copd_stage * 0.3, size=N_PATIENTS)
med_adherence = np.clip(85 - copd_stage * 5 + np.random.normal(0, 12, N_PATIENTS), 20, 100)
comorbidities = np.random.poisson(lam=1.5 + copd_stage * 0.3, size=N_PATIENTS)
bmi = np.clip(np.random.normal(27, 5, N_PATIENTS), 16, 45)
indoor_shielding = np.clip(np.random.beta(3, 2, N_PATIENTS), 0, 1)

patients = pd.DataFrame({
    "age": ages, "sex": sex, "copd_stage": copd_stage, "fev1_pct": fev1,
    "smoking_pack_years": smoking_years, "current_smoker": current_smoker,
    "prior_exacerbations": prior_exacerbations, "prior_er_visits": prior_er,
    "med_adherence": med_adherence, "comorbidity_count": comorbidities,
    "bmi": bmi, "indoor_shielding": indoor_shielding,
})

print(f"  ✓ Generated {N_PATIENTS} patients")

# ╔══════════════════════════════════════════════════════════════════╗
# ║  STEP 3: Create Observations and Outcomes                       ║
# ╚══════════════════════════════════════════════════════════════════╝

print("\n[STEP 3] Creating patient-day observations...")

np.random.seed(123)
n_days_per_patient = 30
total_obs = N_PATIENTS * n_days_per_patient

patient_indices = np.repeat(np.arange(N_PATIENTS), n_days_per_patient)
day_indices = np.array([
    np.random.choice(len(env_df), n_days_per_patient, replace=False)
    for _ in range(N_PATIENTS)
]).flatten()

obs = pd.DataFrame({"patient_idx": patient_indices, "day_idx": day_indices})

for col in patients.columns:
    obs[col] = patients[col].values[obs["patient_idx"].values]

env_cols = [c for c in env_df.columns if c != "date"]
for col in env_cols:
    obs[col] = env_df[col].values[obs["day_idx"].values]

obs["effective_aqi"] = obs["aqi"] * (1 - obs["indoor_shielding"] * 0.65)
obs["effective_pm25"] = obs["pm25"] * (1 - obs["indoor_shielding"] * 0.65)

print(f"  ✓ Created {len(obs):,} patient-day observations")

# ── Use IDENTICAL outcome model as Option 1 ──
print("\n[STEP 4] Simulating outcomes (SAME model as Option 1)...")

logit = (
    -4.5
    + 0.55 * (obs["copd_stage"] - 2)
    + 0.30 * obs["prior_exacerbations"]
    + 0.20 * obs["prior_er_visits"]
    - 0.015 * obs["fev1_pct"]
    + 0.008 * obs["smoking_pack_years"]
    + 0.25 * obs["current_smoker"]
    - 0.012 * obs["med_adherence"]
    + 0.08 * obs["comorbidity_count"]
    + 0.01 * (obs["age"] - 65)
    + 0.008 * (obs["effective_aqi"] - 50)
    + 0.020 * (obs["effective_pm25"] - 12)
    + 0.005 * np.maximum(obs["ozone_ppb"] - 70, 0)
    + 0.010 * np.maximum(obs["temperature_f"] - 95, 0)
    + 0.008 * np.maximum(32 - obs["temperature_f"], 0)
    - 0.80 * obs["baro_change"]
    + 0.005 * np.maximum(obs["humidity_pct"] - 80, 0)
    + 0.004 * np.maximum(obs["heat_index"] - 100, 0)
    + 0.004 * (obs["aqi_lag_1d"] - 50)
    + 0.003 * (obs["aqi_lag_2d"] - 50)
    + 0.002 * (obs["aqi_lag_3d"] - 50)
    + 0.005 * (obs["aqi_3d_avg"] - 50)
    + 0.003 * obs["copd_stage"] * np.maximum(obs["effective_aqi"] - 100, 0) / 50
)

prob = 1 / (1 + np.exp(-logit))
np.random.seed(123)
obs["exacerbation"] = (np.random.random(len(obs)) < prob).astype(int)

exac_rate = obs["exacerbation"].mean()
print(f"  ✓ Overall exacerbation rate: {exac_rate:.1%}")

# ╔══════════════════════════════════════════════════════════════════╗
# ║  STEP 5: ABLATION STUDY                                         ║
# ╚══════════════════════════════════════════════════════════════════╝

print("\n" + "=" * 70)
print("  FEATURE ABLATION STUDY — OPTION 2 (FULLY SYNTHETIC)")
print("=" * 70)

from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.metrics import roc_auc_score, f1_score, precision_score, recall_score, roc_curve
from xgboost import XGBClassifier

clinical_features = [
    "age", "sex", "copd_stage", "fev1_pct", "smoking_pack_years",
    "current_smoker", "prior_exacerbations", "prior_er_visits",
    "med_adherence", "comorbidity_count", "bmi"
]

environmental_features = [
    "effective_aqi", "effective_pm25", "ozone_ppb",
    "temperature_f", "heat_index", "humidity_pct",
    "barometric_inhg", "baro_change",
    "aqi_lag_1d", "aqi_lag_2d", "aqi_lag_3d",
    "pm25_lag_1d", "pm25_lag_2d", "pm25_lag_3d",
    "temp_lag_1d",
    "aqi_3d_avg", "aqi_7d_avg", "pm25_3d_avg",
    "indoor_shielding"
]

all_features = clinical_features + environmental_features
y = obs["exacerbation"].values

cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
xgb_params = {
    "n_estimators": 200, "max_depth": 6, "learning_rate": 0.1,
    "subsample": 0.8, "colsample_bytree": 0.8, "min_child_weight": 5,
    "scale_pos_weight": (1 - exac_rate) / exac_rate,
    "random_state": 42, "eval_metric": "logloss", "verbosity": 0,
}

results = {}
print("\n  Running 5-fold cross-validation...\n")

for name, features in [
    ("Model A: Clinical Only", clinical_features),
    ("Model B: Clinical + Environmental", all_features),
    ("Model C: Environmental Only", environmental_features),
]:
    X = obs[features].values
    y_proba = cross_val_predict(
        XGBClassifier(**xgb_params), X, y, cv=cv, method="predict_proba"
    )[:, 1]
    y_pred = (y_proba >= 0.5).astype(int)
    
    auc = roc_auc_score(y, y_proba)
    f1 = f1_score(y, y_pred)
    prec = precision_score(y, y_pred, zero_division=0)
    rec = recall_score(y, y_pred, zero_division=0)
    
    results[name] = {"auc": auc, "f1": f1, "precision": prec, "recall": rec, "y_proba": y_proba}
    
    print(f"  {name}")
    print(f"    AUC: {auc:.4f}  F1: {f1:.4f}  Prec: {prec:.4f}  Recall: {rec:.4f}")
    print()

auc_a = results["Model A: Clinical Only"]["auc"]
auc_b = results["Model B: Clinical + Environmental"]["auc"]
auc_c = results["Model C: Environmental Only"]["auc"]
delta = auc_b - auc_a

print("─" * 70)
print("  OPTION 2 RESULTS")
print("─" * 70)
print(f"""
  ┌─────────────────────────────────────────────────────┐
  │  Model A (Clinical Only)          AUC = {auc_a:.4f}   │
  │  Model B (Clinical + Environment) AUC = {auc_b:.4f}   │
  │  Model C (Environment Only)       AUC = {auc_c:.4f}   │
  │                                                     │
  │  ΔᎪᵁᶜ (B - A) = +{delta:.4f}                        │
  │  Relative Improvement: +{(delta/auc_a)*100:.1f}%                   │
  └─────────────────────────────────────────────────────┘
""")

# ── Subgroup analysis ──
print("─" * 70)
print("  SUBGROUP ANALYSIS")
print("─" * 70)

for label, mask_func in [
    ("All Days", lambda df: pd.Series(True, index=df.index)),
    ("AQI > 100", lambda df: df["aqi"] > 100),
    ("AQI > 150", lambda df: df["aqi"] > 150),
    ("Temp > 95°F", lambda df: df["temperature_f"] > 95),
    ("Stage III-IV + AQI > 100", lambda df: (df["copd_stage"] >= 3) & (df["aqi"] > 100)),
]:
    mask = mask_func(obs)
    n = mask.sum()
    if n < 100:
        continue
    y_sub = y[mask]
    if len(np.unique(y_sub)) < 2:
        continue
    
    auc_a_sub = roc_auc_score(y_sub, results["Model A: Clinical Only"]["y_proba"][mask])
    auc_b_sub = roc_auc_score(y_sub, results["Model B: Clinical + Environmental"]["y_proba"][mask])
    delta_sub = auc_b_sub - auc_a_sub
    
    print(f"\n  {label} (n={n:,}, rate={y_sub.mean():.1%}):")
    print(f"    Clinical: {auc_a_sub:.4f}  |  + Env: {auc_b_sub:.4f}  |  Δ = +{delta_sub:.4f}")

# ── Save results ──
summary = {
    "study": "VAYU Ablation Study — Option 2 (Fully Synthetic)",
    "n_patients": N_PATIENTS,
    "n_observations": len(obs),
    "exacerbation_rate": float(exac_rate),
    "model_a_auc": float(auc_a),
    "model_b_auc": float(auc_b),
    "model_c_auc": float(auc_c),
    "delta_auc": float(delta),
    "relative_improvement_pct": float((delta / auc_a) * 100),
}

with open(OUTPUT_DIR / "ablation_results_option2.json", "w") as f:
    json.dump(summary, f, indent=2)

# ── Plot ──
fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))
fig.patch.set_facecolor('#0a0f1e')

for ax in axes:
    ax.set_facecolor('#111827')
    ax.tick_params(colors='#8892a4')
    for spine in ax.spines.values():
        spine.set_color('#2a3350')

# ROC curves
ax = axes[0]
for name, color, ls in [
    ("Model A: Clinical Only", "#ff6b6b", "--"),
    ("Model B: Clinical + Environmental", "#00d4aa", "-"),
    ("Model C: Environmental Only", "#a78bfa", ":"),
]:
    fpr, tpr, _ = roc_curve(y, results[name]["y_proba"])
    auc_val = results[name]["auc"]
    ax.plot(fpr, tpr, color=color, linewidth=2.5, linestyle=ls,
            label=f"{name.split(':')[1].strip()} (AUC={auc_val:.3f})")

ax.plot([0, 1], [0, 1], color='#5a6478', linestyle=':', linewidth=1)
ax.set_xlabel("False Positive Rate", color='#8892a4')
ax.set_ylabel("True Positive Rate", color='#8892a4')
ax.set_title("ROC Curves — Option 2 (Fully Synthetic)", color='#f0f4f8', fontweight='bold')
ax.legend(fontsize=8, facecolor='#1a2235', edgecolor='#2a3350', labelcolor='#c8cdd5')

# Comparison bar chart
ax = axes[1]
model_names = ["Clinical\nOnly", "Clinical +\nEnvironmental", "Environmental\nOnly"]
aucs = [auc_a, auc_b, auc_c]
colors = ["#ff6b6b", "#00d4aa", "#a78bfa"]

bars = ax.bar(model_names, aucs, color=colors, width=0.5)
ax.set_ylim(min(aucs) - 0.05, max(aucs) + 0.03)
ax.set_ylabel("AUC-ROC", color='#8892a4')
ax.set_title("Model Comparison — Option 2", color='#f0f4f8', fontweight='bold')

for bar, auc_val in zip(bars, aucs):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.005,
            f'{auc_val:.4f}', ha='center', va='bottom', color='#f0f4f8',
            fontweight='bold', fontsize=11)

plt.tight_layout()
plt.savefig(OUTPUT_DIR / "ablation_results_option2.png", dpi=150, bbox_inches='tight', facecolor='#0a0f1e')
print(f"\n  ✓ Saved plots and results to {OUTPUT_DIR}")

print("\n" + "=" * 70)
print("  OPTION 2 COMPLETE")
print("=" * 70)
