"""
Proposal Generator: creates a tailored MarkeTan proposal for a specific clinic,
using the packages and pricing math from the company profile.

Runs automatically for any clinic whose status is 'replied' and doesn't yet
have a proposal. Can also be run for a specific clinic by ID.

Usage:
    python proposal_agent.py           # generates for all 'replied' clinics missing one
    python proposal_agent.py 42        # generates for clinic id 42 specifically
"""
import sys
import time

from google import genai

from config import GEMINI_API_KEY, GEMINI_MODEL, MARKETAN_SENDER_NAME, MARKETAN_SENDER_TITLE
from db import get_connection

REQUEST_DELAY = 6.5

PROPOSAL_SCHEMA = """
CREATE TABLE IF NOT EXISTS proposals (
    id SERIAL PRIMARY KEY,
    clinic_id INTEGER REFERENCES clinics(id),
    package_recommended TEXT,
    body TEXT NOT NULL,
    status TEXT DEFAULT 'draft',
    created_at TIMESTAMP DEFAULT NOW()
);
"""

PACKAGES = """
FOUNDATION - R6,500/month:
- Marketing Consultation & Onboarding
- Monthly Patient-Focused Content Planning
- 1 Platform, 8 Posts/month
- Patient-Focused Caption Writing, Professional Content Design
- Content Scheduling & Publishing, Clinic Profile Optimization
- Basic Performance Reporting

GROWTH - R10,500/month (most clinics start here):
- Everything in Foundation, plus:
- 2 Platforms, 12 Posts/month
- Google Business Profile Management
- Monthly Strategy Meeting
- Detailed Performance Reporting

PERFORMANCE - R15,000/month:
- Everything in Growth, plus:
- 4 Platforms, 16 Posts/month
- Patient Acquisition Strategy
- Meta Patient Ads Management, Ad Creative & Copywriting
- Campaign Optimisation & CPL Improvement
- Patient Enquiry Tracking Setup, Priority Support
(Advertising spend excluded from all packages)

Example economics clinics can expect (illustrative, not a guarantee):
- Typical cost per enquiry: R120-R350
- Typical enquiry-to-booking conversion: 20-30%
- e.g. 40 enquiries at R180 avg cost (R7,200 ad spend) -> ~10 booked patients
"""


def init_proposals_table(conn):
    conn.executescript(PROPOSAL_SCHEMA)


def generate_proposal(client, clinic):
    prompt = f"""You are drafting a marketing services proposal on behalf of MarkeTan, \
a South African marketing consultancy for wellness and healthcare clinics.

Clinic: {clinic['name']}
City: {clinic['city']}
Why they're a good fit: {clinic['fit_reasoning']}

MarkeTan's packages:
{PACKAGES}

Write a proposal (250-350 words) that:
- Opens by referencing the clinic by name and their specific situation (from the fit reasoning)
- Recommends ONE package (Foundation, Growth, or Performance) that best fits a clinic like
  this, with brief reasoning for the recommendation — default to Growth unless there's a
  clear signal for Foundation (very small/new) or Performance (larger, ready for paid ads)
- Lists what's included in that package, in plain language (not just bullet-copied from
  the package list — make it relevant to their apparent situation)
- Includes the example economics as an ILLUSTRATIVE possibility, clearly labeled as an
  example and not a guaranteed outcome for this specific clinic
- Ends with a clear next step (e.g. a short call to finalize details)
- Signs off as "{MARKETAN_SENDER_NAME}, {MARKETAN_SENDER_TITLE}"
- Does NOT invent facts about the clinic beyond what's given
- Does NOT promise specific guaranteed results for this clinic
- Does NOT include unsubstantiated flattery about the clinic's reputation, authority,
  or brand strength unless that's explicitly part of the given fit reasoning — stick
  to what's actually known (name, location, general category)

Respond with ONLY the proposal text, no preamble, no markdown headers.
Then on a new line write "PACKAGE: " followed by just the package name you recommended
(Foundation, Growth, or Performance).
"""
    response = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
    text = response.text.strip()

    package = "Growth"
    if "PACKAGE:" in text:
        body, _, tail = text.rpartition("PACKAGE:")
        body = body.strip()
        package = tail.strip()
    else:
        body = text

    return body, package


def run_proposals(clinic_id=None):
    if not GEMINI_API_KEY:
        raise SystemExit("GEMINI_API_KEY not set — check your .env file.")

    client = genai.Client(api_key=GEMINI_API_KEY)
    conn = get_connection()
    init_proposals_table(conn)

    if clinic_id:
        rows = conn.execute(
            "SELECT id, name, city, fit_reasoning FROM clinics WHERE id = ?",
            (clinic_id,),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT c.id, c.name, c.city, c.fit_reasoning
            FROM clinics c
            WHERE c.outreach_status = 'replied'
              AND NOT EXISTS (SELECT 1 FROM proposals p WHERE p.clinic_id = c.id)
            """
        ).fetchall()

    if not rows:
        print("No clinics need a proposal right now.")
        return

    print(f"Generating {len(rows)} proposal(s)...\n")

    created = 0
    for i, row in enumerate(rows, 1):
        print(f"[{i}/{len(rows)}] {row['name']}...", end=" ", flush=True)
        try:
            body, package = generate_proposal(client, row)
            conn.execute(
                "INSERT INTO proposals (clinic_id, package_recommended, body) VALUES (?, ?, ?)",
                (row["id"], package, body),
            )
            conn.commit()
            print(f"done ({package})")
            created += 1
        except Exception as e:
            print(f"!! failed: {e}")
        time.sleep(REQUEST_DELAY)

    conn.close()
    print(f"\nDone. Created {created}/{len(rows)} proposal(s).")


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    run_proposals(clinic_id=int(arg) if arg else None)