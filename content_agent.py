"""
Content Agent: generates social media content for MarkeTan's own channels.

Generates three content types per batch:
- educational: marketing tips/insights for clinic owners (positions MarkeTan
  as the expert; "structure over vanity metrics" angle)
- promotional: posts about MarkeTan's services and packages
- demo: sample patient-education content, showing prospects what MarkeTan
  would produce for THEIR clinic

Content is stored in the database for review on the dashboard. Nothing is
posted automatically — Tanita reviews, copies, posts, and marks as used.

Usage:
    python content_agent.py        # generates a standard weekly batch
    python content_agent.py 2      # generates 2 of each type (smaller test)
"""
import sys
import time

from google import genai

from config import GEMINI_API_KEY, GEMINI_MODEL, MARKETAN_PITCH
from db import get_connection

REQUEST_DELAY = 6.5

CONTENT_SCHEMA = """
CREATE TABLE IF NOT EXISTS content (
    id SERIAL PRIMARY KEY,
    content_type TEXT NOT NULL,      -- 'educational' | 'promotional' | 'demo'
    platform TEXT NOT NULL,          -- 'linkedin' | 'instagram' | 'facebook'
    body TEXT NOT NULL,
    status TEXT DEFAULT 'draft',     -- 'draft' | 'posted' | 'discarded'
    created_at TIMESTAMP DEFAULT NOW()
);
"""

# (content_type, platform, prompt) — each tuple generates one post per batch round
CONTENT_BRIEFS = [
    (
        "educational", "linkedin",
        "Write a LinkedIn post (100-180 words) for MarkeTan's page, giving clinic "
        "owners ONE practical, specific marketing insight. Angle: structured, "
        "measurable patient acquisition beats vanity metrics like likes. Be concrete "
        "(e.g. tracking cost-per-enquiry, follow-up speed on enquiries, Google "
        "Business Profile basics). Professional but warm tone. No hashtag spam — "
        "2-3 relevant hashtags max at the end.",
    ),
    (
        "educational", "instagram",
        "Write an Instagram caption (60-120 words) for MarkeTan's page, sharing one "
        "quick marketing tip for wellness clinic owners in South Africa. "
        "Conversational, punchy opening line. End with a light question to drive "
        "comments. 3-5 relevant hashtags.",
    ),
    (
        "promotional", "facebook",
        "Write a Facebook post (80-150 words) for MarkeTan, a South African marketing "
        "consultancy for wellness clinics. Softly promote the service: structured "
        "patient acquisition, measurable results, packages from R6,500/month. Include "
        "a clear but low-pressure call to action to get in touch. Avoid hype words "
        "like 'guaranteed' or unrealistic promises.",
    ),
    (
        "demo", "instagram",
        "Write a sample Instagram caption (60-120 words) that a wellness clinic could "
        "post for its patients — patient education content about ONE wellness/health "
        "topic (e.g. hydration, posture, skin care basics, recovery after treatment). "
        "This is a DEMO of MarkeTan's content work, so make it genuinely good: "
        "warm, credible, non-alarmist, no medical overclaims. 3-4 hashtags.",
    ),
]


def init_content_table(conn):
    conn.executescript(CONTENT_SCHEMA)


def generate_post(client, prompt):
    context = (
        f"About MarkeTan (for context, don't recite this verbatim):\n{MARKETAN_PITCH}\n\n"
        f"{prompt}\n\n"
        "IMPORTANT: Do NOT invent statistics, research findings, or specific claims "
        "(no 'research shows', 'studies find', or made-up percentages). Practical "
        "advice and general principles only — if a claim needs a source, leave it out.\n\n"
        "Respond with ONLY the post text, no preamble, no markdown headers."
    )
    response = client.models.generate_content(model=GEMINI_MODEL, contents=context)
    return response.text.strip()


def run_generation(rounds=1):
    if not GEMINI_API_KEY:
        raise SystemExit("GEMINI_API_KEY not set — check your .env file.")

    client = genai.Client(api_key=GEMINI_API_KEY)
    conn = get_connection()
    init_content_table(conn)

    total = len(CONTENT_BRIEFS) * rounds
    print(f"Generating {total} post(s)... (~{round(total * REQUEST_DELAY / 60, 1)} min)\n")

    created = 0
    n = 0
    for _ in range(rounds):
        for content_type, platform, prompt in CONTENT_BRIEFS:
            n += 1
            print(f"[{n}/{total}] {content_type} / {platform}...", end=" ", flush=True)
            try:
                body = generate_post(client, prompt)
                conn.execute(
                    "INSERT INTO content (content_type, platform, body) VALUES (?, ?, ?)",
                    (content_type, platform, body),
                )
                conn.commit()
                print("done")
                created += 1
            except Exception as e:
                print(f"!! failed: {e}")
            time.sleep(REQUEST_DELAY)

    conn.close()
    print(f"\nDone. Created {created}/{total} post(s) as drafts.")


if __name__ == "__main__":
    rounds_arg = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    run_generation(rounds=rounds_arg)