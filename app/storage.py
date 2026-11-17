"""SQLite-backed storage for group protection settings and warning records."""
from __future__ import annotations

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


@contextmanager
def _connection():
    db = _connect()
    try:
        yield db
        db.commit()
    finally:
        db.close()


def init_storage() -> None:
    with _connection() as db:
        db.executescript(
            """
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
            """
        )


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
    with _connect() as db:
        row = db.execute(
            "SELECT count FROM warnings WHERE chat_id=? AND user_id=?",
            (chat_id, user_id),
        ).fetchone()
        return int(row[0]) if row else 0


def reset_warnings(chat_id: int, user_id: int) -> None:
    with _connect() as db:
        db.execute("DELETE FROM warnings WHERE chat_id=? AND user_id=?", (chat_id, user_id))


def set_feature_enabled(feature: str, chat_id: int, enabled: bool) -> None:
    table = {"badwords": "badword_settings", "antilink": "antilink_settings"}.get(feature)
    if table is None:
        raise ValueError("Unknown protection feature")
    with _connect() as db:
        db.execute(
            f"""INSERT INTO {table}(chat_id, enabled) VALUES (?, ?)
                ON CONFLICT(chat_id) DO UPDATE SET enabled=excluded.enabled""",
            (chat_id, int(enabled)),
        )


def is_feature_enabled(feature: str, chat_id: int) -> bool:
    table = {"badwords": "badword_settings", "antilink": "antilink_settings"}.get(feature)
    if table is None:
        raise ValueError("Unknown protection feature")
    with _connect() as db:
        row = db.execute(f"SELECT enabled FROM {table} WHERE chat_id=?", (chat_id,)).fetchone()
        return bool(row[0]) if row else True


def add_badword(chat_id: int, word: str) -> None:
    with _connect() as db:
        db.execute("INSERT OR IGNORE INTO badwords(chat_id, word) VALUES (?, ?)", (chat_id, word))


def remove_badword(chat_id: int, word: str) -> None:
    with _connect() as db:
        db.execute("DELETE FROM badwords WHERE chat_id=? AND word=?", (chat_id, word))


def get_badwords(chat_id: int) -> set[str]:
    with _connect() as db:
        rows = db.execute("SELECT word FROM badwords WHERE chat_id=? ORDER BY word", (chat_id,)).fetchall()
        return {str(row[0]) for row in rows}


def add_allowed_domain(chat_id: int, domain: str) -> None:
    with _connect() as db:
        db.execute("INSERT OR IGNORE INTO allowed_domains(chat_id, domain) VALUES (?, ?)", (chat_id, domain))


def remove_allowed_domain(chat_id: int, domain: str) -> None:
    with _connect() as db:
        db.execute("DELETE FROM allowed_domains WHERE chat_id=? AND domain=?", (chat_id, domain))


def get_allowed_domains(chat_id: int) -> set[str]:
    with _connect() as db:
        rows = db.execute("SELECT domain FROM allowed_domains WHERE chat_id=? ORDER BY domain", (chat_id,)).fetchall()
        return {str(row[0]) for row in rows}
