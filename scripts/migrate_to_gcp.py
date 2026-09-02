import os
import sys
from pathlib import Path
import pandas as pd
import numpy as np

# Adjust path to import from version-1
sys.path.insert(0, str(Path(__file__).resolve().parent / "version-1"))

from google.cloud import bigquery
from google.cloud import firestore
from google.oauth2 import service_account

from pre_build.model.train_tft import generate_synthetic_dataset
from pre_build.explain.channel_labels import STATIC_LABELS

def main():
    print("Starting migration script...")
    
    # 1. Setup GCP Authentication
    key_path = Path(r"c:\Users\Vector-Ayu (VAYU)\Desktop\vayu\gcp-key.json.json")
    if not key_path.exists():
        print(f"Error: Could not find key file at {key_path}")
        return
        
    credentials = service_account.Credentials.from_service_account_file(key_path)
    project_id = credentials.project_id
    print(f"Authenticated with GCP Project: {project_id}")
    
    # 2. Generate Synthetic Data
    # To stay within free tier limits for quick testing, we'll generate the data
    # (Generating 2847 patients * 30 days = 85,410 samples)
    inputs, targets = generate_synthetic_dataset(n_patients=2847, days_per_patient=30, seed=42)
    
    # Extract static patient profiles (taking just the first day for each patient)
    # The generated static array has shape (85410, num_features).
    # Since it's generated as n_patients * days_per_patient, we can just reshape
    static_numpy = inputs["static"].numpy()
    n_samples = static_numpy.shape[0]
    n_patients = 2847
    days = 30
    
    # Get one static profile per patient (the first day)
    patient_profiles = static_numpy[0::days, :] 
    
    # Create DataFrame for BigQuery
    import re
    def sanitize_col(name):
        return re.sub(r'[^a-zA-Z0-9_]', '_', name).strip('_').lower()
        
    sanitized_labels = [sanitize_col(lbl) for lbl in STATIC_LABELS]
    df_static = pd.DataFrame(patient_profiles, columns=sanitized_labels)
    df_static["patient_id"] = [f"PT-{str(i).zfill(4)}" for i in range(1, n_patients + 1)]
    
    # Add fake names and locations for the demo
    rng = np.random.default_rng(42)
    df_static["postal_code"] = rng.choice(["75218", "75219", "75220", "75225", "75201"], size=n_patients)
    df_static["given_name"] = rng.choice(["Juan", "Maria", "James", "Linda", "Robert", "Patricia"], size=n_patients)
    df_static["primary_language"] = rng.choice(["en", "es"], size=n_patients, p=[0.7, 0.3])
    
    print(f"Created DataFrame with {len(df_static)} patient profiles.")
    
    # 3. Push to BigQuery
    print("\nConnecting to BigQuery...")
    bq_client = bigquery.Client(credentials=credentials, project=project_id)
    
    dataset_id = f"{project_id}.ehr_data"
    dataset = bigquery.Dataset(dataset_id)
    dataset.location = "US"
    
    try:
        bq_client.create_dataset(dataset, timeout=30)
        print(f"Created BigQuery dataset: {dataset_id}")
    except Exception as e:
        if "Already Exists" in str(e):
            print(f"BigQuery dataset {dataset_id} already exists.")
        else:
            print(f"Dataset creation message: {e}")
            
    table_id = f"{dataset_id}.patient_profiles"
    
    print("Uploading to BigQuery...")
    job_config = bigquery.LoadJobConfig(write_disposition="WRITE_TRUNCATE")
    job = bq_client.load_table_from_dataframe(df_static, table_id, job_config=job_config)
    job.result()  # Wait for the job to complete
    
    table = bq_client.get_table(table_id)
    print(f"Success! Uploaded {table.num_rows} rows to BigQuery table: {table_id}")
    
    # 4. Push subset to Firestore
    # WARNING: Firestore Spark (Free) tier limits writes to 20,000 per day.
    # We will only upload a representative sample (100 patients) so we don't blow the quota!
    print("\nConnecting to Firestore...")
    db = firestore.Client(credentials=credentials, project=project_id)
    
    demo_sample = df_static.head(100)
    batch = db.batch()
    
    print("Uploading 100 sample patients to Firestore...")
    for idx, row in demo_sample.iterrows():
        doc_ref = db.collection("patients").document(row["patient_id"])
        # Convert NumPy types to native Python types for Firestore serialization
        doc_data = {k: (v.item() if isinstance(v, (np.integer, np.floating)) else v) for k, v in row.to_dict().items()}
        batch.set(doc_ref, doc_data)
        
    batch.commit()
    print("Success! Uploaded 100 patient profiles to Firestore collection 'patients'.")
    print("\nMigration Complete! Both BigQuery and Firestore are populated.")

if __name__ == "__main__":
    main()
