"""
Database layer for the MarkeTan Prospecting Agent — now backed by Postgres
(Supabase) instead of local SQLite.

A thin compatibility wrapper lets the rest of the codebase keep using
sqlite-style `?` placeholders and `conn.execute(...)` calls without needing
to be rewritten — this class translates them to Postgres under the hood.
"""
import psycopg2
import psycopg2.extras

from config import DATABASE_URL

SCHEMA = """
CREATE TABLE IF NOT EXISTS clinics (
    id SERIAL PRIMARY KEY,

    place_id TEXT UNIQUE,
    name TEXT NOT NULL,
    address TEXT,
    city TEXT,
    phone TEXT,
    website TEXT,

    search_keyword TEXT,
    found_at TIMESTAMP DEFAULT NOW(),

    fit_score INTEGER,
    fit_label TEXT,
    fit_reasoning TEXT,

    outreach_status TEXT DEFAULT 'not_contacted',
    outreach_message TEXT,
    outreach_sent_at TIMESTAMP,

    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_fit_label ON clinics(fit_label);
CREATE INDEX IF NOT EXISTS idx_outreach_status ON clinics(outreach_status);
"""


class PGConnection:
    """
    Wraps a psycopg2 connection so existing sqlite-style call patterns
    (conn.execute("...WHERE id = ?", (val,)).fetchall()) keep working.
    """
    def __init__(self, real_conn):
        self._conn = real_conn

    def execute(self, sql, params=None):
        cur = self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        pg_sql = sql.replace("?", "%s")
        cur.execute(pg_sql, params or ())
        return cur

    def executescript(self, sql):
        cur = self._conn.cursor()
        cur.execute(sql)
        self._conn.commit()

    def commit(self):
        self._conn.commit()

    def close(self):
        self._conn.close()


def get_connection():
    if not DATABASE_URL:
        raise SystemExit("DATABASE_URL not set — check your .env file.")
    real_conn = psycopg2.connect(DATABASE_URL)
    return PGConnection(real_conn)


def init_db():
    conn = get_connection()
    conn.executescript(SCHEMA)
    conn.close()
    print("Database ready (Postgres/Supabase).")


def insert_clinic(conn, place_id, name, address, city, search_keyword):
    """
    Insert a clinic found via search. Ignores duplicates (same place_id).
    Returns True if a new row was inserted, False if it already existed.
    """
    cur = conn.execute(
        """
        INSERT INTO clinics (place_id, name, address, city, search_keyword)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT (place_id) DO NOTHING
        """,
        (place_id, name, address, city, search_keyword),
    )
    conn.commit()
    return cur.rowcount > 0


def count_clinics(conn):
    return conn.execute("SELECT COUNT(*) AS n FROM clinics").fetchone()["n"]


def mark_duplicates(conn):
    """
    Groups by (name, city), keeps the highest-fit_score row per group,
    marks the rest outreach_status='duplicate'. Returns count marked.
    """
    rows = conn.execute(
        """
        SELECT id, name, city, fit_score
        FROM clinics
        WHERE outreach_status = 'not_contacted'
        ORDER BY name, city, fit_score DESC
        """
    ).fetchall()

    seen = set()
    duplicate_ids = []
    for row in rows:
        key = (row["name"].strip().lower(), row["city"])
        if key in seen:
            duplicate_ids.append(row["id"])
        else:
            seen.add(key)

    for dup_id in duplicate_ids:
        conn.execute(
            "UPDATE clinics SET outreach_status = 'duplicate' WHERE id = ?",
            (dup_id,),
        )
    conn.commit()
    return len(duplicate_ids)


if __name__ == "__main__":
    init_db()