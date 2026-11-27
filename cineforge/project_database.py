"""SQLite-backed project catalog with atomic per-project JSON payloads."""
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timezone


def _connect(database):
    path = Path(database)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute("""CREATE TABLE IF NOT EXISTS projects (
        slug TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        payload TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )""")
    return conn


def save_project_record(database, slug, name, payload):
    if not isinstance(payload, dict):
        raise TypeError("Project payload must be an object.")
    encoded = json.dumps(payload, ensure_ascii=False)
    updated = datetime.now(timezone.utc).isoformat()
    with _connect(database) as conn:
        conn.execute("""INSERT INTO projects(slug,name,payload,updated_at)
            VALUES(?,?,?,?) ON CONFLICT(slug) DO UPDATE SET
            name=excluded.name,payload=excluded.payload,updated_at=excluded.updated_at""",
            (str(slug), str(name), encoded, updated))
    return updated


def list_project_records(database):
    with _connect(database) as conn:
        rows = conn.execute("SELECT slug,name,updated_at FROM projects ORDER BY updated_at DESC").fetchall()
    return [{"slug": row[0], "name": row[1], "updated_at": row[2]} for row in rows]


def load_project_record(database, slug):
    with _connect(database) as conn:
        row = conn.execute("SELECT payload FROM projects WHERE slug=?", (str(slug),)).fetchone()
    if row is None:
        raise KeyError(f"Project not found: {slug}")
    data = json.loads(row[0])
    if not isinstance(data, dict) or not isinstance(data.get("scenes", []), list):
        raise ValueError("Stored project payload is invalid.")
    return data
