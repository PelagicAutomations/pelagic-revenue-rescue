def missed_call_message(client: dict, first_name: str = "") -> str:
    who = f" {first_name}" if first_name else ""
    return (
        f"Hi{who}, this is {client['business_name']}. Sorry we missed your call. "
        "What can we help you with today? Reply STOP to unsubscribe."
    )

def estimate_message(client: dict, kind: str, lead: dict) -> str:
    first = lead.get("name","").split(" ")[0] if lead.get("name") else ""
    prefix = f"Hi {first}, " if first else "Hi, "
    svc = lead.get("service_requested") or "your project"
    if kind == "estimate_1":
        return f"{prefix}{client['business_name']} here. Just checking that you received the estimate for {svc}. Any questions I can help with?"
    if kind == "estimate_2":
        return "Wanted to follow up on your estimate. If timing, scope, or scheduling is holding things up, tell me what you're considering and I'll help."
    return "Should we keep this estimate open, revisit it later, or close it out for now?"
