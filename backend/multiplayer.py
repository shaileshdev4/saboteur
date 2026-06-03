"""Multiplayer head-to-head matches.

Design:
  - One match has up to 2 players. Players are identified by session_id.
  - When a match starts, both players see the SAME round (same problem,
    same potential sabotage). The first to submit a correct decision wins
    the round.
  - Matches are short -5 rounds. Score is rounds-won.
  - State lives in memory only (no DB). If the backend restarts, matches
    are lost. That's intentional -multiplayer state is ephemeral.

Concurrency:
  - A single threading.Lock guards the registry. Match operations are
    short, so lock contention is fine for the demo scale (dozens of
    concurrent matches, not thousands).
  - HTTP polling: clients GET /match/{id} every 1–2s to see state changes.
    For V3 scope we don't need websockets; the matches are short and
    poll bandwidth is trivial.

Why no DB:
  - The product-defining moments -matchmaking, the race -don't benefit
    from persistence. If you want a leaderboard later, that's a separate
    table (V4).
"""
from __future__ import annotations

import random
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Optional


# ---------- Data ----------

@dataclass
class MatchPlayer:
    session_id: str
    nickname: str
    score: int = 0
    # Per-round timestamp of when this player submitted their answer.
    # None means hasn't answered yet.
    last_submission_time: Optional[float] = None
    last_submission_correct: Optional[bool] = None


@dataclass
class Match:
    match_id: str
    created_at: float
    join_code: str
    players: list[MatchPlayer] = field(default_factory=list)
    # State machine: lobby -> in_progress -> finished
    state: str = "lobby"
    # Round-level state (set when the next round starts):
    current_round_id: Optional[str] = None    # round_id (also stored in `rounds` table)
    current_round_number: int = 0
    total_rounds: int = 5
    round_started_at: Optional[float] = None
    # When players submit, we hold answers here until both submit (or timeout).
    round_submissions: dict[str, dict] = field(default_factory=dict)

    def to_public_dict(self) -> dict:
        return {
            "match_id": self.match_id,
            "join_code": self.join_code,
            "state": self.state,
            "current_round_number": self.current_round_number,
            "total_rounds": self.total_rounds,
            "players": [
                {
                    "session_id": p.session_id,
                    "nickname": p.nickname,
                    "score": p.score,
                    "answered_this_round":
                        self.current_round_id is not None
                        and p.session_id in self.round_submissions,
                }
                for p in self.players
            ],
            "current_round_id": self.current_round_id,
        }


# ---------- Registry ----------

_MATCHES: dict[str, Match] = {}
_CODE_INDEX: dict[str, str] = {}   # join_code -> match_id
_LOCK = threading.Lock()


def _generate_match_code() -> str:
    alpha = "BCDFGHJKLMNPQRSTVWXYZ"   # consonants only for less ambiguity
    nums = "23456789"
    return (random.choice(alpha) + random.choice(alpha) +
            random.choice(nums) + random.choice(nums))


# ---------- Creating + joining ----------

def create_match(creator_session_id: str, nickname: str) -> Match:
    """Open a lobby match. The creator is player 1 and waits for player 2."""
    with _LOCK:
        for _ in range(50):
            code = _generate_match_code()
            if code not in _CODE_INDEX:
                break
        else:
            raise RuntimeError("Couldn't generate a unique match code.")
        match = Match(
            match_id=uuid.uuid4().hex[:12],
            created_at=time.time(),
            join_code=code,
        )
        match.players.append(MatchPlayer(
            session_id=creator_session_id,
            nickname=nickname.strip()[:24] or "Player 1",
        ))
        _MATCHES[match.match_id] = match
        _CODE_INDEX[code] = match.match_id
    return match


def join_match(join_code: str, session_id: str, nickname: str) -> Match:
    """Join an existing lobby match using its short code."""
    with _LOCK:
        match_id = _CODE_INDEX.get(join_code.upper())
        if not match_id:
            raise KeyError(f"No match with code '{join_code}'")
        match = _MATCHES.get(match_id)
        if not match:
            raise KeyError(f"Match {match_id} no longer exists")
        if match.state != "lobby":
            raise ValueError("Match has already started")
        if any(p.session_id == session_id for p in match.players):
            return match   # already joined; idempotent
        if len(match.players) >= 2:
            raise ValueError("Match is full")
        match.players.append(MatchPlayer(
            session_id=session_id,
            nickname=nickname.strip()[:24] or "Player 2",
        ))
    return match


