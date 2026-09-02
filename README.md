# Pelagic Revenue Rescue MVP

## Production pilot deployment

Use `render.yaml` for the fastest pilot deployment. See `DEPLOY_RENDER.md` for the exact rollout sequence. The Blueprint starts in safe demo mode and provisions a persistent disk plus a scheduled follow-up runner.


A runnable starter backend + control dashboard for Pelagic Automations' productized home-service AI follow-up system.

## What is already implemented

- Multi-client business configuration
- Lead database + pipeline states
- HighLevel webhook receiver
- **Current HighLevel Ed25519 `X-GHL-Signature` verification**
- Duplicate webhook protection
- HighLevel SMS adapter
- HighLevel opportunity create/update adapter
- AI/heuristic intent classification
- Hot-intent / booking detection
- Opt-out handling
- Human-handoff detection
- Emergency safety handling
- Missed-call recovery logic
- Estimate follow-up scheduling
- Follow-up cancellation on DNC / booking / won / lost
- Simple Pelagic dashboard
- Client onboarding page
- Docker support
- Unit tests
- Demo mode that works without HighLevel or OpenAI credentials

## Architecture

HighLevel / Website / Lead Source
        |
        v
Pelagic API (`/api/highlevel/webhook`)
        |
        +--> signature + duplicate check
        |
        +--> lead record
        |
        +--> AI classification
        |
        +--> SMS reply through HighLevel
        |
        +--> pipeline update
        |
        +--> estimate follow-up queue

## 1. Run locally

```bash
cp .env.example .env
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
python scripts/seed_demo.py
uvicorn app.main:app --reload
```

Open: `http://localhost:8000`

The application defaults to **DEMO MODE**. No real SMS will be sent until `GHL_ENABLED=true`.

## 2. Configure your first real client

Open `http://localhost:8000/onboarding`.

Change `PELAGIC_ADMIN_TOKEN` in `.env` first. The onboarding page requires that token.

## 3. HighLevel setup

For an internal first client, use a scoped HighLevel Private Integration token. For a scalable public/marketplace integration, move to OAuth.

Populate:
- `GHL_PRIVATE_TOKEN`
- `GHL_LOCATION_ID`
- `GHL_PIPELINE_ID`
- stage IDs
- sending number

Then set:
`GHL_ENABLED=true`

### Webhook URL
Deploy the API publicly via HTTPS, then configure HighLevel to send relevant webhook events to:

`POST https://YOUR-DOMAIN/api/highlevel/webhook`

Production mode requires a valid `X-GHL-Signature`.

### Estimate workflow
Inside the HighLevel "Estimate Sent" workflow, add a Custom Webhook action:

`POST https://YOUR-DOMAIN/api/highlevel/workflow/estimate-sent`

Header:
`X-Pelagic-Webhook-Secret: <your PELAGIC_WEBHOOK_SECRET>`

Suggested body:
```json
{
  "contactId": "{{contact.id}}",
  "amount": "{{opportunity.monetary_value}}"
}
```

Exact merge-field names should be selected from your HighLevel workflow UI because available fields depend on the trigger/context.

## 4. Run follow-ups

Call the endpoint below every 5 minutes from your hosting platform's cron/scheduler:

`POST /api/jobs/run-due-followups`

Header:
`X-Admin-Token: <PELAGIC_ADMIN_TOKEN>`

This is intentionally cron-driven instead of relying on an in-process timer so it works on common container/serverless deployments.

## 5. OpenAI

Put your key in:
`OPENAI_API_KEY=...`

The service uses the Responses API with a JSON Schema output for lead analysis. If OpenAI is unavailable, the app falls back to safe deterministic rules instead of failing the customer interaction.

## Connection diagnostics

After setting your HighLevel credentials, call `GET /api/setup/diagnostics` with the `X-Admin-Token` header. It validates the sub-account connection and returns the pipelines visible to the integration.

## 6. Before production

Required next work:
- Add user authentication instead of a single admin token.
- Add per-client HighLevel credentials / OAuth tokens.
- Add a queue (Redis/Celery/SQS) for webhook processing at scale.
- Add rate limiting.
- Add structured audit logs.
- Configure SMS registration/consent and carrier requirements.
- Add per-client message windows and timezone rules.
- Add a proper booking API integration instead of only sending a booking link.
- Add review-request workflow.
- Add Stripe subscription provisioning.
- Add SaaS onboarding automation/Snapshot provisioning.
- Add observability and backups.

## API quick test

Create a client:
```bash
curl -X POST http://localhost:8000/api/clients \
  -H "Content-Type: application/json" \
  -H "X-Admin-Token: change-me" \
  -d '{"business_name":"Demo Plumbing","service_area":"Torrance","services":"plumbing","booking_url":"https://calendly.com/pelagicauto"}'
```

Create a lead:
```bash
curl -X POST http://localhost:8000/api/leads \
  -H "Content-Type: application/json" \
  -H "X-Admin-Token: change-me" \
  -d '{"client_id":1,"name":"Chris","phone":"+13105550199","source":"website"}'
```

Process a customer message:
```bash
curl -X POST http://localhost:8000/api/messages/incoming \
  -H "Content-Type: application/json" \
  -H "X-Admin-Token: change-me" \
  -d '{"lead_id":1,"message":"My water heater broke. Can you come today?"}'
```

## Product boundary

This MVP is designed for **consented inbound leads and legitimate customer follow-up**. It does not automatically blast old/purchased lead lists. DNC and opt-out states stop scheduled follow-ups.
