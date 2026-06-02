"""Pydantic schemas for the HTTP API.

These define the wire format. The engine uses dataclasses (engine/types.py);
this layer translates to/from JSON-friendly shapes and importantly STRIPS the
hidden truth label from what gets sent to the client. The frontend gets only
the displayed solution; the truth is held on the server, keyed by round_id.

V2 additions: domain_id, hints.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


# ---------- Domains (new in V2) ----------

class ProblemKindOut(BaseModel):
    id: str
    label: str
    difficulty_min: int
    difficulty_max: int


class DomainOut(BaseModel):
    id: str
    label: str
    description: str
    problem_kinds: list[ProblemKindOut]


# ---------- Round (sent to client) ----------

class StepOut(BaseModel):
    index: int
    latex: str
    operation: str


class RoundOut(BaseModel):
    round_id: str
    session_id: str
    domain_id: str                  # NEW: which domain this round came from
    problem_type: str               # the kind_id within that domain
    difficulty: int
    problem_latex: str
    steps: list[StepOut]


# ---------- Player action ----------

class GradeRequest(BaseModel):
    session_id: str
    round_id: str
    decision: str = Field(..., pattern="^(trust|flag)$")
    flagged_step_index: Optional[int] = None
    flagged_misconception_id: Optional[str] = None


# ---------- Grade ----------

class AchievementOut(BaseModel):
    id: str
    name: str
    description: str
    icon: str
    tier: str


class GradeOut(BaseModel):
    outcome: str
    points: int                       # net points (after hint cost)
    base_points: int = 0              # before hint cost was deducted
    hint_cost: int = 0
    is_clean: bool
    corrupted_step_index: Optional[int] = None
    misconception_id: Optional[str] = None
    misconception_name: Optional[str] = None
    truth_step_latex: Optional[str] = None
    shown_step_latex: Optional[str] = None
    step_narration: list[str] = Field(default_factory=list)
    misconception_explanation: str = ""
    achievements_unlocked: list[AchievementOut] = Field(default_factory=list)


# ---------- Hint (new) ----------

class HintRequestSchema(BaseModel):
    session_id: str
    round_id: str
    tier: int = Field(..., ge=1, le=3)


class HintOut(BaseModel):
    tier: int
    message: str
    cost: int
    cumulative_cost: int
    is_terminal: bool = False


# ---------- Dashboard ----------

class DashboardOut(BaseModel):
    session_id: str
    score: float
    total_points: int
    rating: float
    suggested_difficulty: int
    counts: dict
    score_history: list[float]
    point_history: list[int]
    per_misconception: dict
    per_domain: dict = Field(default_factory=dict)   # NEW


# ---------- Session ----------

class SessionOut(BaseModel):
    session_id: str
    created_at: str


# ---------- Misconceptions ----------

class MisconceptionOut(BaseModel):
    id: str
    name: str
    category: str
    difficulty: int
    description: str
    domain_id: str = "algebra"        # NEW


# ---------- BYOAI ----------

class ByoaiRequest(BaseModel):
    problem: str
    steps: list[str]


class ByoaiStepResult(BaseModel):
    index: int
    expression_latex: str
    is_valid: bool
    expected_latex: Optional[str] = None
    error_message: Optional[str] = None


class ByoaiResult(BaseModel):
    problem_latex: str
    steps: list[ByoaiStepResult]
    first_error_index: Optional[int] = None
    final_answer_correct: Optional[bool] = None
    summary: str


# ===========================================================================
# V3 schemas
# ===========================================================================

# ---------- Universal Auditor ----------

class UniversalAuditRequest(BaseModel):
    blob: str                                     # raw pasted text
    domain_id: Optional[str] = None               # force a domain (optional)
    problem_override: Optional[str] = None        # force the problem text


class UniversalAuditResult(BaseModel):
    problem_latex: str
    steps: list["ByoaiStepResult"]
    first_error_index: Optional[int] = None
    final_answer_correct: Optional[bool] = None
    summary: str
    detected_domain: str
    domain_scores: dict = Field(default_factory=dict)


# ---------- Classroom ----------

class ClassCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)


class ClassOut(BaseModel):
    class_id: str
    name: str
    join_code: str
    created_at: float
    member_count: int = 0
    # teacher_token is included ONLY in the create response. Subsequent
    # requests authenticate by passing it back as a header.
    teacher_token: Optional[str] = None


class ClassJoinRequest(BaseModel):
    join_code: str
    session_id: str
    nickname: str = Field(..., min_length=1, max_length=32)


class ClassMemberStat(BaseModel):
    nickname: str
    score: float
    rating: float
    total_rounds: int
    over_trust_count: int
    correct_catch_count: int


class ClassAggregateOut(BaseModel):
    class_id: str
    name: str
    join_code: str
    member_count: int
    members: list[ClassMemberStat]
    # Class-wide aggregates
    avg_score: float
    avg_rating: float
    misconception_heatmap: dict     # mid -> {seen, caught, catch_rate}


# ---------- Multiplayer ----------

class MatchCreateRequest(BaseModel):
    session_id: str
    nickname: str = Field(..., min_length=1, max_length=24)


class MatchJoinRequest(BaseModel):
    session_id: str
    nickname: str = Field(..., min_length=1, max_length=24)
    join_code: str


class MatchPlayerOut(BaseModel):
    session_id: str
    nickname: str
    score: int
    answered_this_round: bool


class MatchOut(BaseModel):
    match_id: str
    join_code: str
    state: str                                # lobby | in_progress | finished
    current_round_number: int
    total_rounds: int
    players: list[MatchPlayerOut]
    current_round_id: Optional[str] = None


class MatchStartRequest(BaseModel):
    session_id: str


class MatchSubmitRequest(BaseModel):
    session_id: str
    round_id: str
    decision: str = Field(..., pattern="^(trust|flag)$")
    flagged_step_index: Optional[int] = None


# ---------- Image input ----------

class ImageTranscribeResult(BaseModel):
    ok: bool
    text: str
    provider: str
    error: str = ""


# ---------- V5: Leaderboards ----------

class LeaderboardEntryOut(BaseModel):
    session_id: str
    nickname: str
    score: float
    rating: float
    rounds: int
    over_trust: int
    rank_score: float


class LeaderboardOut(BaseModel):
    period: str
    domain_id: Optional[str] = None
    class_id: Optional[str] = None
    entries: list[LeaderboardEntryOut]
    computed_at: float


class DisplayPrefRequest(BaseModel):
    session_id: str
    nickname: Optional[str] = Field(None, max_length=24)
    opted_in: bool


# Resolve the forward ref now that ByoaiStepResult exists above.
UniversalAuditResult.model_rebuild()
