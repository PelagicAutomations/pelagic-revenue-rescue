import re
from datetime import datetime, timedelta, timezone

HIGH_INTENT = [
    "book", "schedule", "appointment", "how soon", "come today",
    "move forward", "next step", "ready", "send someone", "can you come"
]
OPT_OUT = {"stop", "unsubscribe", "cancel", "end", "quit", "stopall"}
COMPLAINT = ["refund", "lawyer", "attorney", "sue", "complaint", "manager", "supervisor"]
EMERGENCY = ["gas leak", "fire", "sparking", "arc", "smoke", "electrocution", "flooding badly"]

def normalized(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())

def is_opt_out(text: str) -> bool:
    t = normalized(text)
    return t in OPT_OUT or any(t.startswith(x + " ") for x in OPT_OUT)

def heuristic_analysis(text: str, booking_url: str = "") -> dict:
    t = normalized(text)
    if is_opt_out(t):
        return {
            "intent":"opt_out","urgency":"unknown","service_requested":"",
            "zip_code":"","wants_booking":False,"human_handoff":False,
            "reply":"Understood. You will no longer receive automated follow-up messages.",
            "summary":"Customer opted out."
        }

    if any(x in t for x in EMERGENCY):
        return {
            "intent":"emergency","urgency":"emergency","service_requested":"",
            "zip_code":"","wants_booking":False,"human_handoff":True,
            "reply":"If there is immediate danger, fire, a suspected gas leak, or an electrical hazard, contact emergency services or the appropriate utility first. I’ll also flag this for the team.",
            "summary":"Potential life-safety emergency; immediate human handoff."
        }

    handoff = any(x in t for x in COMPLAINT) or "human" in t or "person" in t
    high = any(x in t for x in HIGH_INTENT)
    zip_match = re.search(r"\b\d{5}(?:-\d{4})?\b", text or "")
    return {
        "intent":"high" if high else ("medium" if len(t) > 8 else "unknown"),
        "urgency":"urgent" if any(x in t for x in ["today","asap","urgent","right away"]) else "normal",
        "service_requested":"",
        "zip_code":zip_match.group(0) if zip_match else "",
        "wants_booking":high,
        "human_handoff":handoff,
        "reply": (
            f"I can help with that. You can book here: {booking_url}" if high and booking_url
            else "I can help with that. What service do you need, and what ZIP code is the property in?"
        ),
        "summary":"Heuristic lead analysis."
    }

def estimate_followup_schedule(now=None):
    now = now or datetime.now(timezone.utc)
    return [
        (now + timedelta(days=1), "estimate_1"),
        (now + timedelta(days=3), "estimate_2"),
        (now + timedelta(days=7), "estimate_final"),
    ]
