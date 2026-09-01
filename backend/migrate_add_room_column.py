"""
One-off migration: adds the 'room' column to the existing cameras table
without losing any data (staff registrations, camera configs, event
history, etc. are all untouched).

Run this ONCE from the backend/ folder, with the server stopped:

    python migrate_add_room_column.py

Safe to run multiple times - it checks whether the column already exists
before trying to add it.
"""
import sqlite3
from app.config import env

# Reuses the same DATABASE_URL your app already uses. Only handles the
# sqlite:/// case, which is what this project defaults to.
db_url = env.DATABASE_URL
if not db_url.startswith("sqlite"):
    raise SystemExit(
        f"This script only handles sqlite DATABASE_URL values, got: {db_url}\n"
        "If you're on Postgres/MySQL, run the equivalent ALTER TABLE manually."
    )

db_path = db_url.split("///")[-1]
print(f"Using database file: {db_path}")

conn = sqlite3.connect(db_path)
cur = conn.cursor()

cur.execute("PRAGMA table_info(cameras)")
existing_columns = {row[1] for row in cur.fetchall()}

if "room" in existing_columns:
    print("Column 'room' already exists - nothing to do.")
else:
    cur.execute("ALTER TABLE cameras ADD COLUMN room VARCHAR")
    conn.commit()
    print("Added 'room' column to cameras table.")

conn.close()
