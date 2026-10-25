import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


def save_review(path, record_key, details):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    event = {
        **details,
        "review_id": str(uuid4()),
        "saved_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    payload = json.dumps(event, ensure_ascii=False, allow_nan=False)

    with closing(sqlite3.connect(path, timeout=10)) as database:
        with database:
            database.execute(
                "CREATE TABLE IF NOT EXISTS reviews "
                "(sequence INTEGER PRIMARY KEY, record_key TEXT NOT NULL, "
                "payload TEXT NOT NULL)"
            )
            database.execute(
                "INSERT INTO reviews (record_key, payload) VALUES (?, ?)",
                (record_key, payload),
            )

    return event


def load_history(path, record_key):
    path = Path(path)
    if not path.exists():
        return []

    with closing(sqlite3.connect(path, timeout=10)) as database:
        with database:
            database.execute(
                "CREATE TABLE IF NOT EXISTS reviews "
                "(sequence INTEGER PRIMARY KEY, record_key TEXT NOT NULL, "
                "payload TEXT NOT NULL)"
            )
            rows = database.execute(
                "SELECT payload FROM reviews WHERE record_key = ? "
                "ORDER BY sequence",
                (record_key,),
            ).fetchall()

    return [json.loads(row[0]) for row in rows]