def get_match(match_id: str) -> Match:
    with _LOCK:
        match = _MATCHES.get(match_id)
    if not match:
        raise KeyError(f"Match {match_id} not found")
    return match


def get_match_by_code(join_code: str) -> Match:
    with _LOCK:
        mid = _CODE_INDEX.get(join_code.upper())
    if not mid:
        raise KeyError(f"No match with code '{join_code}'")
    return get_match(mid)


# ---------- Round flow ----------

def start_match(match_id: str, requester_session_id: str) -> Match:
    """Move match from lobby to in_progress. Only a player can start."""
    with _LOCK:
        match = _MATCHES.get(match_id)
        if not match:
            raise KeyError(f"Match {match_id} not found")
        if match.state != "lobby":
            raise ValueError(f"Match state is {match.state}, not lobby")
        if not any(p.session_id == requester_session_id for p in match.players):
            raise PermissionError("Only a player can start the match")
        if len(match.players) < 2:
            raise ValueError("Need 2 players to start")
        match.state = "in_progress"
        match.current_round_number = 0
    return match


def attach_round(match_id: str, round_id: str) -> Match:
    """Both players receive the same round_id. Called by /match/{id}/round
    after generating a fresh round."""
    with _LOCK:
        match = _MATCHES.get(match_id)
        if not match:
            raise KeyError(f"Match {match_id} not found")
        match.current_round_id = round_id
        match.current_round_number += 1
        match.round_started_at = time.time()
        match.round_submissions = {}
    return match


def submit_round_answer(match_id: str, session_id: str,
                        is_correct: bool) -> Match:
    """A player submitted their answer; record it and update scores if both
    players have answered."""
    with _LOCK:
        match = _MATCHES.get(match_id)
        if not match:
            raise KeyError(f"Match {match_id} not found")
        if match.state != "in_progress":
            raise ValueError("Match is not in progress")
        if not match.current_round_id:
            raise ValueError("No active round")
        if session_id in match.round_submissions:
            return match   # already submitted; idempotent
        match.round_submissions[session_id] = {
            "is_correct": is_correct,
            "ts": time.time(),
        }
        # Player record
        for p in match.players:
            if p.session_id == session_id:
                p.last_submission_time = time.time()
                p.last_submission_correct = is_correct

        # If both have submitted, award the round.
        if len(match.round_submissions) >= len(match.players):
            _award_round(match)
            if match.current_round_number >= match.total_rounds:
                match.state = "finished"
            match.current_round_id = None     # next /round call will start a new one
    return match


def _award_round(match: Match) -> None:
    """Award 1 point to the FIRST player who got it correct.

    If both correct: faster wins. If only one correct: that one wins. If
    neither correct: nobody gets a point.
    """
    correct_submissions = [
        (sid, s["ts"]) for sid, s in match.round_submissions.items()
        if s["is_correct"]
    ]
    if not correct_submissions:
        return
    correct_submissions.sort(key=lambda x: x[1])
    winner_sid = correct_submissions[0][0]
    for p in match.players:
        if p.session_id == winner_sid:
            p.score += 1
            break


# ---------- Cleanup ----------

def prune_old_matches(max_age_seconds: int = 3600) -> int:
    """Remove matches older than `max_age_seconds`. Returns count pruned.

    Should be called periodically (e.g., at startup or on a timer). For the
    hackathon scope, we call it lazily before each list/create operation.
    """
    cutoff = time.time() - max_age_seconds
    removed = 0
    with _LOCK:
        stale_ids = [mid for mid, m in _MATCHES.items() if m.created_at < cutoff]
        for mid in stale_ids:
            match = _MATCHES.pop(mid, None)
            if match:
                _CODE_INDEX.pop(match.join_code, None)
                removed += 1
    return removed
