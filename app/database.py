import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from .config import settings

SCHEMA = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS clients (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  business_name TEXT NOT NULL,
  phone TEXT,
  email TEXT,
  service_area TEXT NOT NULL DEFAULT '',
  services TEXT NOT NULL DEFAULT '',
  services_not_offered TEXT NOT NULL DEFAULT '',
  business_hours TEXT NOT NULL DEFAULT '',
  booking_url TEXT NOT NULL DEFAULT '',
  emergency_policy TEXT NOT NULL DEFAULT '',
  financing_info TEXT NOT NULL DEFAULT '',
  promotions TEXT NOT NULL DEFAULT '',
  active INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS leads (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  client_id INTEGER NOT NULL,
  ghl_contact_id TEXT,
  ghl_opportunity_id TEXT,
  name TEXT NOT NULL DEFAULT '',
  phone TEXT NOT NULL DEFAULT '',
  email TEXT NOT NULL DEFAULT '',
  service_requested TEXT NOT NULL DEFAULT '',
  zip_code TEXT NOT NULL DEFAULT '',
  urgency TEXT NOT NULL DEFAULT 'unknown',
  intent TEXT NOT NULL DEFAULT 'unknown',
  stage TEXT NOT NULL DEFAULT 'new',
  source TEXT NOT NULL DEFAULT '',
  dnc INTEGER NOT NULL DEFAULT 0,
  human_handoff INTEGER NOT NULL DEFAULT 0,
  appointment_booked INTEGER NOT NULL DEFAULT 0,
  estimate_amount REAL,
  last_message TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY(client_id) REFERENCES clients(id)
);

CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  webhook_id TEXT UNIQUE,
  event_type TEXT NOT NULL,
  lead_id INTEGER,
  payload TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS followups (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  lead_id INTEGER NOT NULL,
  kind TEXT NOT NULL,
  due_at TEXT NOT NULL,
  message TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  created_at TEXT NOT NULL,
  sent_at TEXT,
  FOREIGN KEY(lead_id) REFERENCES leads(id)
);
"""

def utcnow():
    return datetime.now(timezone.utc).isoformat()

@contextmanager
def db():
    conn = sqlite3.connect(settings.database_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def init_db():
    with db() as conn:
        conn.executescript(SCHEMA)

def one(query: str, params=()):
    with db() as conn:
        row = conn.execute(query, params).fetchone()
        return dict(row) if row else None

def all_rows(query: str, params=()):
    with db() as conn:
        return [dict(r) for r in conn.execute(query, params).fetchall()]

def execute(query: str, params=()):
    with db() as conn:
        cur = conn.execute(query, params)
        return cur.lastrowid
