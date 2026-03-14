# wokwi_fetch.py
import re
import requests

def get_project_id(url: str) -> str:
    m = re.search(r"/projects/(\d+)", url)
    if not m:
        raise ValueError("Invalid Wokwi project URL (expected .../projects/<id>)")
    return m.group(1)

def fetch_diagram_json(project_url: str) -> dict:
    pid = get_project_id(project_url)

    # Correct endpoint for the actual diagram JSON
    diagram_url = f"https://wokwi.com/api/projects/{pid}/diagram.json"

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json,text/plain,*/*",
    }

    r = requests.get(diagram_url, headers=headers, timeout=20)
    r.raise_for_status()

    diagram = r.json()
    if not isinstance(diagram, dict):
        raise RuntimeError("diagram.json response is not a JSON object")

    # sanity check (diagram.json normally has connections/parts)
    if "connections" not in diagram:
        # still return it, but warn
        print("WARN: diagram has no 'connections' field")

    return diagram