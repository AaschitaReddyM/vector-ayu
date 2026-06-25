from fastapi.testclient import TestClient
from pre_build.api.main import app

client = TestClient(app)

def test_api():
    print("Testing /api/patients...")
    response = client.get("/api/patients")
    assert response.status_code == 200
    patients = response.json()
    print(f"  Got {len(patients)} patients. First: {patients[0]['id']}")

    print("Testing /api/patients/PT-0001...")
    response = client.get("/api/patients/PT-0001")
    assert response.status_code == 200
    detail = response.json()
    print(f"  Patient: {detail['patient']['display_name']}, Obs: {len(detail['observations'])}")

    print("Testing /api/pipeline/run/PT-0001...")
    response = client.post("/api/pipeline/run/PT-0001")
    assert response.status_code == 200
    result = response.json()
    print(f"  Risk Head: {result['risk']['top_head']}, Triage Rank: {result['triage_rank']}")

    print("Testing /api/triage/queue...")
    response = client.get("/api/triage/queue")
    assert response.status_code == 200
    queue = response.json()
    print(f"  Accepted: {len(queue['accepted'])}, Deferred: {len(queue['deferred'])}")
    
    print("All tests passed successfully!")

if __name__ == "__main__":
    test_api()
