import os
from pathlib import Path
from functools import lru_cache
from google.cloud import firestore
from google.oauth2 import service_account

@lru_cache(maxsize=1)
def get_firestore_client() -> firestore.Client:
    """Returns a connected Firestore client using the local GCP service account key."""
    # Look for the GCP key in the version-1 directory
    # Adjust this path if deploying to Cloud Run (where we might just use default credentials)
    key_path = Path(r"c:\Users\Vector-Ayu (VAYU)\Desktop\vayu\version-1\gcp-key.json.json")
    
    if key_path.exists():
        credentials = service_account.Credentials.from_service_account_file(key_path)
        return firestore.Client(credentials=credentials, project=credentials.project_id)
    else:
        # Fallback to Application Default Credentials for Cloud Run
        return firestore.Client()
