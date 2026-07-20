"""
Contact enrichment: re-queries LocationIQ with extratags to pull phone numbers
and websites from OpenStreetMap data, for good-fit clinics missing contact info.

Coverage is honest-but-partial: OSM only has contact details where volunteers
added them. Expect to fill maybe 30-50% — the rest stay manual lookups.

Usage:
    python enrich.py
"""
import time
import requests

from config import LOCATIONIQ_API_KEY
from db import get_connection

BASE_URL = "https://us1.locationiq.com/v1/search"
REQUEST_DELAY = 0.6


def lookup_contact(name, city):
    """Search LocationIQ for this clinic with extratags to get phone/website."""
    resp = requests.get(BASE_URL, params={
        "key": LOCATIONIQ_API_KEY,
        "format": "json",
        "q": f"{name}, {city}",
        "countrycodes": "za",
        "limit": 1,
        "extratags": 1,
    }, timeout=15)
    time.sleep(REQUEST_DELAY)

    if resp.status_code == 404:
        return None, None
    resp.raise_for_status()
    results = resp.json()
    if not results:
        return None, None

    extratags = results[0].get("extratags") or {}
    phone = (
        extratags.get("phone")
        or extratags.get("contact:phone")
        or extratags.get("contact:mobile")
    )
    website = (
        extratags.get("website")
        or extratags.get("contact:website")
        or extratags.get("contact:facebook")
        or extratags.get("contact:instagram")
    )
    return phone, website


def run_enrichment():
    if not LOCATIONIQ_API_KEY:
        raise SystemExit("LOCATIONIQ_API_KEY not set — check your .env file.")

    conn = get_connection()
    rows = conn.execute(
        """
        SELECT id, name, city FROM clinics
        WHERE fit_label = 'good_fit'
          AND outreach_status != 'duplicate'
          AND (phone IS NULL AND website IS NULL)
        ORDER BY fit_score DESC
        """
    ).fetchall()

    if not rows:
        print("No clinics needing enrichment.")
        return

    print(f"Enriching {len(rows)} clinic(s)...\n")

    found = 0
    for i, row in enumerate(rows, 1):
        print(f"[{i}/{len(rows)}] {row['name']}...", end=" ", flush=True)
        try:
            phone, website = lookup_contact(row["name"], row["city"])
            if phone or website:
                conn.execute(
                    "UPDATE clinics SET phone = ?, website = ? WHERE id = ?",
                    (phone, website, row["id"]),
                )
                conn.commit()
                parts = []
                if phone:
                    parts.append(f"phone: {phone}")
                if website:
                    parts.append(f"web: {website}")
                print(" | ".join(parts))
                found += 1
            else:
                print("nothing found")
        except requests.exceptions.RequestException as e:
            print(f"!! failed: {e}")

    conn.close()
    print(f"\nDone. Found contact info for {found}/{len(rows)} clinic(s).")


if __name__ == "__main__":
    run_enrichment()