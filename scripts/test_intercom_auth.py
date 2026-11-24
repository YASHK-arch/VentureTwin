import os
import httpx
from pathlib import Path

env_file = Path(__file__).resolve().parent.parent / ".env"
if env_file.exists():
    with open(env_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

token = os.getenv("INTERCOM_ACCESS_TOKEN")

headers = {
    "Authorization": f"Bearer {token}",
    "Accept": "application/json",
    "Content-Type": "application/json",
    "Intercom-Version": "2.11"
}

convo_id = "215476983437471"
admin_id = "12176960"

payload = {
    "message_type": "close",
    "type": "admin",
    "admin_id": admin_id,
    "body": "Issue resolved with production patch."
}

res = httpx.post(f"https://api.intercom.io/conversations/{convo_id}/reply", headers=headers, json=payload, timeout=15.0)
print("Close status via reply:", res.status_code)
if res.status_code == 200:
    print("State:", res.json().get("state"))
else:
    print("Error:", res.text)
