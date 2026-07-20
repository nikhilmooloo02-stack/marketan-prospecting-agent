"""
One-off migration: copies all clinic rows from the local SQLite database
(data/prospects.db) into the new Postgres (Supabase) database.

Run once, after db.py's schema has been created on Postgres.
Safe to re-run: uses ON CONFLICT (place_id) DO NOTHING, so it won't
duplicate rows if run twice.
"""
import sqlite3
from pathlib import Path

from db import get_connection

SQLITE_PATH = Path(__file__).parent / "data" / "prospects.db"

COLUMNS = [
    "place_id", "name", "address", "city", "phone", "website",
    "search_keyword", "fit_score", "fit_label", "fit_reasoning",
    "outreach_status", "outreach_message", "notes",
]


def migrate():
    if not SQLITE_PATH.exists():
        raise SystemExit(f"No local SQLite database found at {SQLITE_PATH}")

    sqlite_conn = sqlite3.connect(SQLITE_PATH)
    sqlite_conn.row_factory = sqlite3.Row
    rows = sqlite_conn.execute(f"SELECT {', '.join(COLUMNS)} FROM clinics").fetchall()
    sqlite_conn.close()

    print(f"Found {len(rows)} clinic(s) in local SQLite database.")

    pg_conn = get_connection()
    placeholders = ", ".join(["?"] * len(COLUMNS))
    col_list = ", ".join(COLUMNS)

    migrated = 0
    for row in rows:
        values = tuple(row[col] for col in COLUMNS)
        cur = pg_conn.execute(
            f"""
            INSERT INTO clinics ({col_list})
            VALUES ({placeholders})
            ON CONFLICT (place_id) DO NOTHING
            """,
            values,
        )
        if cur.rowcount > 0:
            migrated += 1
    pg_conn.commit()
    pg_conn.close()

    print(f"Migrated {migrated} new clinic(s) into Postgres.")
    print(f"({len(rows) - migrated} were already present or skipped.)")


if __name__ == "__main__":
    migrate()