import os
from dataclasses import dataclass

def _bool(name: str, default: bool=False) -> bool:
    return os.getenv(name, str(default)).lower() in {"1","true","yes","on"}

@dataclass(frozen=True)
class Settings:
    env: str = os.getenv("PELAGIC_ENV", "development")
    admin_token: str = os.getenv("PELAGIC_ADMIN_TOKEN", "change-me")
    webhook_secret: str = os.getenv("PELAGIC_WEBHOOK_SECRET", "change-me-too")
    database_path: str = os.getenv("DATABASE_PATH", "./pelagic.db")

    ghl_enabled: bool = _bool("GHL_ENABLED", False)
    ghl_api_base: str = os.getenv("GHL_API_BASE", "https://services.leadconnectorhq.com")
    ghl_api_version: str = os.getenv("GHL_API_VERSION", "v3")
    ghl_private_token: str = os.getenv("GHL_PRIVATE_TOKEN", "")
    ghl_location_id: str = os.getenv("GHL_LOCATION_ID", "")
    ghl_pipeline_id: str = os.getenv("GHL_PIPELINE_ID", "")
    ghl_stage_new: str = os.getenv("GHL_STAGE_NEW", "")
    ghl_stage_qualified: str = os.getenv("GHL_STAGE_QUALIFIED", "")
    ghl_stage_booked: str = os.getenv("GHL_STAGE_BOOKED", "")
    ghl_stage_estimate: str = os.getenv("GHL_STAGE_ESTIMATE", "")
    ghl_stage_won: str = os.getenv("GHL_STAGE_WON", "")
    ghl_from_number: str = os.getenv("GHL_FROM_NUMBER", "")

    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-5-mini")

settings = Settings()
