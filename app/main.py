import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Request, HTTPException, Depends, Header
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .config import settings
from .database import init_db, execute, one, all_rows, db, utcnow
from .schemas import ClientCreate, LeadCreate, IncomingMessage, EstimateSent
from .services.ai import analyze_message
from .services.rules import estimate_followup_schedule
from .services.messages import missed_call_message, estimate_message
from .services.ghl import verify_ghl_signature, send_sms, create_opportunity, update_opportunity, get_location, get_pipelines

BASE = Path(__file__).resolve().parent
app = FastAPI(title="Pelagic Revenue Rescue", version="0.1.0")
app.mount("/static", StaticFiles(directory=BASE/"static"), name="static")
templates = Jinja2Templates(directory=BASE/"templates")

@app.on_event("startup")
def startup():
    init_db()

def require_admin(x_admin_token: str | None = Header(default=None)):
    if x_admin_token != settings.admin_token:
        raise HTTPException(401, "Invalid admin token")

def get_client(client_id: int):
    client = one("SELECT * FROM clients WHERE id=?", (client_id,))
    if not client:
        raise HTTPException(404, "Client not found")
    return client

def get_lead(lead_id: int):
    lead = one("SELECT * FROM leads WHERE id=?", (lead_id,))
    if not lead:
        raise HTTPException(404, "Lead not found")
    return lead

@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    clients = all_rows("SELECT * FROM clients ORDER BY id DESC")
    leads = all_rows("SELECT * FROM leads ORDER BY updated_at DESC LIMIT 50")
    pending = one("SELECT COUNT(*) AS n FROM followups WHERE status='pending'")["n"]
    hot = one("SELECT COUNT(*) AS n FROM leads WHERE intent='high' AND dnc=0")["n"]
    booked = one("SELECT COUNT(*) AS n FROM leads WHERE appointment_booked=1")["n"]
    return templates.TemplateResponse("index.html", {
        "request": request, "clients": clients, "leads": leads,
        "pending": pending, "hot": hot, "booked": booked,
        "ghl_enabled": settings.ghl_enabled
    })

@app.get("/onboarding", response_class=HTMLResponse)
def onboarding(request: Request):
    return templates.TemplateResponse("onboarding.html", {"request": request})

@app.get("/health")
def health():
    return {"ok": True, "ghl_enabled": settings.ghl_enabled, "ai_enabled": bool(settings.openai_api_key)}

@app.get("/api/setup/diagnostics")
async def setup_diagnostics(_: None = Depends(require_admin)):
    configured = {
        "ghl_enabled": settings.ghl_enabled,
        "location_id_present": bool(settings.ghl_location_id),
        "private_token_present": bool(settings.ghl_private_token),
        "pipeline_id_present": bool(settings.ghl_pipeline_id),
        "openai_key_present": bool(settings.openai_api_key),
    }
    if not settings.ghl_enabled:
        return {"ok": True, "mode": "demo", "configured": configured, "next": "Add HighLevel credentials, then set GHL_ENABLED=true."}
    if not settings.ghl_private_token or not settings.ghl_location_id:
        return {"ok": False, "configured": configured, "error": "HighLevel is enabled but token/location ID is missing."}
    try:
        location = await get_location()
        pipelines = await get_pipelines()
        return {
            "ok": True,
            "mode": "live",
            "configured": configured,
            "location": location.get("location", location),
            "pipelines": pipelines.get("pipelines", []),
        }
    except Exception as exc:
        return {"ok": False, "mode": "live", "configured": configured, "error": str(exc)}


