"""One-off test: confirms we can connect to the Supabase Postgres database."""
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

url = os.getenv("DATABASE_URL")
if not url:
    raise SystemExit("DATABASE_URL not set — check your .env file.")

try:
    conn = psycopg2.connect(url)
    cur = conn.cursor()
    cur.execute("SELECT version();")
    print("Connected successfully!")
    print(cur.fetchone()[0])
    conn.close()
except Exception as e:
    print(f"Connection failed: {e}")