import json
from .rules import heuristic_analysis
from ..config import settings

SCHEMA = {
  "type": "object",
  "properties": {
    "intent": {"type":"string","enum":["low","medium","high","opt_out","complaint","emergency","unknown"]},
    "urgency": {"type":"string","enum":["low","normal","urgent","emergency","unknown"]},
    "service_requested": {"type":"string"},
    "zip_code": {"type":"string"},
    "wants_booking": {"type":"boolean"},
    "human_handoff": {"type":"boolean"},
    "reply": {"type":"string"},
    "summary": {"type":"string"}
  },
  "required":["intent","urgency","service_requested","zip_code","wants_booking","human_handoff","reply","summary"],
  "additionalProperties": False
}

def analyze_message(message: str, client: dict) -> dict:
    if not settings.openai_api_key:
        return heuristic_analysis(message, client.get("booking_url",""))

    prompt = f"""
You are the lead-response engine for {client['business_name']}.
Services offered: {client.get('services','')}
Services NOT offered: {client.get('services_not_offered','')}
Service area: {client.get('service_area','')}
Business hours: {client.get('business_hours','')}
Booking URL: {client.get('booking_url','')}
Emergency policy: {client.get('emergency_policy','')}

Analyze the customer's latest message and produce a concise customer-facing reply.

Rules:
- Never invent prices, discounts, warranties, arrival times, or availability.
- Ask at most one question in the reply unless you are giving emergency guidance.
- If customer asks to stop, set intent=opt_out and do not market further.
- If there is a safety-critical situation, set urgency=emergency and human_handoff=true.
- Complaints, refund/legal threats, or explicit requests for a person require human handoff.
- If they want to schedule, set wants_booking=true. You may include the configured booking URL.
- Keep the reply natural, short, and appropriate for SMS.

Customer message:
{message}
""".strip()

    from openai import OpenAI
    client_api = OpenAI(api_key=settings.openai_api_key)
    try:
        resp = client_api.responses.create(
            model=settings.openai_model,
            input=prompt,
            text={
                "format": {
                    "type": "json_schema",
                    "name": "lead_analysis",
                    "strict": True,
                    "schema": SCHEMA,
                }
            },
        )
        return json.loads(resp.output_text)
    except Exception:
        # Production resilience: never block a customer response because the AI provider is unavailable.
        return heuristic_analysis(message, client.get("booking_url",""))
