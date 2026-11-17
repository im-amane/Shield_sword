"""SQLite-backed storage for group protection settings and warning records."""
from __future__ import annotations

import json
import os
import sqlite3
from io import BytesIO
import time
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(os.getenv("DATABASE_PATH", "data/aniworld.sqlite3"))


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH, timeout=10)
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute("PRAGMA busy_timeout=5000")
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
CREATE TABLE IF NOT EXISTS copyright_settings (
    chat_id INTEGER PRIMARY KEY,
    enabled INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS security_audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    chat_id INTEGER NOT NULL,
    actor_id INTEGER,
    action TEXT NOT NULL,
    target_id INTEGER,
    details TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_security_audit_chat_id ON security_audit(chat_id, id DESC);
"""

_initialized_path: Path | None = None
_CACHE_TTL = 15.0
_feature_cache: dict[tuple[str, int], tuple[float, bool]] = {}
_badwords_cache: dict[int, tuple[float, set[str]]] = {}
_domains_cache: dict[int, tuple[float, set[str]]] = {}


def _cache_valid(entry) -> bool:
    return entry is not None and time.monotonic() - entry[0] < _CACHE_TTL


@contextmanager
def _connection():
    global _initialized_path
    db = _connect()
    try:
        if _initialized_path != DB_PATH:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("PRAGMA synchronous=NORMAL")
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
    _feature_cache.pop((feature, chat_id), None)
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
    key = (feature, chat_id)
    cached = _feature_cache.get(key)
    if _cache_valid(cached):
        return cached[1]
    with _connection() as db:
        row = db.execute(f"SELECT enabled FROM {table} WHERE chat_id=?", (chat_id,)).fetchone()
    value = bool(row[0]) if row else True
    _feature_cache[key] = (time.monotonic(), value)
    return value


def add_badword(chat_id: int, word: str) -> None:
    _badwords_cache.pop(chat_id, None)
    with _connection() as db:
        db.execute("INSERT OR IGNORE INTO badwords(chat_id, word) VALUES (?, ?)", (chat_id, word))


def remove_badword(chat_id: int, word: str) -> None:
    _badwords_cache.pop(chat_id, None)
    with _connection() as db:
        db.execute("DELETE FROM badwords WHERE chat_id=? AND word=?", (chat_id, word))


def get_badwords(chat_id: int) -> set[str]:
    cached = _badwords_cache.get(chat_id)
    if _cache_valid(cached):
        return set(cached[1])
    with _connection() as db:
        rows = db.execute("SELECT word FROM badwords WHERE chat_id=? ORDER BY word", (chat_id,)).fetchall()
    value = {str(row[0]) for row in rows}
    _badwords_cache[chat_id] = (time.monotonic(), value)
    return set(value)


def add_allowed_domain(chat_id: int, domain: str) -> None:
    _domains_cache.pop(chat_id, None)
    with _connection() as db:
        db.execute("INSERT OR IGNORE INTO allowed_domains(chat_id, domain) VALUES (?, ?)", (chat_id, domain))


def remove_allowed_domain(chat_id: int, domain: str) -> None:
    _domains_cache.pop(chat_id, None)
    with _connection() as db:
        db.execute("DELETE FROM allowed_domains WHERE chat_id=? AND domain=?", (chat_id, domain))


def get_allowed_domains(chat_id: int) -> set[str]:
    cached = _domains_cache.get(chat_id)
    if _cache_valid(cached):
        return set(cached[1])
    with _connection() as db:
        rows = db.execute("SELECT domain FROM allowed_domains WHERE chat_id=? ORDER BY domain", (chat_id,)).fetchall()
    value = {str(row[0]) for row in rows}
    _domains_cache[chat_id] = (time.monotonic(), value)
    return set(value)


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


def record_audit_event(chat_id: int, action: str, actor_id: int | None = None,
                       target_id: int | None = None, details: str = "") -> None:
    """Append a bounded, non-secret security event to the audit trail."""
    safe_details = str(details).replace("\\x00", "")[:500]
    with _connection() as db:
        db.execute(
            "INSERT INTO security_audit(chat_id, actor_id, action, target_id, details) VALUES (?, ?, ?, ?, ?)",
            (chat_id, actor_id, action[:80], target_id, safe_details),
        )
        db.execute(
            "DELETE FROM security_audit WHERE id NOT IN "
            "(SELECT id FROM security_audit ORDER BY id DESC LIMIT 5000)"
        )


def get_audit_events(limit: int = 20) -> list[dict]:
    """Return newest security events, capped to a safe maximum."""
    limit = max(1, min(int(limit), 100))
    with _connection() as db:
        rows = db.execute(
            "SELECT created_at, chat_id, actor_id, action, target_id, details "
            "FROM security_audit ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(created_at=row[0], chat_id=row[1], actor_id=row[2],
                 action=row[3], target_id=row[4], details=row[5]) for row in rows]


def create_database_backup() -> bytes:
    """Create a consistent SQLite backup snapshot in memory."""
    source = _connect()
    target = sqlite3.connect(":memory:")
    try:
        source.backup(target)
        snapshot = BytesIO()
        # Serialize returns the complete consistent database image.
        snapshot.write(target.serialize())
        return snapshot.getvalue()
    finally:
        target.close()
        source.close()


def set_copyright_enabled(chat_id: int, enabled: bool) -> None:
    with _connection() as db:
        db.execute(
            "INSERT INTO copyright_settings(chat_id, enabled) VALUES (?, ?) "
            "ON CONFLICT(chat_id) DO UPDATE SET enabled=excluded.enabled",
            (chat_id, int(enabled)),
        )


def is_copyright_enabled(chat_id: int) -> bool:
    """Copyright media filtering is enabled by default for every group."""
    with _connection() as db:
        row = db.execute(
            "SELECT enabled FROM copyright_settings WHERE chat_id=?", (chat_id,)
        ).fetchone()
    return bool(row[0]) if row else True
