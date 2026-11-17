"""SQLite-backed storage for group protection settings and warning records."""
from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(os.getenv("DATABASE_PATH", "data/aniworld.sqlite3"))


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH, timeout=10)
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA foreign_keys=ON")
    return connection


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS warnings (
    chat_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    count INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (chat_id, user_id)
);
CREATE TABLE IF NOT EXISTS badword_settings (
    chat_id INTEGER PRIMARY KEY,
    enabled INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS badwords (
    chat_id INTEGER NOT NULL,
    word TEXT NOT NULL,
    PRIMARY KEY (chat_id, word)
);
CREATE TABLE IF NOT EXISTS antilink_settings (
    chat_id INTEGER PRIMARY KEY,
    enabled INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS allowed_domains (
    chat_id INTEGER NOT NULL,
    domain TEXT NOT NULL,
    PRIMARY KEY (chat_id, domain)
);
CREATE TABLE IF NOT EXISTS pending_verifications (
    chat_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    correct_index INTEGER NOT NULL,
    expires_at INTEGER NOT NULL,
    permissions_json TEXT NOT NULL,
    PRIMARY KEY (chat_id, user_id)
);
CREATE TABLE IF NOT EXISTS raid_joins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER NOT NULL,
    joined_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_raid_joins_chat_time
    ON raid_joins(chat_id, joined_at);
CREATE TABLE IF NOT EXISTS raid_modes (
    chat_id INTEGER PRIMARY KEY,
    expires_at REAL NOT NULL
);
"""

_initialized_path: Path | None = None


@contextmanager
def _connection():
    global _initialized_path
    db = _connect()
    try:
        if _initialized_path != DB_PATH:
            db.executescript(SCHEMA_SQL)
            _initialized_path = DB_PATH
        yield db
        db.commit()
    finally:
        db.close()


def init_storage() -> None:
    """Initialize the schema; safe to call repeatedly."""
    with _connection():
        pass

def add_warning(chat_id: int, user_id: int) -> int:
    with _connection() as db:
        db.execute(
            """INSERT INTO warnings(chat_id, user_id, count) VALUES (?, ?, 1)
               ON CONFLICT(chat_id, user_id) DO UPDATE SET count = count + 1""",
            (chat_id, user_id),
        )
        row = db.execute(
            "SELECT count FROM warnings WHERE chat_id=? AND user_id=?",
            (chat_id, user_id),
        ).fetchone()
        return int(row[0])


def get_warnings(chat_id: int, user_id: int) -> int:
    with _connection() as db:
        row = db.execute(
            "SELECT count FROM warnings WHERE chat_id=? AND user_id=?",
            (chat_id, user_id),
        ).fetchone()
        return int(row[0]) if row else 0


def reset_warnings(chat_id: int, user_id: int) -> None:
    with _connection() as db:
        db.execute("DELETE FROM warnings WHERE chat_id=? AND user_id=?", (chat_id, user_id))


def set_feature_enabled(feature: str, chat_id: int, enabled: bool) -> None:
    table = {"badwords": "badword_settings", "antilink": "antilink_settings"}.get(feature)
    if table is None:
        raise ValueError("Unknown protection feature")
    with _connection() as db:
        db.execute(
            f"""INSERT INTO {table}(chat_id, enabled) VALUES (?, ?)
                ON CONFLICT(chat_id) DO UPDATE SET enabled=excluded.enabled""",
            (chat_id, int(enabled)),
        )


def is_feature_enabled(feature: str, chat_id: int) -> bool:
    table = {"badwords": "badword_settings", "antilink": "antilink_settings"}.get(feature)
    if table is None:
        raise ValueError("Unknown protection feature")
    with _connection() as db:
        row = db.execute(f"SELECT enabled FROM {table} WHERE chat_id=?", (chat_id,)).fetchone()
        return bool(row[0]) if row else True


def add_badword(chat_id: int, word: str) -> None:
    with _connection() as db:
        db.execute("INSERT OR IGNORE INTO badwords(chat_id, word) VALUES (?, ?)", (chat_id, word))


def remove_badword(chat_id: int, word: str) -> None:
    with _connection() as db:
        db.execute("DELETE FROM badwords WHERE chat_id=? AND word=?", (chat_id, word))


def get_badwords(chat_id: int) -> set[str]:
    with _connection() as db:
        rows = db.execute("SELECT word FROM badwords WHERE chat_id=? ORDER BY word", (chat_id,)).fetchall()
        return {str(row[0]) for row in rows}


def add_allowed_domain(chat_id: int, domain: str) -> None:
    with _connection() as db:
        db.execute("INSERT OR IGNORE INTO allowed_domains(chat_id, domain) VALUES (?, ?)", (chat_id, domain))


def remove_allowed_domain(chat_id: int, domain: str) -> None:
    with _connection() as db:
        db.execute("DELETE FROM allowed_domains WHERE chat_id=? AND domain=?", (chat_id, domain))


def get_allowed_domains(chat_id: int) -> set[str]:
    with _connection() as db:
        rows = db.execute("SELECT domain FROM allowed_domains WHERE chat_id=? ORDER BY domain", (chat_id,)).fetchall()
        return {str(row[0]) for row in rows}


def save_verification(chat_id: int, user_id: int, correct_index: int,
                      expires_at: int, permissions: dict) -> None:
    with _connection() as db:
        db.execute(
            """INSERT INTO pending_verifications
               (chat_id, user_id, correct_index, expires_at, permissions_json)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(chat_id, user_id) DO UPDATE SET
                 correct_index=excluded.correct_index,
                 expires_at=excluded.expires_at,
                 permissions_json=excluded.permissions_json""",
            (chat_id, user_id, correct_index, expires_at,
             json.dumps(permissions, separators=(",", ":"))),
        )


def get_verification(chat_id: int, user_id: int) -> dict | None:
    with _connection() as db:
        row = db.execute(
            """SELECT correct_index, expires_at, permissions_json
               FROM pending_verifications WHERE chat_id=? AND user_id=?""",
            (chat_id, user_id),
        ).fetchone()
    if not row:
        return None
    return {"correct_index": int(row[0]), "expires_at": int(row[1]),
            "permissions": json.loads(row[2])}


def delete_verification(chat_id: int, user_id: int) -> None:
    with _connection() as db:
        db.execute("DELETE FROM pending_verifications WHERE chat_id=? AND user_id=?",
                   (chat_id, user_id))


def cleanup_verifications(now: int) -> None:
    with _connection() as db:
        db.execute("DELETE FROM pending_verifications WHERE expires_at<=?", (now,))


def record_raid_joins(chat_id: int, count: int, joined_at: float,
                      window_seconds: int) -> int:
    with _connection() as db:
        db.execute("DELETE FROM raid_joins WHERE chat_id=? AND joined_at<?",
                   (chat_id, joined_at - window_seconds))
        db.executemany("INSERT INTO raid_joins(chat_id, joined_at) VALUES (?, ?)",
                       [(chat_id, joined_at)] * count)
        row = db.execute("SELECT COUNT(*) FROM raid_joins WHERE chat_id=? AND joined_at>=?",
                         (chat_id, joined_at - window_seconds)).fetchone()
        return int(row[0])


def get_raid_join_count(chat_id: int, now: float, window_seconds: int) -> int:
    with _connection() as db:
        row = db.execute("SELECT COUNT(*) FROM raid_joins WHERE chat_id=? AND joined_at>=?",
                         (chat_id, now - window_seconds)).fetchone()
        return int(row[0])


def get_raid_expiry(chat_id: int) -> float:
    with _connection() as db:
        row = db.execute("SELECT expires_at FROM raid_modes WHERE chat_id=?",
                         (chat_id,)).fetchone()
        return float(row[0]) if row else 0.0


def set_raid_expiry(chat_id: int, expires_at: float) -> None:
    with _connection() as db:
        db.execute("""INSERT INTO raid_modes(chat_id, expires_at) VALUES (?, ?)
                      ON CONFLICT(chat_id) DO UPDATE SET expires_at=excluded.expires_at""",
                   (chat_id, expires_at))


def clear_raid_expiry(chat_id: int) -> bool:
    with _connection() as db:
        cursor = db.execute("DELETE FROM raid_modes WHERE chat_id=?", (chat_id,))
        return cursor.rowcount > 0


def clear_raid_data() -> None:
    with _connection() as db:
        db.execute("DELETE FROM raid_joins")
        db.execute("DELETE FROM raid_modes")
