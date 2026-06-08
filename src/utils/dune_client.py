import time
import requests
from src.config import DUNE_API_KEY

BASE_URL = "https://api.dune.com/api/v1"
HEADERS = {"X-Dune-API-Key": DUNE_API_KEY}


def run_query(query_id: int, params: dict | None = None) -> list[dict]:
    """Execute a saved Dune query and return rows. Polls until complete."""
    payload = {"query_parameters": params or {}}
    resp = requests.post(f"{BASE_URL}/query/{query_id}/execute", json=payload, headers=HEADERS)
    resp.raise_for_status()
    execution_id = resp.json()["execution_id"]

    for _ in range(60):
        status = requests.get(f"{BASE_URL}/execution/{execution_id}/status", headers=HEADERS)
        status.raise_for_status()
        state = status.json()["state"]
        if state == "QUERY_STATE_COMPLETED":
            break
        if state in ("QUERY_STATE_FAILED", "QUERY_STATE_CANCELLED"):
            raise RuntimeError(f"Dune query {query_id} ended with state: {state}")
        time.sleep(5)
    else:
        raise TimeoutError(f"Dune query {query_id} did not complete within 5 minutes.")

    results = requests.get(f"{BASE_URL}/execution/{execution_id}/results", headers=HEADERS)
    results.raise_for_status()
    return results.json()["result"]["rows"]
