"""HTTP transport for the simulator — the ONLY way it talks to the model.

The simulator deliberately never imports the pipeline: it exercises the same
public /predict path the dashboard's data comes through, which is exactly
what makes the demo an end-to-end system test (ADR-005/012 stay intact).
httpx2 is already a pinned project dependency (it also backs the API tests).
"""

import httpx2 as httpx

from simulator.replay import ApiUnreachable, RequestTimeout

DEFAULT_API_URL = "http://localhost:8000"


def make_sender(api_url=DEFAULT_API_URL, timeout=5.0):
    """Return send(payload) -> (status_code, body_dict) for run_replay."""
    client = httpx.Client(base_url=api_url, timeout=timeout)

    def send(payload):
        try:
            response = client.post("/predict", json={"features": payload})
        except httpx.TimeoutException as error:
            raise RequestTimeout(str(error)) from error
        except httpx.TransportError as error:
            raise ApiUnreachable(str(error)) from error
        try:
            body = response.json()
        except ValueError:
            body = {}
        return response.status_code, body

    return send


def check_health(api_url=DEFAULT_API_URL, timeout=5.0):
    """Return the /health body, or None if the API is unreachable."""
    try:
        response = httpx.get(f"{api_url}/health", timeout=timeout)
        return response.json() if response.status_code == 200 else None
    except httpx.HTTPError:
        return None
