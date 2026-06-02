"""SQLite persistence.

We store:
  - sessions:  one row per session, holds the calibration state JSON.
  - rounds:    one row per round, holds the SabotageRecord-derived truth label
               + the generated solution (as serialized SymPy strings).

The round table lets us look up a round_id and re-grade against the truth
without ever sending the truth to the client.

Why a JSON blob and not a normalized schema? Because the engine is the source
of truth; making the DB schema mirror engine internals would couple them too
tightly. JSON blobs let us evolve the engine without DB migrations.
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Optional


DB_PATH = os.environ.get("SABOTEUR_DB_PATH", "saboteur.sqlite3")

_lock = threading.Lock()


def init_db(db_path: str = DB_PATH) -> None:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    with _conn(db_path) as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id   TEXT PRIMARY KEY,
                created_at   REAL NOT NULL,
                state_json   TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS rounds (
                round_id     TEXT PRIMARY KEY,
                session_id   TEXT NOT NULL,
                created_at   REAL NOT NULL,
                truth_json   TEXT NOT NULL,
                graded       INTEGER NOT NULL DEFAULT 0,
                domain_id    TEXT NOT NULL DEFAULT 'algebra',
                difficulty   INTEGER NOT NULL DEFAULT 2,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            );
            CREATE INDEX IF NOT EXISTS rounds_session_idx
                ON rounds(session_id);
            CREATE TABLE IF NOT EXISTS hints (
                round_id     TEXT NOT NULL,
                tier         INTEGER NOT NULL,
                cost         INTEGER NOT NULL,
                created_at   REAL NOT NULL,
                PRIMARY KEY (round_id, tier),
                FOREIGN KEY (round_id) REFERENCES rounds(round_id)
            );
        """)
        # Migration: add columns to old `rounds` rows if missing.
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(rounds)")}
        if "domain_id" not in cols:
            conn.execute("ALTER TABLE rounds ADD COLUMN domain_id TEXT NOT NULL DEFAULT 'algebra'")
        if "difficulty" not in cols:
            conn.execute("ALTER TABLE rounds ADD COLUMN difficulty INTEGER NOT NULL DEFAULT 2")
        conn.commit()


@contextmanager
def _conn(db_path: str = DB_PATH):
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


# ---------- Sessions ----------

def new_session(state_json: str, db_path: str = DB_PATH) -> str:
    sid = uuid.uuid4().hex[:16]
    with _lock, _conn(db_path) as conn:
        conn.execute(
            "INSERT INTO sessions(session_id, created_at, state_json) VALUES (?, ?, ?)",
            (sid, time.time(), state_json),
        )
        conn.commit()
    return sid


def load_session(session_id: str, db_path: str = DB_PATH) -> Optional[dict]:
    with _conn(db_path) as conn:
        row = conn.execute(
            "SELECT created_at, state_json FROM sessions WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        if not row:
            return None
        return {
            "session_id": session_id,
            "created_at": row["created_at"],
            "state_json": row["state_json"],
        }


def update_session(session_id: str, state_json: str, db_path: str = DB_PATH) -> None:
    with _lock, _conn(db_path) as conn:
        conn.execute(
            "UPDATE sessions SET state_json = ? WHERE session_id = ?",
            (state_json, session_id),
        )
        conn.commit()


# ---------- Rounds ----------

def new_round(session_id: str, truth_json: str,
              domain_id: str = "algebra",
              difficulty: int = 2,
              db_path: str = DB_PATH) -> str:
    rid = uuid.uuid4().hex[:16]
    with _lock, _conn(db_path) as conn:
        conn.execute(
            "INSERT INTO rounds(round_id, session_id, created_at, truth_json, "
            "domain_id, difficulty) VALUES (?, ?, ?, ?, ?, ?)",
            (rid, session_id, time.time(), truth_json, domain_id, difficulty),
        )
        conn.commit()
    return rid


def load_round(round_id: str, db_path: str = DB_PATH) -> Optional[dict]:
    with _conn(db_path) as conn:
        row = conn.execute(
            "SELECT session_id, created_at, truth_json, graded, "
            "domain_id, difficulty FROM rounds WHERE round_id = ?",
            (round_id,),
        ).fetchone()
        if not row:
            return None
        return {
            "round_id": round_id,
            "session_id": row["session_id"],
            "created_at": row["created_at"],
            "truth_json": row["truth_json"],
            "graded": bool(row["graded"]),
            "domain_id": row["domain_id"] if "domain_id" in row.keys() else "algebra",
            "difficulty": row["difficulty"] if "difficulty" in row.keys() else 2,
        }


def mark_round_graded(round_id: str, db_path: str = DB_PATH) -> None:
    with _lock, _conn(db_path) as conn:
        conn.execute(
            "UPDATE rounds SET graded = 1 WHERE round_id = ?",
            (round_id,),
        )
        conn.commit()


# ---------- Hints ----------

def record_hint(round_id: str, tier: int, cost: int,
                db_path: str = DB_PATH) -> None:
    with _lock, _conn(db_path) as conn:
        conn.execute(
            "INSERT OR IGNORE INTO hints(round_id, tier, cost, created_at) "
            "VALUES (?, ?, ?, ?)",
            (round_id, tier, cost, time.time()),
        )
        conn.commit()


def load_hints(round_id: str, db_path: str = DB_PATH) -> list[dict]:
    with _conn(db_path) as conn:
        rows = conn.execute(
            "SELECT tier, cost, created_at FROM hints "
            "WHERE round_id = ? ORDER BY tier ASC",
            (round_id,),
        ).fetchall()
        return [
            {"tier": r["tier"], "cost": r["cost"], "created_at": r["created_at"]}
            for r in rows
        ]


def hint_total_cost(round_id: str, db_path: str = DB_PATH) -> int:
    return sum(h["cost"] for h in load_hints(round_id, db_path))
