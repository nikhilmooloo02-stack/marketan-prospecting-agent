"""
Clinic search via LocationIQ (OpenStreetMap-based, free tier).

LocationIQ's Search API is a geocoder, not a category-based "find every
business" search like Google Places was. It matches on name/address text,
so results depend on how clinics are tagged in OpenStreetMap. It's a solid
free starting point, not a complete directory — expect to supplement with
other sources later (LinkedIn, referrals, local directories).

Free plan rate limit: 2 requests/second. This module paces itself accordingly.
"""
import time
import requests

from config import LOCATIONIQ_API_KEY, TARGET_CITIES, SEARCH_KEYWORDS

BASE_URL = "https://us1.locationiq.com/v1/search"
REQUEST_DELAY = 0.6  # seconds between calls, safely under the 2/sec free-plan cap


def _request(params):
    """Low-level GET wrapper with rate-limit pacing and basic error handling."""
    params = {**params, "key": LOCATIONIQ_API_KEY, "format": "json"}
    resp = requests.get(BASE_URL, params=params, timeout=15)
    time.sleep(REQUEST_DELAY)

    if resp.status_code == 404:
        return []
    resp.raise_for_status()
    return resp.json()


def search_clinics(keyword: str, city: str, limit: int = 20):
    """
    Search for clinics matching `keyword` in `city`.
    Returns a list of dicts: place_id, name, address, city.
    """
    query = f"{keyword}, {city}"
    results = _request({
        "q": query,
        "limit": limit,
        "addressdetails": 1,
        "dedupe": 1,
        "countrycodes": "za",
    })

    clinics = []
    for r in results:
        addr = r.get("address", {})
        name = addr.get("name") or r.get("display_name", "").split(",")[0]
        clinics.append({
            "place_id": f"{r.get('osm_type', '')}:{r.get('osm_id', r.get('place_id'))}",
            "name": name,
            "address": r.get("display_name", ""),
            "city": city,
        })
    return clinics


def run_search():
    """
    Runs every (keyword, city) combination from config and returns
    the combined, raw result list.
    """
    all_results = []
    total_calls = len(TARGET_CITIES) * len(SEARCH_KEYWORDS)
    call_num = 0

    for city in TARGET_CITIES:
        for keyword in SEARCH_KEYWORDS:
            call_num += 1
            print(f"[{call_num}/{total_calls}] Searching '{keyword}' in {city}...")
            try:
                results = search_clinics(keyword, city)
                print(f"    -> {len(results)} result(s)")
                all_results.extend(results)
            except requests.exceptions.RequestException as e:
                print(f"    !! Request failed: {e}")

    return all_results


if __name__ == "__main__":
    if not LOCATIONIQ_API_KEY:
        raise SystemExit("LOCATIONIQ_API_KEY not set — check your .env file.")

    results = run_search()
    print(f"\nTotal raw results across all searches: {len(results)}")
