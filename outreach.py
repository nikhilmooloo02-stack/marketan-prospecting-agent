"""
Outreach message drafting for good-fit clinics, using Gemini.

Generates a short, personalized first-touch message per clinic and stores it
in outreach_message (status moves not_contacted -> drafted). Nothing is sent
automatically — these are drafts for Tanita to review and send herself.

Usage:
    python outreach.py         # drafts for all good-fit, not-yet-contacted clinics
    python outreach.py 5       # drafts for the first 5 only (good for testing)
"""
import sys
import time

from google import genai

from config import (
    GEMINI_API_KEY,
    GEMINI_MODEL,
    MARKETAN_PITCH,
    MARKETAN_SENDER_NAME,
    MARKETAN_SENDER_TITLE,
)
from db import get_connection, mark_duplicates

REQUEST_DELAY = 6.5  # same free-tier pacing as scorer.py

PROMPT_TEMPLATE = """You are drafting a short, warm first-touch outreach message on behalf \
of a South African marketing consultancy called MarkeTan, reaching out to a clinic that \
looks like a good potential client.

About MarkeTan:
{pitch}

Clinic being contacted:
Name: {name}
City: {city}
Why it looks like a good fit: {fit_reasoning}

Write a short message (80-120 words) suitable for email or WhatsApp. It should:
- Reference the clinic by name naturally
- NOT claim any prior familiarity with the clinic (no "I've been following you,"
  "I love what you do," or similar — this is a first-time cold outreach, be
  honest about that)
- Briefly mention MarkeTan's structured, measurable approach to patient acquisition
  (not vanity metrics)
- NOT invent specific numbers or claims about this clinic's current marketing —
  we don't have that information
- End with a soft, low-pressure call to action (e.g. offering a short chat)
- Sign off as "{sender_name}, {sender_title}"

Respond with ONLY the message text, no preamble, no explanation, no markdown formatting.
"""


def draft_message(client, name, city, fit_reasoning):
    prompt = PROMPT_TEMPLATE.format(
        pitch=MARKETAN_PITCH,
        name=name,
        city=city,
        fit_reasoning=fit_reasoning or "general fit with MarkeTan's target client profile",
        sender_name=MARKETAN_SENDER_NAME,
        sender_title=MARKETAN_SENDER_TITLE,
    )
    response = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
    return response.text.strip()


def run_outreach(limit=None):
    if not GEMINI_API_KEY:
        raise SystemExit("GEMINI_API_KEY not set — check your .env file.")

    client = genai.Client(api_key=GEMINI_API_KEY)
    conn = get_connection()

    dup_count = mark_duplicates(conn)
    if dup_count:
        print(f"Marked {dup_count} duplicate clinic entr{'y' if dup_count == 1 else 'ies'} — skipping those.\n")

    query = """
        SELECT id, name, city, fit_reasoning
        FROM clinics
        WHERE fit_label = 'good_fit' AND outreach_status = 'not_contacted'
        ORDER BY fit_score DESC
    """
    if limit:
        query += f" LIMIT {limit}"
    rows = conn.execute(query).fetchall()

    if not rows:
        print("No good-fit clinics awaiting outreach — nothing to draft.")
        return

    print(f"Drafting outreach for {len(rows)} clinic(s)... "
          f"(~{round(len(rows) * REQUEST_DELAY / 60, 1)} min)\n")

    drafted = 0
    for i, row in enumerate(rows, 1):
        print(f"[{i}/{len(rows)}] {row['name']} ({row['city']})...", end=" ", flush=True)
        try:
            message = draft_message(client, row["name"], row["city"], row["fit_reasoning"])
            conn.execute(
                """
                UPDATE clinics
                SET outreach_message = ?, outreach_status = 'drafted'
                WHERE id = ?
                """,
                (message, row["id"]),
            )
            conn.commit()
            print("drafted")
            drafted += 1
        except Exception as e:
            print(f"!! failed: {e}")

        time.sleep(REQUEST_DELAY)

    conn.close()
    print(f"\nDone. Drafted {drafted}/{len(rows)} outreach message(s).")


if __name__ == "__main__":
    limit_arg = int(sys.argv[1]) if len(sys.argv) > 1 else None
    run_outreach(limit=limit_arg)