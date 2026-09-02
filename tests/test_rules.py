from app.services.rules import is_opt_out, heuristic_analysis, estimate_followup_schedule

def test_opt_out():
    assert is_opt_out("STOP")
    assert is_opt_out("unsubscribe please")
    assert not is_opt_out("Please stop the leak")

def test_high_intent():
    a = heuristic_analysis("Can I book for tomorrow?", "https://book.test")
    assert a["intent"] == "high"
    assert a["wants_booking"] is True
    assert "https://book.test" in a["reply"]

def test_emergency():
    a = heuristic_analysis("I smell a gas leak")
    assert a["urgency"] == "emergency"
    assert a["human_handoff"] is True

def test_estimate_schedule():
    rows = estimate_followup_schedule()
    assert len(rows) == 3
    assert rows[0][1] == "estimate_1"
