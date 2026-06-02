"""Leaderboard scoring.

Rank function: weighted blend of calibration score, rounds played (with
diminishing returns), and over-trust penalty.

  rank_score = score - 5 * over_trust_rate * 100 + 10 * log1p(rounds_played)

Periods:
  - "all_time": every opted-in session
  - "weekly":   sessions created in the last 7 days (best-effort)
  - "daily":    sessions created in the last 24 hours (best-effort)

Cached in SQLite with a 60-second TTL (lazy refresh, no background workers).
"""
from __future__ import annotations

import json
import math
import time
from typing import Optional

try:
    from .persistence import DB_PATH, _conn, _lock
except ImportError:
    from persistence import DB_PATH, _conn, _lock


CACHE_TTL_SECONDS = 60


def init_tables(db_path: str = DB_PATH) -> None:
    with _conn(db_path) as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS leaderboard_cache (
                key         TEXT PRIMARY KEY,
                payload     TEXT NOT NULL,
                computed_at REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS session_display (
                session_id   TEXT PRIMARY KEY,
                nickname     TEXT,
                opted_in     INTEGER NOT NULL DEFAULT 0,
                updated_at   REAL NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            );
        """)
        conn.commit()


def set_display(session_id: str, nickname: Optional[str], opted_in: bool,
                db_path: str = DB_PATH) -> None:
    """Player opts in to public leaderboards with a nickname."""
    with _lock, _conn(db_path) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO session_display"
            "(session_id, nickname, opted_in, updated_at) VALUES (?, ?, ?, ?)",
            (session_id, nickname, 1 if opted_in else 0, time.time()),
        )
        conn.commit()
    _invalidate_cache(db_path)


def get_display(session_id: str, db_path: str = DB_PATH) -> Optional[dict]:
    with _conn(db_path) as conn:
        row = conn.execute(
            "SELECT nickname, opted_in FROM session_display WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        if not row:
            return None
        return {"nickname": row["nickname"], "opted_in": bool(row["opted_in"])}


def _rank_score(score: float, rounds: int, over_trust: int) -> float:
    if rounds == 0:
        return score
    over_trust_rate = over_trust / rounds
    return score - 5.0 * over_trust_rate * 100 + 10.0 * math.log1p(rounds)


def compute_leaderboard(period: str = "all_time",
                        domain_id: Optional[str] = None,
                        class_id: Optional[str] = None,
                        limit: int = 50,
                        db_path: str = DB_PATH) -> list[dict]:
    """Recompute the leaderboard from sessions table."""
    if period not in ("all_time", "weekly", "daily"):
        raise ValueError(f"unknown period: {period}")

    cutoff: Optional[float] = None
    if period == "weekly":
        cutoff = time.time() - 7 * 86400
    elif period == "daily":
        cutoff = time.time() - 86400

    with _conn(db_path) as conn:
        sql = """
            SELECT s.session_id, s.state_json, sd.nickname, s.created_at
            FROM sessions s
            JOIN session_display sd ON sd.session_id = s.session_id
            WHERE sd.opted_in = 1
        """
        params: list = []
        if class_id:
            sql += (
                " AND s.session_id IN (SELECT session_id FROM class_members"
                " WHERE class_id = ?)"
            )
            params.append(class_id)
        if cutoff is not None:
            sql += " AND s.created_at >= ?"
            params.append(cutoff)
        rows = conn.execute(sql, params).fetchall()

    entries = []
    for row in rows:
        try:
            state = json.loads(row["state_json"])
        except Exception:
            continue

        if domain_id:
            d = state.get("per_domain", {}).get(domain_id)
            if not d or not d.get("counts", {}).get("total"):
                continue
            counts = d["counts"]
            score = d.get("score", 0.0)
            rating = d.get("rating", 1000.0)
        else:
            counts = state.get("counts", {})
            if not counts.get("total"):
                continue
            score = state.get("score", 0.0)
            rating = state.get("rating", 1000.0)

        rounds = counts.get("total", 0)
        over_trust = counts.get("over_trust", 0)
        rank_score = _rank_score(score, rounds, over_trust)

        entries.append({
            "session_id": row["session_id"],
            "nickname": row["nickname"] or "Anonymous",
            "score": score,
            "rating": rating,
            "rounds": rounds,
            "over_trust": over_trust,
            "rank_score": rank_score,
        })

    entries.sort(key=lambda e: -e["rank_score"])
    return entries[:limit]


def _invalidate_cache(db_path: str = DB_PATH) -> None:
    with _lock, _conn(db_path) as conn:
        conn.execute("DELETE FROM leaderboard_cache")
        conn.commit()


def cached_leaderboard(period: str, domain_id: Optional[str],
                       class_id: Optional[str], limit: int = 50,
                       db_path: str = DB_PATH) -> list[dict]:
    cache_key = f"{period}:{domain_id or 'all'}:{class_id or 'all'}:{limit}"
    with _conn(db_path) as conn:
        row = conn.execute(
            "SELECT payload, computed_at FROM leaderboard_cache WHERE key = ?",
            (cache_key,),
        ).fetchone()
        if row and (time.time() - row["computed_at"]) < CACHE_TTL_SECONDS:
            return json.loads(row["payload"])

    entries = compute_leaderboard(period, domain_id, class_id, limit, db_path)
    with _lock, _conn(db_path) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO leaderboard_cache(key, payload, computed_at)"
            " VALUES (?, ?, ?)",
            (cache_key, json.dumps(entries), time.time()),
        )
        conn.commit()
    return entries
