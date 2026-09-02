# Deploy Pelagic Revenue Rescue on Render

This project now includes a Render Blueprint (`render.yaml`) that creates:

1. `pelagic-revenue-rescue` — the FastAPI web app.
2. `pelagic-followup-runner` — a cron job that runs due estimate follow-ups every 10 minutes.
3. A 1 GB persistent disk mounted at `/var/data` for the SQLite pilot database.

## Recommended rollout

### Stage A — Deploy safely in demo mode

The Blueprint intentionally starts with:

`GHL_ENABLED=false`

That means the app can be deployed and tested without sending real SMS messages.

1. Put this project in a private GitHub repository.
2. In Render, create a **Blueprint** from that repository.
3. Render reads `render.yaml` automatically.
4. When Render asks for secret values, you can leave the HighLevel values blank for the first deploy if the UI permits it, or provide placeholders and keep `GHL_ENABLED=false`.
5. Deploy.
6. Open the generated `*.onrender.com` URL and verify `/health` returns `ok: true`.

## Stage B — Connect the first HighLevel sub-account

Create a **Private Integration** inside the HighLevel sub-account you want to pilot.

Name it:

`Pelagic Revenue Rescue Pilot`

Grant only the permissions needed by this MVP. At minimum, the integration needs access appropriate for:

- Contacts: view/edit
- Conversations: view/edit
- Conversation Messages: view/edit
- Opportunities: view/edit
- Locations: view

If you add direct calendar booking later, also enable:

- Calendars: view/edit
- Calendar Events: view/edit

Copy the Private Integration Token immediately and store it only in Render's secret environment variable:

`GHL_PRIVATE_TOKEN`

Do **not** paste it into source code or commit it to GitHub.

Also populate these environment variables in Render:

- `GHL_LOCATION_ID`
- `GHL_PIPELINE_ID`
- `GHL_STAGE_NEW`
- `GHL_STAGE_QUALIFIED`
- `GHL_STAGE_BOOKED`
- `GHL_STAGE_ESTIMATE`
- `GHL_STAGE_WON`
- `GHL_FROM_NUMBER`

Then set:

`GHL_ENABLED=true`

Redeploy/restart the web service.

## Stage C — Configure HighLevel events

The production webhook endpoint is:

`https://YOUR-RENDER-HOST/api/highlevel/webhook`

Production mode requires HighLevel's current `X-GHL-Signature` Ed25519 signature. The app already verifies it against HighLevel's documented public key.

For the first pilot, use HighLevel workflows/custom webhooks to send only the event data you actually need. Avoid wiring every possible event at once.

### Estimate Sent workflow

Create a HighLevel workflow that runs when an estimate/opportunity reaches your estimate-sent state.

Add a Custom Webhook action to:

`POST https://YOUR-RENDER-HOST/api/highlevel/workflow/estimate-sent`

Header:

`X-Pelagic-Webhook-Secret: <PELAGIC_WEBHOOK_SECRET>`

Example body:

```json
{
  "contactId": "{{contact.id}}",
  "amount": "{{opportunity.monetary_value}}"
}
```

Select merge fields from HighLevel's workflow editor instead of typing them blindly; available merge fields depend on the workflow trigger.

## Stage D — Add OpenAI

In Render, set:

`OPENAI_API_KEY=<your key>`

Keep:

`OPENAI_MODEL=gpt-5-mini`

If the OpenAI key is missing or the API request fails, the MVP falls back to deterministic intent rules instead of blocking customer responses.

## Stage E — Test before turning on customer traffic

Use a test contact and test number.

Run these tests in order:

1. New inbound lead appears in Pelagic dashboard.
2. Inbound "Can you come today?" becomes high-intent/urgent.
3. AI reply is concise and contains no invented price.
4. STOP causes DNC and cancels pending follow-ups.
5. Missed call sends only one recovery message.
6. Estimate Sent creates three scheduled follow-ups.
7. Marking the lead Booked cancels remaining estimate follow-ups.
8. Marking Won cancels remaining follow-ups and updates HighLevel.
9. Invalid webhook signatures are rejected in production.
10. A real HighLevel event is accepted with a valid signature.

## Important limitation of the pilot

This deployment uses SQLite on a persistent disk. That is appropriate for a single-instance pilot. Before onboarding many paying clients, move the database to Postgres and change the integration model from one shared HighLevel Private Integration configuration to per-client OAuth/token storage.
