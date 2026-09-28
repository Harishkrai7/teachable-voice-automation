"""
config.py — Centralised configuration.
Reads from .env file (local dev) or environment variables (Cloud Run).
Never hardcode secrets here.
"""
import os
from dotenv import load_dotenv

# Load .env file if it exists (only used locally; Cloud Run uses env vars directly)
load_dotenv()

# ── Gemini AI ────────────────────────────────────────────────────────────────
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

# ── App metadata ─────────────────────────────────────────────────────────────
APP_VERSION: str = "1.0.0"
SCHEMA_VERSION: str = "v1"

# ── Flow storage ─────────────────────────────────────────────────────────────
# Local dev: flows/ folder. Cloud Run: ephemeral (upgrade to Firestore for demo day).
FLOWS_DIR: str = os.getenv("FLOWS_DIR", "flows")

# ── Safety: keywords that always trigger a STOP decision ─────────────────────
SENSITIVE_SCREEN_KEYWORDS = [
    "payment", "pay now", "otp", "one time password",
    "enter password", "login", "sign in", "pin",
    "credit card", "debit card", "cvv", "upi pin",
    "authenticate", "biometric", "fingerprint",
]

# ── AI confidence threshold ──────────────────────────────────────────────────
# If AI confidence is below this, return ASK_USER instead of executing.
MIN_CONFIDENCE_THRESHOLD: float = 0.70
