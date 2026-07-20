"""
MarkeTan Prospecting Agent — main entry point.

Step 2 (current): search LocationIQ for candidate clinics, store new ones
in the database, skip duplicates already found in a previous run.

Later steps will add: fit scoring (Gemini), outreach drafting (Gemini),
and CSV export for Tanita to review.
"""
from config import LOCATIONIQ_API_KEY
from db import get_connection, init_db, insert_clinic, count_clinics
from places_search import run_search


def main():
    if not LOCATIONIQ_API_KEY:
        raise SystemExit("LOCATIONIQ_API_KEY not set — check your .env file.")

    init_db()
    conn = get_connection()

    before = count_clinics(conn)
    print(f"Clinics in database before this run: {before}\n")

    results = run_search()

    new_count = 0
    for r in results:
        # search_keyword isn't tracked per-result here since run_search()
        # flattens across keywords; good enough for v1, revisit if useful.
        inserted = insert_clinic(
            conn,
            place_id=r["place_id"],
            name=r["name"],
            address=r["address"],
            city=r["city"],
            search_keyword=None,
        )
        if inserted:
            new_count += 1

    after = count_clinics(conn)
    print(f"\nDone. {new_count} new clinic(s) added.")
    print(f"Total clinics in database: {after}")

    conn.close()


if __name__ == "__main__":
    main()
