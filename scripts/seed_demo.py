import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from app.database import init_db, one, execute, utcnow

init_db()
if not one("SELECT id FROM clients LIMIT 1"):
    cid = execute("""
    INSERT INTO clients(business_name,phone,email,service_area,services,services_not_offered,business_hours,booking_url,
    emergency_policy,financing_info,promotions,created_at)
    VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
    """,(
      "South Bay Demo Plumbing","+13105550123","owner@example.com",
      "Torrance, Redondo Beach, Carson, Lomita",
      "Leak repair, drain cleaning, water heaters, fixture installation",
      "Septic pumping",
      "Mon-Fri 7am-6pm; Sat 8am-2pm",
      "https://calendly.com/pelagicauto",
      "For immediate danger, gas leak, fire, or electrical hazard, contact emergency services/utility first.",
      "Financing subject to approval.",
      "",
      utcnow()
    ))
else:
    cid = one("SELECT id FROM clients LIMIT 1")["id"]

if not one("SELECT id FROM leads LIMIT 1"):
    now=utcnow()
    demo = [
      ("Alex Rivera","+13105550155","Water heater replacement","90503","high","urgent","booking_requested","Google LSA"),
      ("Jordan Lee","+13105550166","Drain cleaning","90277","medium","normal","qualified","Website"),
      ("Taylor Kim","+13105550177","Leak repair","90717","unknown","normal","estimate_sent","Missed Call"),
    ]
    for name,phone,svc,z,intent,urgency,stage,source in demo:
        execute("""INSERT INTO leads(client_id,name,phone,service_requested,zip_code,intent,urgency,stage,source,created_at,updated_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                (cid,name,phone,svc,z,intent,urgency,stage,source,now,now))
print("Demo data seeded.")
