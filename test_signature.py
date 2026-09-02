from app.services.ghl import verify_ghl_signature

def test_bad_signature_rejected():
    assert verify_ghl_signature(b'{"test":true}', "AAAA") is False
