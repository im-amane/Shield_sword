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
CREATE TABLE IF NOT EXISTS channel_media_settings (
    channel_id INTEGER PRIMARY KEY,
    enabled INTEGER NOT NULL DEFAULT 0
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
CREATE TABLE IF NOT EXISTS known_groups (
    chat_id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    last_seen TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS member_join_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER NOT NULL,
    chat_title TEXT NOT NULL,
    user_id INTEGER NOT NULL,
    username TEXT NOT NULL DEFAULT '',
    display_name TEXT NOT NULL DEFAULT '',
    joined_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_member_joins_chat_time
    ON member_join_events(chat_id, joined_at DESC);
CREATE TABLE IF NOT EXISTS security_incidents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    chat_id INTEGER NOT NULL,
    chat_title TEXT NOT NULL DEFAULT '',
    kind TEXT NOT NULL,
    severity TEXT NOT NULL DEFAULT 'medium',
    user_id INTEGER,
    username TEXT NOT NULL DEFAULT '',
    display_name TEXT NOT NULL DEFAULT '',
    details TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS automatic_backup_state (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    last_success_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS daily_report_state (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    last_success_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_security_incidents_time
    ON security_incidents(created_at DESC);
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


def get_expired_verifications(now: int, limit: int = 100) -> list[dict]:
    """Return pending challenges whose deadline has passed, without deleting them."""
    limit = max(1, min(int(limit), 500))
    with _connection() as db:
        rows = db.execute(
            """SELECT chat_id, user_id, expires_at FROM pending_verifications
               WHERE expires_at<=? ORDER BY expires_at LIMIT ?""",
            (now, limit),
        ).fetchall()
    return [
        {"chat_id": int(row[0]), "user_id": int(row[1]), "expires_at": int(row[2])}
        for row in rows
    ]


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



def register_group(chat_id: int, title: str) -> None:
    """Remember a group the bot has observed, without storing message content."""
    safe_title = str(title or "Telegram group")[:200]
    with _connection() as db:
        db.execute(
            """INSERT INTO known_groups(chat_id, title, last_seen)
               VALUES (?, ?, CURRENT_TIMESTAMP)
               ON CONFLICT(chat_id) DO UPDATE SET
                 title=excluded.title, last_seen=CURRENT_TIMESTAMP""",
            (chat_id, safe_title),
        )


def record_member_join(chat_id: int, chat_title: str, user_id: int,
                       username: str | None, display_name: str) -> None:
    """Store public Telegram profile fields and join time for defensive review."""
    with _connection() as db:
        db.execute(
            """INSERT INTO member_join_events
               (chat_id, chat_title, user_id, username, display_name)
               VALUES (?, ?, ?, ?, ?)""",
            (chat_id, str(chat_title or "Telegram group")[:200], user_id,
             str(username or "")[:64], str(display_name or "")[:160]),
        )
        db.execute(
            "DELETE FROM member_join_events WHERE id NOT IN "
            "(SELECT id FROM member_join_events ORDER BY id DESC LIMIT 5000)"
        )


def record_security_incident(chat_id: int, chat_title: str, kind: str,
                             severity: str = "medium", user_id: int | None = None,
                             username: str | None = None, display_name: str = "",
                             details: str = "") -> None:
    """Store concise defensive incident metadata, never message bodies or secrets."""
    allowed_severities = {"low", "medium", "high", "critical"}
    severity = severity if severity in allowed_severities else "medium"
    with _connection() as db:
        db.execute(
            """INSERT INTO security_incidents
               (chat_id, chat_title, kind, severity, user_id, username, display_name, details)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (chat_id, str(chat_title or "Telegram group")[:200], str(kind)[:80],
             severity, user_id, str(username or "")[:64],
             str(display_name or "")[:160], str(details)[:500]),
        )
        db.execute(
            "DELETE FROM security_incidents WHERE id NOT IN "
            "(SELECT id FROM security_incidents ORDER BY id DESC LIMIT 3000)"
        )



def has_recent_security_incident(chat_id: int, kind: str, seconds: int = 600) -> bool:
    """Check whether a matching alert was already recorded within a cooldown."""
    seconds = max(1, min(int(seconds), 86400))
    with _connection() as db:
        row = db.execute(
            """SELECT 1 FROM security_incidents
               WHERE chat_id=? AND kind=?
                 AND created_at >= datetime('now', ?)
               LIMIT 1""",
            (chat_id, kind, f"-{seconds} seconds"),
        ).fetchone()
    return row is not None


def get_known_groups(limit: int = 20) -> list[dict]:
    limit = max(1, min(int(limit), 50))
    with _connection() as db:
        rows = db.execute(
            "SELECT chat_id, title, last_seen FROM known_groups "
            "ORDER BY last_seen DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(chat_id=row[0], title=row[1], last_seen=row[2]) for row in rows]


def get_owner_security_summary() -> dict:
    """Return aggregated security counters for the owner dashboard."""
    with _connection() as db:
        groups = db.execute("SELECT COUNT(*) FROM known_groups").fetchone()[0]
        joins_24h = db.execute(
            "SELECT COUNT(*) FROM member_join_events "
            "WHERE datetime(joined_at) >= datetime('now', '-1 day')"
        ).fetchone()[0]
        incidents_24h = db.execute(
            "SELECT COUNT(*) FROM security_incidents "
            "WHERE datetime(created_at) >= datetime('now', '-1 day')"
        ).fetchone()[0]
        raids_7d = db.execute(
            "SELECT COUNT(*) FROM security_incidents WHERE kind='raid_detected' "
            "AND datetime(created_at) >= datetime('now', '-7 days')"
        ).fetchone()[0]
        spam_24h = db.execute(
            "SELECT COUNT(*) FROM security_incidents WHERE kind='anti_spam' "
            "AND datetime(created_at) >= datetime('now', '-1 day')"
        ).fetchone()[0]
        active_raids = db.execute(
            "SELECT COUNT(*) FROM raid_modes WHERE expires_at > ?", (time.time(),)
        ).fetchone()[0]
    return {
        "groups": int(groups), "joins_24h": int(joins_24h),
        "incidents_24h": int(incidents_24h), "raids_7d": int(raids_7d),
        "spam_24h": int(spam_24h), "active_raids": int(active_raids),
    }


def get_recent_security_incidents(limit: int = 10) -> list[dict]:
    limit = max(1, min(int(limit), 30))
    with _connection() as db:
        rows = db.execute(
            """SELECT created_at, chat_id, chat_title, kind, severity,
                      user_id, username, display_name, details
               FROM security_incidents ORDER BY id DESC LIMIT ?""", (limit,)
        ).fetchall()
    keys = ("created_at", "chat_id", "chat_title", "kind", "severity",
            "user_id", "username", "display_name", "details")
    return [dict(zip(keys, row)) for row in rows]


def get_recent_member_joins(limit: int = 10) -> list[dict]:
    limit = max(1, min(int(limit), 30))
    with _connection() as db:
        rows = db.execute(
            """SELECT joined_at, chat_id, chat_title, user_id, username, display_name
               FROM member_join_events ORDER BY id DESC LIMIT ?""", (limit,)
        ).fetchall()
    keys = ("joined_at", "chat_id", "chat_title", "user_id", "username", "display_name")
    return [dict(zip(keys, row)) for row in rows]


def get_database_status() -> dict:
    """Return a non-sensitive health summary for the active database."""
    with _connection() as db:
        integrity = str(db.execute("PRAGMA quick_check").fetchone()[0])
        table_count = int(db.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchone()[0])
        journal_mode = str(db.execute("PRAGMA journal_mode").fetchone()[0])
    size_bytes = DB_PATH.stat().st_size if DB_PATH.exists() else 0
    return {
        "path": str(DB_PATH),
        "exists": DB_PATH.exists(),
        "size_bytes": size_bytes,
        "integrity": integrity,
        "table_count": table_count,
        "journal_mode": journal_mode,
    }


def verify_database_backup(snapshot: bytes) -> dict:
    """Restore a snapshot into an isolated in-memory database and validate it."""
    if not isinstance(snapshot, bytes) or not snapshot.startswith(b"SQLite format 3"):
        raise sqlite3.DatabaseError("Backup is not a valid SQLite database image")
    restored = sqlite3.connect(":memory:")
    try:
        restored.deserialize(snapshot)
        integrity = str(restored.execute("PRAGMA integrity_check").fetchone()[0])
        if integrity != "ok":
            raise sqlite3.DatabaseError(f"Restored backup integrity check failed: {integrity}")
        tables = {
            str(row[0]) for row in restored.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
        }
        required_tables = {
            "warnings", "pending_verifications", "security_audit",
            "security_incidents", "known_groups", "member_join_events",
            "automatic_backup_state", "daily_report_state",
            "channel_media_settings",
        }
        missing = required_tables - tables
        if missing:
            raise sqlite3.DatabaseError(
                "Restored backup is missing required tables: " + ", ".join(sorted(missing))
            )
        return {"integrity": integrity, "table_count": len(tables)}
    finally:
        restored.close()


def create_database_backup() -> bytes:
    """Create a consistent SQLite snapshot and verify an isolated restore."""
    source = _connect()
    target = sqlite3.connect(":memory:")
    try:
        source.backup(target)
        integrity = str(target.execute("PRAGMA integrity_check").fetchone()[0])
        if integrity != "ok":
            raise sqlite3.DatabaseError(f"Backup integrity check failed: {integrity}")
        snapshot = target.serialize()
        verify_database_backup(snapshot)
        return snapshot
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


def set_channel_media_enabled(channel_id: int, enabled: bool) -> None:
    """Persist the channel media policy; channels are opt-in and default OFF."""
    with _connection() as db:
        db.execute(
            "INSERT INTO channel_media_settings(channel_id, enabled) VALUES (?, ?) "
            "ON CONFLICT(channel_id) DO UPDATE SET enabled=excluded.enabled",
            (channel_id, int(enabled)),
        )


def is_channel_media_enabled(channel_id: int) -> bool:
    """Return whether channel media filtering was explicitly enabled."""
    with _connection() as db:
        row = db.execute(
            "SELECT enabled FROM channel_media_settings WHERE channel_id=?",
            (channel_id,),
        ).fetchone()
    return bool(row[0]) if row else False



def get_last_automatic_backup_at() -> float | None:
    """Return the Unix timestamp of the last successfully delivered automatic backup."""
    with _connection() as db:
        row = db.execute(
            "SELECT last_success_at FROM automatic_backup_state WHERE id=1"
        ).fetchone()
    return float(row[0]) if row else None


def set_last_automatic_backup_at(timestamp: float) -> None:
    """Persist the last successful automatic backup time across service restarts."""
    with _connection() as db:
        db.execute(
            """INSERT INTO automatic_backup_state(id, last_success_at) VALUES (1, ?)
               ON CONFLICT(id) DO UPDATE SET last_success_at=excluded.last_success_at""",
            (float(timestamp),),
        )


def get_last_daily_report_at() -> float | None:
    """Return the timestamp of the last successfully delivered daily report."""
    with _connection() as db:
        row = db.execute(
            "SELECT last_success_at FROM daily_report_state WHERE id=1"
        ).fetchone()
    return float(row[0]) if row else None


def set_last_daily_report_at(timestamp: float) -> None:
    """Persist successful daily report delivery to prevent restart duplicates."""
    with _connection() as db:
        db.execute(
            """INSERT INTO daily_report_state(id, last_success_at) VALUES (1, ?)
               ON CONFLICT(id) DO UPDATE SET last_success_at=excluded.last_success_at""",
            (float(timestamp),),
        )
