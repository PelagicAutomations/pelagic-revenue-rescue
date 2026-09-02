from pydantic import BaseModel, Field
from typing import Optional

class ClientCreate(BaseModel):
    business_name: str
    phone: str = ""
    email: str = ""
    service_area: str = ""
    services: str = ""
    services_not_offered: str = ""
    business_hours: str = ""
    booking_url: str = ""
    emergency_policy: str = ""
    financing_info: str = ""
    promotions: str = ""

class LeadCreate(BaseModel):
    client_id: int
    name: str = ""
    phone: str = ""
    email: str = ""
    service_requested: str = ""
    zip_code: str = ""
    source: str = "manual"
    ghl_contact_id: str = ""

class IncomingMessage(BaseModel):
    lead_id: int
    message: str

class EstimateSent(BaseModel):
    lead_id: int
    amount: Optional[float] = None

class AIAnalysis(BaseModel):
    intent: str = Field(description="low, medium, high, opt_out, complaint, emergency, unknown")
    urgency: str = Field(description="low, normal, urgent, emergency, unknown")
    service_requested: str = ""
    zip_code: str = ""
    wants_booking: bool = False
    human_handoff: bool = False
    reply: str
    summary: str
