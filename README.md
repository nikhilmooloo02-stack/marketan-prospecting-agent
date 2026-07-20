# MarkeTan Prospecting Agent

Finds and qualifies South African wellness/healthcare clinics as prospective
MarkeTan clients, using MarkeTan's own ICP criteria from the company profile.

## Build plan (step by step)

- [x] Step 1: Project scaffold, config, database schema  <-- YOU ARE HERE
- [ ] Step 2: Clinic search (LocationIQ API) — pulls candidate clinics by city + keyword
- [ ] Step 3: Fit scoring (Gemini API) — scores each clinic against the ICP
- [ ] Step 4: Outreach drafting (Gemini API) — personalized first-touch messages
- [ ] Step 5: Export / review workflow (CSV + simple status tracking)

## Why SQLite, not Postgres

This is a single-user tool with no concurrent load. SQLite is a single file,
needs no server, and is trivial to migrate to Postgres later if MarkeTan
scales into a multi-user CRM. Don't build for a scaling problem that doesn't
exist yet.

## Setup (Windows / PowerShell + Claude Code)

```powershell
# From the project folder in VS Code / Claude Code terminal:
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Copy the example env file and fill in your keys
copy .env.example .env
# Then edit .env in VS Code and add:
#   GEMINI_API_KEY=...
#   LOCATIONIQ_API_KEY=...   (added in Step 2)

# Initialize the database
python db.py
```

You'll need (both genuinely free, no credit card):
- A Gemini API key: aistudio.google.com/apikey — for scoring/outreach (Step 3+)
- A LocationIQ API key: locationiq.com (free signup, ~5,000 requests/day) — for clinic search (Step 2)

Note: Google's own Places API dropped its free tier in Feb 2025 (now ~$275/month
minimum), so LocationIQ (built on OpenStreetMap data) is the free substitute.
Coverage for SA metro areas is solid; you just don't get Google's star ratings/
review counts, which OSM doesn't track.

## ICP criteria (from MarkeTan company profile)

**Good fit:**
- Wellness or healthcare clinic
- 1–3 locations
- Has administrative staff (implies some enquiry-handling capacity)
- Looking for predictable patient acquisition
- Willing to invest in structured marketing

**Not a fit:**
- Brand new clinic with no operational systems yet
- No marketing budget
- Unlikely to follow a structured process
