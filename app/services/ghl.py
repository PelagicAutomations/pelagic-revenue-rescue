import base64
import json
import httpx
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from ..config import settings

GHL_ED25519_PUBLIC_KEY = b"""-----BEGIN PUBLIC KEY-----
MCowBQYDK2VwAyEAi2HR1srL4o18O8BRa7gVJY7G7bupbN3H9AwJrHCDiOg=
-----END PUBLIC KEY-----"""

def verify_ghl_signature(raw_body: bytes, signature_b64: str | None) -> bool:
    if not signature_b64:
        return False
    try:
        signature = base64.b64decode(signature_b64)
        public_key = load_pem_public_key(GHL_ED25519_PUBLIC_KEY)
        public_key.verify(signature, raw_body)
        return True
    except Exception:
        return False

def _headers():
    return {
        "Authorization": f"Bearer {settings.ghl_private_token}",
        "Content-Type": "application/json",
        "Version": settings.ghl_api_version,
    }

async def send_sms(contact_id: str, message: str) -> dict:
    if not settings.ghl_enabled:
        return {"demo": True, "contactId": contact_id, "message": message}
    if not settings.ghl_private_token:
        raise RuntimeError("GHL_ENABLED=true but GHL_PRIVATE_TOKEN is empty.")
    payload = {
        "type": "SMS",
        "contactId": contact_id,
        "message": message,
        "status": "pending",
    }
    if settings.ghl_from_number:
        payload["fromNumber"] = settings.ghl_from_number
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(
            f"{settings.ghl_api_base}/conversations/messages",
            headers=_headers(),
            json=payload,
        )
        r.raise_for_status()
        return r.json()

async def create_opportunity(contact_id: str, name: str, stage_id: str = "") -> dict:
    if not settings.ghl_enabled:
        return {"demo": True, "opportunity": {"id": f"demo-{contact_id}"}}
    payload = {
        "pipelineId": settings.ghl_pipeline_id,
        "locationId": settings.ghl_location_id,
        "name": name or "New Pelagic Lead",
        "status": "open",
        "contactId": contact_id,
    }
    if stage_id:
        payload["pipelineStageId"] = stage_id
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(
            f"{settings.ghl_api_base}/opportunities/",
            headers=_headers(),
            json=payload,
        )
        r.raise_for_status()
        return r.json()

async def update_opportunity(opportunity_id: str, **updates) -> dict:
    if not settings.ghl_enabled or not opportunity_id:
        return {"demo": True, "opportunity_id": opportunity_id, "updates": updates}
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.put(
            f"{settings.ghl_api_base}/opportunities/{opportunity_id}",
            headers=_headers(),
            json=updates,
        )
        r.raise_for_status()
        return r.json()

async def get_location() -> dict:
    if not settings.ghl_enabled:
        return {"demo": True, "location": {"id": settings.ghl_location_id or "demo-location", "name": "Demo HighLevel Account"}}
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get(
            f"{settings.ghl_api_base}/locations/{settings.ghl_location_id}",
            headers=_headers(),
        )
        r.raise_for_status()
        return r.json()

async def get_pipelines() -> dict:
    if not settings.ghl_enabled:
        return {"demo": True, "pipelines": []}
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get(
            f"{settings.ghl_api_base}/opportunities/pipelines",
            headers=_headers(),
            params={"locationId": settings.ghl_location_id},
        )
        r.raise_for_status()
        return r.json()
