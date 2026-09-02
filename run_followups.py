import os
import sys
import httpx

hostport = os.getenv("PELAGIC_TARGET_HOSTPORT", "").strip()
token = os.getenv("PELAGIC_ADMIN_TOKEN", "").strip()

if not hostport or not token:
    print("Missing PELAGIC_TARGET_HOSTPORT or PELAGIC_ADMIN_TOKEN", file=sys.stderr)
    raise SystemExit(2)

url = f"http://{hostport}/api/jobs/run-due-followups"
response = httpx.post(url, headers={"X-Admin-Token": token}, timeout=30)
response.raise_for_status()
print(response.json())
