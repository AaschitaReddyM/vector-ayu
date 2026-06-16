"""
TFT Model Training Script (Pre-Buildathon).
Generates a large-scale synthetic dataset of patient-day sequences,
calibrated to clinical literature effect sizes, and trains the TFTSkeleton
with early stopping and learning rate scheduling.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

from pre_build.model.tft_skeleton import TFTConfig, TFTSkeleton
from pre_build.model.multitask_loss import MultiTaskLoss, MultiTaskWeights
from pre_build.explain.channel_labels import STATIC_LABELS, CLINICAL_LABELS, ENVIRONMENTAL_LABELS

# Setup directories
MODEL_DIR = Path(__file__).resolve().parent
CHECKPOINT_PATH = MODEL_DIR / "tft_trained.pt"

def generate_synthetic_dataset(
    n_patients: int = 2847,
    days_per_patient: int = 30,
    horizon_hours: int = 72,
    seed: int = 42,
) -> tuple[dict[str, torch.Tensor], dict[str, torch.Tensor]]:
    """
    Generates static, clinical_temporal, and environmental_temporal tensors,
    and computes binary outcomes for the three heads (respiratory, cardiovascular, metabolic)
    based on published clinical risk factor effect sizes.
    """
    print(f"Generating synthetic dataset for {n_patients} patients × {days_per_patient} days...")
    rng = np.random.default_rng(seed)
    
    n_samples = n_patients * days_per_patient
    
    # 1. Dimensions from configurations
    cfg = TFTConfig()
    
    # 2. Map label indices
    s_age = STATIC_LABELS.index("Age decile")
    s_shield = STATIC_LABELS.index("Shielding Coefficient")
    s_bmi = STATIC_LABELS.index("BMI")
    s_copd = STATIC_LABELS.index("COPD severity (GOLD)")
    s_chf = STATIC_LABELS.index("CHF NYHA class")
    s_a1c = STATIC_LABELS.index("Diabetes A1c (last)")
    s_smoking = STATIC_LABELS.index("Smoking pack-years")
    s_prior_er = STATIC_LABELS.index("Prior ER visits (12 mo)")
    s_adherence = STATIC_LABELS.index("Medication adherence")
    
    c_spo2 = CLINICAL_LABELS.index("SpO2 (pulse-ox)")
    c_hr = CLINICAL_LABELS.index("Heart rate")
    c_hrv = CLINICAL_LABELS.index("Heart rate variability")
    c_bp_sys = CLINICAL_LABELS.index("Systolic BP")
    c_rr = CLINICAL_LABELS.index("Respiratory rate")
    c_body_temp = CLINICAL_LABELS.index("Body temperature")
    c_cgm = CLINICAL_LABELS.index("CGM glucose")
    c_inhaler = CLINICAL_LABELS.index("Inhaler actuations")
    
    e_pm25 = ENVIRONMENTAL_LABELS.index("PM2.5")
    e_o3 = ENVIRONMENTAL_LABELS.index("Ozone (O₃)")
    e_aqi = ENVIRONMENTAL_LABELS.index("AQI composite")
    e_pollen = ENVIRONMENTAL_LABELS.index("Pollen index")
    e_temp = ENVIRONMENTAL_LABELS.index("Ambient temperature")
    e_humidity = ENVIRONMENTAL_LABELS.index("Relative humidity")
    e_uv = ENVIRONMENTAL_LABELS.index("UV index")
    
    # 3. Generate static features (shape: n_samples, static_input_dim)
    # Start with standard normal, then inject correlations
    static = rng.normal(0.0, 1.0, size=(n_samples, cfg.static_input_dim)).astype(np.float32)
    # Shielding coefficient is typically positive or zero, let's keep it centered
    # COPD stage correlated with age and smoking
    static[:, s_copd] = 0.5 * static[:, s_age] + 0.6 * static[:, s_smoking] + rng.normal(0, 0.5, n_samples)
    static[:, s_chf] = 0.4 * static[:, s_age] + rng.normal(0, 0.8, n_samples)
    static[:, s_a1c] = 0.3 * static[:, s_bmi] + rng.normal(0, 0.8, n_samples)
    
    # 4. Generate clinical temporal features (shape: n_samples, horizon_hours, clinical_input_dim)
    # Model as AR(1) process starting from some baseline + noise
    clinical = np.zeros((n_samples, horizon_hours, cfg.clinical_input_dim), dtype=np.float32)
    for i in range(cfg.clinical_input_dim):
        # Initial state: partially correlated with static indicators
        init = rng.normal(0, 0.5, size=n_samples)
        if i == c_spo2:
            init -= 0.4 * static[:, s_copd]
        elif i == c_hr:
            init += 0.3 * static[:, s_chf]
        elif i == c_cgm:
            init += 0.5 * static[:, s_a1c]
            
        clinical[:, 0, i] = init
        # AR(1) step
        phi = 0.85
        for t in range(1, horizon_hours):
            clinical[:, t, i] = phi * clinical[:, t-1, i] + rng.normal(0, np.sqrt(1 - phi**2), size=n_samples)
            
    # 5. Generate environmental temporal features (shape: n_samples, horizon_hours, environmental_input_dim)
    # Model with daily cycle + trend (simulating weather event progression)
    enviro = np.zeros((n_samples, horizon_hours, cfg.environmental_input_dim), dtype=np.float32)
    t_axis = np.arange(horizon_hours)
    diurnal = np.sin(2 * np.pi * t_axis / 24.0)  # diurnal variation
    
    for i in range(cfg.environmental_input_dim):
        # Base trend for weather event
        trend = np.linspace(rng.uniform(-0.5, 0.5, n_samples), rng.uniform(0.5, 2.0, n_samples), horizon_hours).T
        noise = rng.normal(0, 0.5, size=(n_samples, horizon_hours))
        
        if i == e_temp:
            enviro[:, :, i] = trend + 0.5 * diurnal[None, :] + noise
        elif i == e_o3:
            # Ozone peaks during high temp
            enviro[:, :, i] = 0.8 * trend + 0.4 * diurnal[None, :] + noise
        elif i == e_pm25 or i == e_aqi:
            # Stagnation event buildup
            enviro[:, :, i] = 1.2 * trend + noise
        else:
            enviro[:, :, i] = trend + noise
            
    # 6. Apply indoor shielding to environmental factors
    # Shielding coefficient acts as attenuation on environmental spikes (if shield is high, exposure is lower)
    # Shielding is static[:, s_shield]. Let's scale it between 0 and 0.8
    shield_factor = np.clip((static[:, s_shield] + 2) / 4, 0.0, 0.8)  # map ~[-2, 2] to ~[0, 0.8]
    # For environmental exposure, we reduce PM2.5 and Ozone for patients with high shielding
    enviro[:, :, e_pm25] = enviro[:, :, e_pm25] * (1.0 - shield_factor[:, None])
    enviro[:, :, e_o3] = enviro[:, :, e_o3] * (1.0 - shield_factor[:, None])
    enviro[:, :, e_aqi] = enviro[:, :, e_aqi] * (1.0 - shield_factor[:, None])

    # 7. Compute logits and outcomes based on means
    env_mean = enviro.mean(axis=1)
    clin_mean = clinical.mean(axis=1)
    
    # Intercepts calibrated to achieve ~8% to 15% positive rate
    z_resp = (
        -2.2
        + 1.3 * env_mean[:, e_pm25]
        + 1.0 * env_mean[:, e_o3]
        + 0.8 * env_mean[:, e_aqi]
        + 0.4 * env_mean[:, e_pollen]
        + 1.1 * static[:, s_copd]
        + 0.7 * static[:, s_smoking]
        + 0.6 * static[:, s_prior_er]
        - 1.2 * static[:, s_shield]
        - 0.5 * static[:, s_adherence]
        - 0.9 * clin_mean[:, c_spo2]
        + 0.6 * clin_mean[:, c_rr]
        + 0.4 * clin_mean[:, c_inhaler]
    )
    
    z_card = (
        -2.5
        + 1.2 * env_mean[:, e_aqi]
        + 0.8 * env_mean[:, e_pm25]
        + 0.9 * env_mean[:, e_temp]
        + 0.8 * static[:, s_prior_er]
        + 1.2 * static[:, s_chf]
        + 0.6 * static[:, s_age]
        - 1.0 * static[:, s_shield]
        - 0.4 * static[:, s_adherence]
        + 0.8 * clin_mean[:, c_hr]
        - 0.7 * clin_mean[:, c_hrv]
        + 0.5 * clin_mean[:, c_bp_sys]
    )
    
    z_meta = (
        -2.8
        + 1.1 * env_mean[:, e_temp]
        + 0.8 * env_mean[:, e_humidity]
        + 0.5 * env_mean[:, e_uv]
        + 1.3 * static[:, s_a1c]
        + 0.7 * static[:, s_bmi]
        - 0.8 * static[:, s_shield]
        - 0.4 * static[:, s_adherence]
        + 1.0 * clin_mean[:, c_cgm]
        + 0.5 * clin_mean[:, c_body_temp]
    )
    
    def to_binary(z):
        p = 1.0 / (1.0 + np.exp(-z))
        return (rng.uniform(size=p.shape) < p).astype(np.float32)
        
    y_resp = to_binary(z_resp)
    y_card = to_binary(z_card)
    y_meta = to_binary(z_meta)
    
    # Report generation statistics
    print(f"Generated {n_samples} samples:")
    print(f"  Respiratory event rate: {y_resp.mean():.2%}")
    print(f"  Cardiovascular event rate: {y_card.mean():.2%}")
    print(f"  Metabolic event rate: {y_meta.mean():.2%}")
    
    # 8. Convert to tensors
    inputs = {
        "static": torch.from_numpy(static),
        "clinical": torch.from_numpy(clinical),
        "environmental": torch.from_numpy(enviro),
    }
    targets = {
        "respiratory": torch.from_numpy(y_resp),
        "cardiovascular": torch.from_numpy(y_card),
        "metabolic": torch.from_numpy(y_meta),
    }
    
    return inputs, targets

def train():
    # Set seed
    torch.manual_seed(42)
    np.random.seed(42)
    
    # Check device
    device = torch.device("mps" if torch.backends.mps.is_available() else ("cuda" if torch.cuda.is_available() else "cpu"))
    print(f"Using device: {device}")
    
    # Optimize CPU threads for 10-core M1 Pro
    torch.set_num_threads(10)
    print("Configured PyTorch CPU intra-op parallelism to 10 threads")
    
    # 1. Generate data
    inputs, targets = generate_synthetic_dataset()
    
    # Create dataset
    dataset = TensorDataset(
        inputs["static"],
        inputs["clinical"],
        inputs["environmental"],
        targets["respiratory"],
        targets["cardiovascular"],
        targets["metabolic"],
    )
    
    # Train / Val Split (80% / 20%)
    n_samples = len(dataset)
    n_train = int(0.8 * n_samples)
    n_val = n_samples - n_train
    
    train_dataset, val_dataset = torch.utils.data.random_split(dataset, [n_train, n_val])
    
    # Data loaders (Increased batch size to 256 for M1 Pro GPU cores saturation)
    batch_size = 256
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)
    
    # 2. Instantiate model and loss
    cfg = TFTConfig()
    model = TFTSkeleton(cfg).to(device)
    
    # Calculate positive weights for class imbalance
    # pos_weight = negative_samples / positive_samples
    y_resp_train = torch.stack([d[3] for d in train_dataset])
    y_card_train = torch.stack([d[4] for d in train_dataset])
    y_meta_train = torch.stack([d[5] for d in train_dataset])
    
    pos_w_resp = (len(y_resp_train) - y_resp_train.sum().item()) / max(y_resp_train.sum().item(), 1)
    pos_w_card = (len(y_card_train) - y_card_train.sum().item()) / max(y_card_train.sum().item(), 1)
    pos_w_meta = (len(y_meta_train) - y_meta_train.sum().item()) / max(y_meta_train.sum().item(), 1)
    
    print(f"Calculated positive class weights for loss:")
    print(f"  Respiratory: {pos_w_resp:.2f}, Cardiovascular: {pos_w_card:.2f}, Metabolic: {pos_w_meta:.2f}")
    
    weights = MultiTaskWeights(alpha=1.0, beta=5.0, gamma=2.0)
    loss_fn = MultiTaskLoss(
        weights=weights,
        pos_weight_respiratory=pos_w_resp,
        pos_weight_cardiovascular=pos_w_card,
        pos_weight_metabolic=pos_w_meta
    ).to(device)
    
    # Optimizer and Scheduler
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=40, eta_min=1e-5)
    
    # Training Loop
    best_val_loss = float("inf")
    epochs = 40
    patience = 8
    epochs_no_improve = 0
    
    print("\nStarting model training...")
    for epoch in range(epochs):
        model.train()
        train_loss = 0.0
        train_loss_resp = 0.0
        train_loss_card = 0.0
        train_loss_meta = 0.0
        
        for stat, clin, env, t_resp, t_card, t_meta in train_loader:
            stat = stat.to(device)
            clin = clin.to(device)
            env = env.to(device)
            
            batch_targets = {
                "respiratory": t_resp.to(device),
                "cardiovascular": t_card.to(device),
                "metabolic": t_meta.to(device),
            }
            
            optimizer.zero_grad()
            logits = model(stat, clin, env)
            
            loss_components = loss_fn(logits, batch_targets)
            loss = loss_components["total"]
            
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            
            train_loss += loss.item() * len(stat)
            train_loss_resp += loss_components["respiratory"].item() * len(stat)
            train_loss_card += loss_components["cardiovascular"].item() * len(stat)
            train_loss_meta += loss_components["metabolic"].item() * len(stat)
            
        scheduler.step()
        
        # Validation
        model.eval()
        val_loss = 0.0
        val_loss_resp = 0.0
        val_loss_card = 0.0
        val_loss_meta = 0.0
        
        # For AUC calculation
        all_val_preds = {"respiratory": [], "cardiovascular": [], "metabolic": []}
        all_val_targets = {"respiratory": [], "cardiovascular": [], "metabolic": []}
        
        with torch.no_grad():
            for stat, clin, env, t_resp, t_card, t_meta in val_loader:
                stat = stat.to(device)
                clin = clin.to(device)
                env = env.to(device)
                
                batch_targets = {
                    "respiratory": t_resp.to(device),
                    "cardiovascular": t_card.to(device),
                    "metabolic": t_meta.to(device),
                }
                
                logits = model(stat, clin, env)
                loss_components = loss_fn(logits, batch_targets)
                
                val_loss += loss_components["total"].item() * len(stat)
                val_loss_resp += loss_components["respiratory"].item() * len(stat)
                val_loss_card += loss_components["cardiovascular"].item() * len(stat)
                val_loss_meta += loss_components["metabolic"].item() * len(stat)
                
                # Store predictions for AUC
                for h in ["respiratory", "cardiovascular", "metabolic"]:
                    probs = torch.sigmoid(logits[h])
                    all_val_preds[h].extend(probs.cpu().numpy())
                    all_val_targets[h].extend(batch_targets[h].cpu().numpy())
                    
        train_loss /= len(train_dataset)
        val_loss /= len(val_dataset)
        
        # Calculate AUC metrics using sklearn
        from sklearn.metrics import roc_auc_score
        auc_scores = {}
        for h in ["respiratory", "cardiovascular", "metabolic"]:
            auc_scores[h] = roc_auc_score(all_val_targets[h], all_val_preds[h])
            
        print(f"Epoch {epoch+1:02d}/{epochs} - Train Loss: {train_loss:.4f} | Val Loss: {val_loss:.4f} | "
              f"Val AUC -> Resp: {auc_scores['respiratory']:.3f}, Card: {auc_scores['cardiovascular']:.3f}, Meta: {auc_scores['metabolic']:.3f}")
              
        # Checkpoint and Early Stopping
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            epochs_no_improve = 0
            
            # Save weights and config
            torch.save(model.state_dict(), CHECKPOINT_PATH)
            print(f"  ✓ Saved checkpoint to {CHECKPOINT_PATH}")
        else:
            epochs_no_improve += 1
            if epochs_no_improve >= patience:
                print(f"Early stopping triggered at epoch {epoch+1}. Training completed.")
                break
                
    print(f"\nTraining finished. Best validation loss: {best_val_loss:.4f}")

if __name__ == "__main__":
    train()
