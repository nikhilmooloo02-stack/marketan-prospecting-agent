"""
Fit scoring for prospected clinics, using Gemini.

Reads clinics that haven't been scored yet, asks Gemini to assess fit against
MarkeTan's ICP criteria (from config.py), and writes fit_score / fit_label /
fit_reasoning back to the database.

Usage:
    python scorer.py           # scores all unscored clinics
    python scorer.py 5         # scores only the first 5 (good for testing)
"""
import json
import sys
import time

from google import genai

from config import GEMINI_API_KEY, GEMINI_MODEL, ICP_GOOD_FIT, ICP_DISQUALIFIERS
from db import get_connection

# Free tier is roughly 10 requests/minute — 6.5s spacing keeps us safely under that.
REQUEST_DELAY = 6.5

PROMPT_TEMPLATE = """You are helping a South African marketing consultancy called MarkeTan \
evaluate whether a business is a good prospective client.

MarkeTan's ideal client criteria (GOOD FIT):
{good_fit}

MarkeTan's disqualifiers (NOT A FIT):
{disqualifiers}

Business to evaluate:
Name: {name}
Address: {address}
City: {city}

Based only on the name and address (no other information is available), assess how
likely this business is to be a good fit for MarkeTan. The business name is often a
strong signal — e.g. "medical spa", "wellness clinic", "aesthetic clinic" suggest a
strong fit; a generic medical practice or unrelated business suggests a weaker fit.

Respond with ONLY a JSON object, no other text, in this exact format:
{{"fit_score": <integer 0-100>, "fit_label": "<good_fit|not_a_fit|unclear>", "fit_reasoning": "<one sentence>"}}
"""


def score_clinic(client, name, address, city):
    prompt = PROMPT_TEMPLATE.format(
        good_fit="\n".join(f"- {c}" for c in ICP_GOOD_FIT),
        disqualifiers="\n".join(f"- {c}" for c in ICP_DISQUALIFIERS),
        name=name,
        address=address or "",
        city=city or "",
    )
    response = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
    text = response.text.strip()

    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()

    return json.loads(text)


def run_scoring(limit=None):
    if not GEMINI_API_KEY:
        raise SystemExit("GEMINI_API_KEY not set — check your .env file.")

    client = genai.Client(api_key=GEMINI_API_KEY)
    conn = get_connection()

    query = "SELECT id, name, address, city FROM clinics WHERE fit_score IS NULL"
    if limit:
        query += f" LIMIT {limit}"
    rows = conn.execute(query).fetchall()

    if not rows:
        print("No unscored clinics found — everything's already scored.")
        return

    print(f"Scoring {len(rows)} clinic(s)... (~{round(len(rows) * REQUEST_DELAY / 60, 1)} min)\n")

    scored = 0
    for i, row in enumerate(rows, 1):
        print(f"[{i}/{len(rows)}] {row['name']}...", end=" ", flush=True)
        try:
            result = score_clinic(client, row["name"], row["address"], row["city"])
            conn.execute(
                """
                UPDATE clinics
                SET fit_score = ?, fit_label = ?, fit_reasoning = ?
                WHERE id = ?
                """,
                (result["fit_score"], result["fit_label"], result["fit_reasoning"], row["id"]),
            )
            conn.commit()
            print(f"-> {result['fit_label']} ({result['fit_score']})")
            scored += 1
        except Exception as e:
            print(f"!! failed: {e}")

        time.sleep(REQUEST_DELAY)

    conn.close()
    print(f"\nDone. Scored {scored}/{len(rows)} clinic(s).")


if __name__ == "__main__":
    limit_arg = int(sys.argv[1]) if len(sys.argv) > 1 else None
    run_scoring(limit=limit_arg)