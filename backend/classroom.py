"""Classroom mode.

A *class* is a group of sessions tied together by a join code. The teacher
creates the class and gets a short alphanumeric code; students enter the code
to opt their session into the class. The teacher dashboard then aggregates
calibration data across the class.

Schema additions:
  classes:
    class_id        TEXT PK
    teacher_token   TEXT       — bearer token for teacher; only the teacher
                                  knows this. Used to view aggregate data.
    join_code       TEXT       — short code (e.g. "TIGER-PI"); shared with
                                  students.
    name            TEXT       — display name
    created_at      REAL

  class_members:
    class_id        TEXT
    session_id      TEXT
    nickname        TEXT       — student-chosen name shown in teacher view
    joined_at       REAL
    PRIMARY KEY (class_id, session_id)

We don't add a user table — sessions remain anonymous. The teacher_token is
the only "auth" primitive, and it's per-class. A student joining a class with
a known code doesn't get the teacher token; they get the public class data
only (just enough to confirm they joined).

Privacy note: by design, the teacher can see per-student calibration data.
Students see only their own. Nicknames are how the teacher tells them apart;
they aren't real identities.
"""
from __future__ import annotations

import random
import secrets
import string
import threading
import time
import uuid
from contextlib import contextmanager
from typing import Optional

try:
    from .persistence import _conn, DB_PATH, _lock
except ImportError:
    from persistence import _conn, DB_PATH, _lock