@app.post("/api/clients")
def create_client(payload: ClientCreate, _: None = Depends(require_admin)):
    now = utcnow()
    client_id = execute("""
        INSERT INTO clients
        (business_name,phone,email,service_area,services,services_not_offered,business_hours,
         booking_url,emergency_policy,financing_info,promotions,created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        payload.business_name,payload.phone,payload.email,payload.service_area,payload.services,
        payload.services_not_offered,payload.business_hours,payload.booking_url,
        payload.emergency_policy,payload.financing_info,payload.promotions,now
    ))
    return get_client(client_id)

@app.get("/api/clients")
def clients(_: None = Depends(require_admin)):
    return all_rows("SELECT * FROM clients ORDER BY id DESC")

@app.post("/api/leads")
async def create_lead(payload: LeadCreate, _: None = Depends(require_admin)):
    get_client(payload.client_id)
    now = utcnow()
    lead_id = execute("""
        INSERT INTO leads
        (client_id,name,phone,email,service_requested,zip_code,source,ghl_contact_id,created_at,updated_at)
        VALUES (?,?,?,?,?,?,?,?,?,?)
    """, (payload.client_id,payload.name,payload.phone,payload.email,payload.service_requested,
          payload.zip_code,payload.source,payload.ghl_contact_id,now,now))
    lead = get_lead(lead_id)

    if payload.ghl_contact_id:
        opp = await create_opportunity(payload.ghl_contact_id, payload.name or "New Lead", settings.ghl_stage_new)
        oid = (opp.get("opportunity") or {}).get("id","")
        if oid:
            execute("UPDATE leads SET ghl_opportunity_id=? WHERE id=?", (oid, lead_id))
            lead = get_lead(lead_id)
    return lead

@app.get("/api/leads")
def list_leads(_: None = Depends(require_admin)):
    return all_rows("SELECT * FROM leads ORDER BY updated_at DESC")

async def process_customer_message(lead: dict, message: str):
    client = get_client(lead["client_id"])
    analysis = analyze_message(message, client)

    dnc = 1 if analysis["intent"] == "opt_out" else lead["dnc"]
    handoff = 1 if analysis["human_handoff"] else lead["human_handoff"]
    stage = lead["stage"]
    if analysis["intent"] == "high":
        stage = "qualified"
    if analysis["wants_booking"]:
        stage = "booking_requested"

    execute("""
        UPDATE leads SET intent=?,urgency=?,service_requested=CASE WHEN ?<>'' THEN ? ELSE service_requested END,
        zip_code=CASE WHEN ?<>'' THEN ? ELSE zip_code END,dnc=?,human_handoff=?,stage=?,last_message=?,updated_at=?
        WHERE id=?
    """, (
        analysis["intent"],analysis["urgency"],analysis["service_requested"],analysis["service_requested"],
        analysis["zip_code"],analysis["zip_code"],dnc,handoff,stage,message,utcnow(),lead["id"]
    ))

    if analysis["intent"] == "opt_out":
        execute("UPDATE followups SET status='cancelled' WHERE lead_id=? AND status='pending'", (lead["id"],))

    if lead.get("ghl_opportunity_id"):
        stage_id = ""
        if stage in {"qualified","booking_requested"}:
            stage_id = settings.ghl_stage_qualified
        updates = {}
        if stage_id: updates["pipelineStageId"] = stage_id
        if updates:
            await update_opportunity(lead["ghl_opportunity_id"], **updates)

    if not dnc and lead.get("ghl_contact_id") and analysis.get("reply"):
        await send_sms(lead["ghl_contact_id"], analysis["reply"])

    return analysis

@app.post("/api/messages/incoming")
async def incoming_message(payload: IncomingMessage, _: None = Depends(require_admin)):
    lead = get_lead(payload.lead_id)
    return await process_customer_message(lead, payload.message)

@app.post("/api/leads/{lead_id}/estimate-sent")
def estimate_sent(lead_id: int, payload: EstimateSent, _: None = Depends(require_admin)):
    lead = get_lead(lead_id)
    execute("UPDATE leads SET stage='estimate_sent',estimate_amount=?,updated_at=? WHERE id=?",
            (payload.amount,utcnow(),lead_id))
    client = get_client(lead["client_id"])
    for due, kind in estimate_followup_schedule():
        execute("""INSERT INTO followups(lead_id,kind,due_at,message,status,created_at)
                   VALUES(?,?,?,?, 'pending', ?)""",
                (lead_id,kind,due.isoformat(),estimate_message(client,kind,lead),utcnow()))
    return {"ok": True, "scheduled": 3}

@app.post("/api/jobs/run-due-followups")
async def run_followups(_: None = Depends(require_admin)):
    now = datetime.now(timezone.utc).isoformat()
    due = all_rows("""
        SELECT f.*, l.dnc,l.appointment_booked,l.stage,l.ghl_contact_id
        FROM followups f JOIN leads l ON l.id=f.lead_id
        WHERE f.status='pending' AND f.due_at<=?
        ORDER BY f.due_at LIMIT 100
    """, (now,))
    sent = 0
    skipped = 0
    for item in due:
        if item["dnc"] or item["appointment_booked"] or item["stage"] in {"won","lost"}:
            execute("UPDATE followups SET status='cancelled' WHERE id=?", (item["id"],))
            skipped += 1
            continue
        if item["ghl_contact_id"]:
            await send_sms(item["ghl_contact_id"], item["message"])
        execute("UPDATE followups SET status='sent',sent_at=? WHERE id=?", (utcnow(),item["id"]))
        sent += 1
    return {"processed": len(due), "sent": sent, "skipped": skipped}

def _extract_contact(payload: dict):
    c = payload.get("contact") or payload.get("data") or payload
    return {
        "contact_id": c.get("contactId") or c.get("id") or payload.get("contactId") or "",
        "name": c.get("name") or c.get("fullName") or c.get("firstName") or "",
        "phone": c.get("phone") or "",
        "email": c.get("email") or "",
    }

def _find_lead_by_contact(contact_id: str):
    if not contact_id:
        return None
    return one("SELECT * FROM leads WHERE ghl_contact_id=? ORDER BY id DESC LIMIT 1", (contact_id,))

@app.post("/api/highlevel/webhook")
async def highlevel_webhook(request: Request):
    raw = await request.body()
    signature = request.headers.get("X-GHL-Signature")

    # In production, signed webhook verification is mandatory.
    # In development, allow unsigned payloads for local testing.
    if settings.env == "production" and not verify_ghl_signature(raw, signature):
        raise HTTPException(401, "Invalid HighLevel webhook signature")
    if signature and not verify_ghl_signature(raw, signature):
        raise HTTPException(401, "Invalid HighLevel webhook signature")

    try:
        payload = json.loads(raw.decode("utf-8"))
    except Exception:
        raise HTTPException(400, "Invalid JSON")

    webhook_id = payload.get("webhookId") or payload.get("idempotencyKey")
    event_type = str(payload.get("type") or payload.get("eventType") or "unknown")

    if webhook_id and one("SELECT id FROM events WHERE webhook_id=?", (webhook_id,)):
        return {"ok": True, "duplicate": True}

    contact = _extract_contact(payload)
    lead = _find_lead_by_contact(contact["contact_id"])

    # If a configured client exists, attach unknown contacts to the first active client.
    if not lead and contact["contact_id"]:
        client = one("SELECT * FROM clients WHERE active=1 ORDER BY id LIMIT 1")
        if client:
            now = utcnow()
            lead_id = execute("""
                INSERT INTO leads(client_id,ghl_contact_id,name,phone,email,source,created_at,updated_at)
                VALUES(?,?,?,?,?,'highlevel',?,?)
            """, (client["id"],contact["contact_id"],contact["name"],contact["phone"],contact["email"],now,now))
            lead = get_lead(lead_id)

    evt = event_type.lower()

    # Common inbound message patterns.
    msg = (
        payload.get("message")
        or (payload.get("data") or {}).get("message")
        or (payload.get("body") if isinstance(payload.get("body"), str) else "")
    )

    if lead and msg and any(x in evt for x in ["message","conversation","inbound"]):
        # Webhook source is trusted after signature verification.
        await process_customer_message(lead, msg)

    # Missed-call recovery: intentionally broad event matching because account workflow payloads vary.
    if lead and ("call" in evt and any(x in json.dumps(payload).lower() for x in ["missed","no-answer","no_answer"])):
        if not lead["dnc"] and lead["ghl_contact_id"]:
            client = get_client(lead["client_id"])
            await send_sms(lead["ghl_contact_id"], missed_call_message(client, lead["name"].split(" ")[0] if lead["name"] else ""))

    execute(
        "INSERT INTO events(webhook_id,event_type,lead_id,payload,created_at) VALUES(?,?,?,?,?)",
        (webhook_id,event_type,lead["id"] if lead else None,json.dumps(payload),utcnow())
    )
    return {"ok": True, "event_type": event_type, "lead_id": lead["id"] if lead else None}

@app.post("/api/highlevel/workflow/estimate-sent")
def workflow_estimate_sent(payload: dict, x_pelagic_webhook_secret: str | None = Header(default=None)):
    if x_pelagic_webhook_secret != settings.webhook_secret:
        raise HTTPException(401, "Invalid webhook secret")
    contact_id = payload.get("contactId") or payload.get("contact_id")
    lead = _find_lead_by_contact(contact_id)
    if not lead:
        raise HTTPException(404, "Lead not found for contact")
    amount = payload.get("amount") or payload.get("estimateAmount")
    return estimate_sent(lead["id"], EstimateSent(amount=amount), None)

@app.post("/api/leads/{lead_id}/booked")
async def mark_booked(lead_id: int, _: None = Depends(require_admin)):
    lead = get_lead(lead_id)
    execute("UPDATE leads SET appointment_booked=1,stage='booked',updated_at=? WHERE id=?", (utcnow(),lead_id))
    execute("UPDATE followups SET status='cancelled' WHERE lead_id=? AND status='pending'", (lead_id,))
    if lead.get("ghl_opportunity_id") and settings.ghl_stage_booked:
        await update_opportunity(lead["ghl_opportunity_id"], pipelineStageId=settings.ghl_stage_booked)
    return {"ok": True}

@app.post("/api/leads/{lead_id}/won")
async def mark_won(lead_id: int, _: None = Depends(require_admin)):
    lead = get_lead(lead_id)
    execute("UPDATE leads SET stage='won',updated_at=? WHERE id=?", (utcnow(),lead_id))
    execute("UPDATE followups SET status='cancelled' WHERE lead_id=? AND status='pending'", (lead_id,))
    if lead.get("ghl_opportunity_id"):
        updates = {"status":"won"}
        if settings.ghl_stage_won:
            updates["pipelineStageId"] = settings.ghl_stage_won
        await update_opportunity(lead["ghl_opportunity_id"], **updates)
    return {"ok": True}
