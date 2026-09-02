# Pelagic — First 30 Minutes

## 1. Put the app in GitHub

Create a **private** GitHub repository named `pelagic-revenue-rescue`. Upload the contents of this folder so `render.yaml` is at the repository root. Never upload a `.env` file or any API token.

## 2. Deploy with Render Blueprint

In Render:

1. New → Blueprint.
2. Connect the private GitHub repository.
3. Select `render.yaml`.
4. Deploy the Blueprint.
5. Leave `GHL_ENABLED=false` initially.
6. Open the new Pelagic web-service URL.
7. Verify `/health`.

## 3. Add a demo client

Open `/onboarding`. Retrieve the generated `PELAGIC_ADMIN_TOKEN` from Render's Environment page and use it in the form.

Suggested first config:

- Business name: Pelagic Demo Plumbing
- Service area: Torrance, Redondo Beach, Carson, Lomita
- Services: plumbing, drain cleaning, water heater, leak repair
- Booking URL: https://calendly.com/pelagicauto

## 4. Create the HighLevel Private Integration

In the **pilot sub-account**, open Settings → Private Integrations → Create New Integration.

Name: `Pelagic Revenue Rescue Pilot`

Grant the smallest useful set of permissions for Contacts, Conversations/Conversation Messages, Opportunities, and Locations. Add Calendar permissions only when direct booking is enabled.

Copy the generated token once and store it in Render as `GHL_PRIVATE_TOKEN`. Do not send it in chat or commit it to GitHub.

## 5. Add HighLevel values to Render

Set:

- `GHL_LOCATION_ID`
- `GHL_PRIVATE_TOKEN`
- `GHL_FROM_NUMBER`

Keep `GHL_ENABLED=false` until the token/location test is ready.

Then temporarily set `GHL_ENABLED=true`, redeploy, and call:

`GET /api/setup/diagnostics`

Header:

`X-Admin-Token: <your generated Pelagic admin token>`

The response should contain the connected HighLevel location and the pipelines visible to the integration. Use those results to fill the pipeline and stage IDs in Render.

## 6. Add OpenAI

Store the API key in Render as `OPENAI_API_KEY`. Do not place it in the repository.

## 7. First live test

Use only your own/test phone number. Verify:

1. A lead reaches Pelagic.
2. `Can you come today?` is detected as high intent.
3. The reply contains no invented price.
4. `STOP` opts the test contact out.
5. An Estimate Sent event schedules follow-ups.
6. Booking/Won cancels remaining follow-ups.

Only after those pass should customer traffic be enabled.