def _init_classroom_tables(db_path: str = DB_PATH) -> None:
    """Idempotent table creation. Call once at app startup."""
    with _conn(db_path) as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS classes (
                class_id       TEXT PRIMARY KEY,
                teacher_token  TEXT NOT NULL UNIQUE,
                join_code      TEXT NOT NULL UNIQUE,
                name           TEXT NOT NULL,
                created_at     REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS classes_join_code_idx
                ON classes(join_code);
            CREATE TABLE IF NOT EXISTS class_members (
                class_id      TEXT NOT NULL,
                session_id    TEXT NOT NULL,
                nickname      TEXT NOT NULL,
                joined_at     REAL NOT NULL,
                PRIMARY KEY (class_id, session_id),
                FOREIGN KEY (class_id) REFERENCES classes(class_id),
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            );
            CREATE INDEX IF NOT EXISTS class_members_session_idx
                ON class_members(session_id);
        """)
        conn.commit()


# Human-friendly join codes: ADJECTIVE-NOUN pairs.
_ADJECTIVES = [
    "RED", "BLUE", "GREEN", "GOLD", "SILVER", "BRIGHT", "QUIET", "SWIFT",
    "BOLD", "CALM", "WARM", "COOL", "EVEN", "SHARP", "WILD", "TRUE",
]
_NOUNS = [
    "PI", "TAU", "PHI", "EULER", "TANGENT", "PROOF", "LEMMA", "AXIOM",
    "VECTOR", "MATRIX", "PRIME", "ROOT", "POWER", "LIMIT", "FIELD", "GROUP",
]


def _generate_join_code(rng: random.Random) -> str:
    adj = rng.choice(_ADJECTIVES)
    noun = rng.choice(_NOUNS)
    num = rng.randint(10, 99)
    return f"{adj}-{noun}-{num}"


# ---------- Class CRUD ----------

def create_class(name: str, db_path: str = DB_PATH) -> dict:
    """Create a new class. Returns dict with class_id, teacher_token, join_code."""
    _init_classroom_tables(db_path)
    rng = random.Random()
    class_id = uuid.uuid4().hex[:16]
    teacher_token = secrets.token_urlsafe(32)
    # Try a few codes in case of collision.
    for _ in range(20):
        join_code = _generate_join_code(rng)
        with _lock, _conn(db_path) as conn:
            try:
                conn.execute(
                    "INSERT INTO classes(class_id, teacher_token, join_code, "
                    "name, created_at) VALUES (?, ?, ?, ?, ?)",
                    (class_id, teacher_token, join_code, name, time.time()),
                )
                conn.commit()
                return {
                    "class_id": class_id,
                    "teacher_token": teacher_token,
                    "join_code": join_code,
                    "name": name,
                }
            except Exception:
                continue
    raise RuntimeError("Failed to generate unique join code; try again.")


def get_class_by_code(join_code: str, db_path: str = DB_PATH) -> Optional[dict]:
    _init_classroom_tables(db_path)
    with _conn(db_path) as conn:
        row = conn.execute(
            "SELECT class_id, name, created_at FROM classes WHERE join_code = ?",
            (join_code.upper(),),
        ).fetchone()
        if not row:
            return None
        return {
            "class_id": row["class_id"],
            "join_code": join_code.upper(),
            "name": row["name"],
            "created_at": row["created_at"],
        }


def get_class_by_teacher_token(teacher_token: str,
                               db_path: str = DB_PATH) -> Optional[dict]:
    _init_classroom_tables(db_path)
    with _conn(db_path) as conn:
        row = conn.execute(
            "SELECT class_id, name, join_code, created_at FROM classes "
            "WHERE teacher_token = ?",
            (teacher_token,),
        ).fetchone()
        if not row:
            return None
        return {
            "class_id": row["class_id"],
            "name": row["name"],
            "join_code": row["join_code"],
            "created_at": row["created_at"],
        }


# ---------- Membership ----------

def join_class(join_code: str, session_id: str, nickname: str,
               db_path: str = DB_PATH) -> dict:
    """Add a session to a class. Returns the class info (not teacher_token)."""
    cls = get_class_by_code(join_code, db_path)
    if cls is None:
        raise KeyError(f"No class with join code '{join_code}'")
    nickname = nickname.strip()[:32] or "Anonymous"
    with _lock, _conn(db_path) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO class_members(class_id, session_id, "
            "nickname, joined_at) VALUES (?, ?, ?, ?)",
            (cls["class_id"], session_id, nickname, time.time()),
        )
        conn.commit()
    return cls


def leave_class(class_id: str, session_id: str,
                db_path: str = DB_PATH) -> None:
    with _lock, _conn(db_path) as conn:
        conn.execute(
            "DELETE FROM class_members WHERE class_id = ? AND session_id = ?",
            (class_id, session_id),
        )
        conn.commit()


def session_class(session_id: str, db_path: str = DB_PATH) -> Optional[dict]:
    """Which class (if any) is this session in?"""
    _init_classroom_tables(db_path)
    with _conn(db_path) as conn:
        row = conn.execute(
            "SELECT c.class_id, c.name, c.join_code, cm.nickname, cm.joined_at "
            "FROM class_members cm JOIN classes c ON c.class_id = cm.class_id "
            "WHERE cm.session_id = ?",
            (session_id,),
        ).fetchone()
        if not row:
            return None
        return dict(row)


# ---------- Aggregation ----------

def class_members(class_id: str, db_path: str = DB_PATH) -> list[dict]:
    """List members of a class with their session_ids and nicknames."""
    with _conn(db_path) as conn:
        rows = conn.execute(
            "SELECT session_id, nickname, joined_at FROM class_members "
            "WHERE class_id = ? ORDER BY joined_at ASC",
            (class_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def class_member_states(class_id: str, db_path: str = DB_PATH) -> list[dict]:
    """Return every member's session state_json (parsed by caller)."""
    import json
    members = class_members(class_id, db_path)
    out = []
    with _conn(db_path) as conn:
        for m in members:
            row = conn.execute(
                "SELECT state_json FROM sessions WHERE session_id = ?",
                (m["session_id"],),
            ).fetchone()
            if not row:
                continue
            out.append({
                "session_id": m["session_id"],
                "nickname": m["nickname"],
                "joined_at": m["joined_at"],
                "state": json.loads(row["state_json"]),
            })
    return out
