"""
Central configuration for the MarkeTan Prospecting Agent.

Keep all "things you'll want to tweak" in one place so later steps
(search, scoring, outreach) don't hardcode values scattered across files.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


def _get_secret(key):
    """
    Reads a secret from Streamlit Cloud's secrets manager if available
    (when deployed), otherwise falls back to the local .env file.
    """
    try:
        import streamlit as st
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return os.getenv(key)


# --- API keys (Step 2+ will use these) ---
# Both free tier, no credit card required:
#   Gemini key:     https://aistudio.google.com/apikey
#   LocationIQ key: https://locationiq.com (free signup, ~5,000 requests/day)
GEMINI_API_KEY = _get_secret("GEMINI_API_KEY")
LOCATIONIQ_API_KEY = _get_secret("LOCATIONIQ_API_KEY")
DATABASE_URL = _get_secret("DATABASE_URL")

# --- Paths ---
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "prospects.db"

# --- Gemini model for scoring / outreach (Step 3+) ---
# Flash is the free-tier workhorse — fast, generous quota, well-suited to
# structured tasks like fit-scoring and short outreach drafts.
GEMINI_MODEL = "gemini-3.1-flash-lite"
# --- ICP search targets ---
# Cities to search. Start narrow (where Tanita can realistically
# service clients in person if needed), expand later.
TARGET_CITIES = [
    "Pretoria",
    "Johannesburg",
    "Centurion",
]

# Search keywords — the kinds of practices MarkeTan is built for.
# Based on the "wellness and healthcare clinics" ICP in the company profile.
SEARCH_KEYWORDS = [
    "wellness clinic",
    "medical spa",
    "physiotherapy clinic",
    "aesthetic clinic",
    "chiropractic clinic",
    "dental clinic",
]

# ICP disqualifiers (used in scoring prompts, Step 3) — pulled directly
# from the "Ideal Clients" slide of the MarkeTan company profile.
ICP_GOOD_FIT = [
    "Wellness or healthcare clinic",
    "1-3 locations",
    "Has administrative staff to handle enquiries",
    "Looking for predictable patient acquisition",
    "Willing to invest in structured marketing systems",
]

ICP_DISQUALIFIERS = [
    "Brand new clinic without operational systems",
    "No marketing budget",
    "Unwilling to follow structured marketing processes",
]

# --- MarkeTan positioning (from company profile) — used in outreach drafts ---
MARKETAN_PITCH = (
    "MarkeTan is a South African marketing consultancy that helps wellness and "
    "healthcare clinics generate consistent, trackable patient enquiries through "
    "structured patient acquisition systems — targeted advertising, content, and "
    "funnel tracking — rather than vanity metrics like likes or impressions. "
    "Packages start at R6,500/month covering social media management and content "
    "planning, scaling up to full patient-acquisition advertising and campaign "
    "optimization for clinics ready to invest in predictable growth."
)

MARKETAN_SENDER_NAME = "Tanita Haripersad"
MARKETAN_SENDER_TITLE = "Founder & Marketing Consultant, MarkeTan"
