"""FastAPI app v2 -multi-domain.

New in v2:
  GET  /domains                         -> list registered domains
  GET  /domains/{did}/misconceptions    -> misconceptions specific to a domain
  POST /hint                            -> request a tier-N hint for a round

Existing endpoints adjusted:
  GET  /session/{sid}/round             -> now accepts ?domain_id=...
  POST /grade                           -> deducts hint cost from points
  GET  /session/{sid}/dashboard         -> now includes per_domain
"""
from __future__ import annotations

import json
import os
import random
import sys
import time
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import sympy as sp
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

# Import domains FIRST so they self-register before anything else uses them.
from engine import domains  # noqa: F401
from engine.calibration import CalibrationState, OutcomeCounts
from engine.domain import all_domains, get_domain, find_misconception_across_domains
from engine.grader import grade as grade_engine
from engine.hints import HINT_COSTS, build_hint
from engine.misconceptions import all_misconceptions
from engine.sabotage_v2 import sabotage_domain, SabotageOptions
from engine.types import (
    GradeOutcome, PlayerAction, PlayerDecision,
)

try:
    from . import achievements as achievements_module
    from . import byoai as byoai_module
    from . import leaderboard as lb_module
    from . import llm as llm_module
    from . import persistence
    from .schemas import (
        ByoaiRequest,
        ByoaiResult,
        ByoaiStepResult,
        ClassAggregateOut,
        ClassCreateRequest,
        ClassJoinRequest,
        ClassMemberStat,
        ClassOut,
        AchievementOut,
        DashboardOut,
        DisplayPrefRequest,
        DomainOut,
        GradeOut,
        LeaderboardEntryOut,
        LeaderboardOut,
        GradeRequest,
        HintOut,
        HintRequestSchema,
        ImageTranscribeResult,
        MatchCreateRequest,
        MatchJoinRequest,
        MatchOut,
        MatchPlayerOut,
        MatchStartRequest,
        MatchSubmitRequest,
        MisconceptionOut,
        ProblemKindOut,
        RoundOut,
        SessionOut,
        StepOut,
        UniversalAuditRequest,
        UniversalAuditResult,
    )
except ImportError:
    import achievements as achievements_module
    import byoai as byoai_module
    import leaderboard as lb_module
    import llm as llm_module
    import persistence
    from schemas import (
        ByoaiRequest,
        ByoaiResult,
        ByoaiStepResult,
        ClassAggregateOut,
        ClassCreateRequest,
        ClassJoinRequest,
        ClassMemberStat,
        ClassOut,
        AchievementOut,
        DashboardOut,
        DisplayPrefRequest,
        DomainOut,
        GradeOut,
        LeaderboardEntryOut,
        LeaderboardOut,
        GradeRequest,
        HintOut,
        HintRequestSchema,
        ImageTranscribeResult,
        MatchCreateRequest,
        MatchJoinRequest,
        MatchOut,
        MatchPlayerOut,
        MatchStartRequest,
        MatchSubmitRequest,
        MisconceptionOut,
        ProblemKindOut,
        RoundOut,
        SessionOut,
        StepOut,
        UniversalAuditRequest,
        UniversalAuditResult,
    )


app = FastAPI(title="The Saboteur API", version="2.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting (no-op if slowapi isn't installed).
try:
    from . import rate_limit as _rate_limit
except ImportError:
    import rate_limit as _rate_limit
_rate_limit.install(app)
limiter = _rate_limit.limiter

persistence.init_db()
lb_module.init_tables()


@app.on_event("startup")
def _startup():
    persistence.init_db()
    lb_module.init_tables()


def _serialize_truth(record, domain_id: str) -> str:
    def step_summary(step):
        return {
            "index": step.index,
            "latex": step.latex(),
            "operation": step.operation.value,
            "note": step.note,
        }
    return json.dumps({
        "domain_id": domain_id,
        "is_clean": record.is_clean,
        "corrupted_step_index": record.corrupted_step_index,
        "misconception_id": record.misconception_id,
        "displayed_steps": [step_summary(s) for s in record.displayed.steps],
        "truth_steps": [step_summary(s) for s in record.truth.steps],
        "problem_type": record.truth.problem_type.value if hasattr(record.truth.problem_type, "value") else str(record.truth.problem_type),
    })


def _deserialize_truth(s: str) -> dict:
    return json.loads(s)


@app.get("/health")
def health():
    total_misconceptions = sum(len(d.misconceptions()) for d in all_domains())
    return {
        "ok": True,
        "ts": time.time(),
        "version": "2.0.0",
        "domains_loaded": len(all_domains()),
        "misconceptions_loaded": total_misconceptions,
    }


@app.get("/domains", response_model=list[DomainOut])
def list_domains():
    out = []
    for d in all_domains():
        kinds = [
            ProblemKindOut(id=k.id, label=k.label,
                           difficulty_min=k.difficulty_range[0],
                           difficulty_max=k.difficulty_range[1])
            for k in d.problem_kinds()
        ]
        out.append(DomainOut(id=d.id, label=d.label, description=d.description,
                             problem_kinds=kinds))
    return out


@app.get("/domains/{did}/misconceptions", response_model=list[MisconceptionOut])
def list_domain_misconceptions(did: str):
    try:
        d = get_domain(did)
    except KeyError as e:
        raise HTTPException(404, str(e))
    return [
        MisconceptionOut(
            id=m.id, name=m.name, category=m.category,
            difficulty=m.difficulty, description=m.description,
            domain_id=did,
        )
        for m in d.misconceptions()
    ]


@app.post("/session", response_model=SessionOut)
def create_session():
    state = CalibrationState()
    sid = persistence.new_session(json.dumps(state.to_dict()))
    return SessionOut(session_id=sid, created_at=str(time.time()))


@app.get("/session/{sid}/dashboard", response_model=DashboardOut)
def get_dashboard(sid: str):
    sess = persistence.load_session(sid)
    if not sess:
        raise HTTPException(404, "session not found")
    state_dict = json.loads(sess["state_json"])

    enriched: dict = {}
    for mid, entry in state_dict.get("per_misconception", {}).items():
        try:
            mis = find_misconception_across_domains(mid)
            enriched[mid] = {
                **entry, "name": mis.name, "category": mis.category,
                "difficulty": mis.difficulty,
            }
        except KeyError:
            enriched[mid] = entry

    return DashboardOut(
        session_id=sid,
        score=state_dict["score"],
        total_points=state_dict["total_points"],
        rating=state_dict["rating"],
        suggested_difficulty=state_dict["suggested_difficulty"],
        counts=state_dict["counts"],
        score_history=state_dict["score_history"],
        point_history=state_dict["point_history"],
        per_misconception=enriched,
        per_domain=state_dict.get("per_domain", {}),
    )


@app.get("/session/{sid}/round", response_model=RoundOut)
def new_round(sid: str,
              domain_id: str = "algebra",
              difficulty: int | None = None,
              corrupt_prob: float = 0.5,
              problem_type: str | None = None,
              propagate: bool = False):
    sess = persistence.load_session(sid)
    if not sess:
        raise HTTPException(404, "session not found")
    state_dict = json.loads(sess["state_json"])

    try:
        domain = get_domain(domain_id)
    except KeyError as e:
        raise HTTPException(400, str(e))

    if difficulty is None:
        dstate = state_dict.get("per_domain", {}).get(domain_id, {})
        difficulty = dstate.get("suggested_difficulty",
                                state_dict.get("suggested_difficulty", 2))
    difficulty = max(1, min(5, int(difficulty)))

    if problem_type is None:
        problem_type = random.choice(domain.problem_kinds()).id

    try:
        sol = domain.generate(problem_type, difficulty=difficulty)
    except KeyError as e:
        raise HTTPException(400, f"Unknown problem_type for domain {domain_id}: {e}")

    record = sabotage_domain(
        domain, sol,
        options=SabotageOptions(
            corrupt_probability=corrupt_prob,
            difficulty_range=(1, min(5, difficulty + 1)),
            propagate=propagate,
        ),
    )

    rid = persistence.new_round(sid, _serialize_truth(record, domain_id),
                                 domain_id=domain_id, difficulty=difficulty)

    return RoundOut(
        round_id=rid,
        session_id=sid,
        domain_id=domain_id,
        problem_type=problem_type,
        difficulty=difficulty,
        problem_latex=record.displayed.steps[0].latex(),
        steps=[
            StepOut(index=s.index, latex=s.latex(), operation=s.operation.value)
            for s in record.displayed.steps
        ],
    )


# Mini record reused by /hint and /grade.
class _MiniSolution:
    def __init__(self):
        self.steps = []

class _MiniStep:
    def __init__(self, latex_str, idx):
        self._latex = latex_str
        self.index = idx
    def latex(self):
        return self._latex

class _MiniRecord:
    def __init__(self, t):
        self.is_clean = t["is_clean"]
        self.corrupted_step_index = t["corrupted_step_index"]
        self.misconception_id = t["misconception_id"]
        self.truth = _MiniSolution()
        self.displayed = _MiniSolution()
        self.truth.steps = [
            _MiniStep(s["latex"], s["index"]) for s in t["truth_steps"]
        ]
        self.displayed.steps = [
            _MiniStep(s["latex"], s["index"]) for s in t["displayed_steps"]
        ]


@app.post("/hint", response_model=HintOut)
def request_hint(req: HintRequestSchema):
    sess = persistence.load_session(req.session_id)
    if not sess:
        raise HTTPException(404, "session not found")
    round_row = persistence.load_round(req.round_id)
    if not round_row:
        raise HTTPException(404, "round not found")
    if round_row["session_id"] != req.session_id:
        raise HTTPException(400, "round/session mismatch")
    if round_row["graded"]:
        raise HTTPException(400, "round already graded; hints unavailable")

    prior = persistence.load_hints(req.round_id)
    prior_tiers = [h["tier"] for h in prior]
    if req.tier in prior_tiers:
        raise HTTPException(400, f"hint tier {req.tier} already used")
    if prior_tiers and max(prior_tiers) >= req.tier:
        raise HTTPException(400, "hints must be requested in ascending tier")

    truth = _deserialize_truth(round_row["truth_json"])
    record = _MiniRecord(truth)

    try:
        prior_tier = max(prior_tiers) if prior_tiers else 0
        hint = build_hint(req.tier, record, prior_tier=prior_tier)
    except ValueError as e:
        raise HTTPException(400, str(e))

    persistence.record_hint(req.round_id, req.tier, hint.cost)
    return HintOut(
        tier=hint.tier,
        message=hint.message,
        cost=hint.cost,
        cumulative_cost=hint.cumulative_cost,
        is_terminal=hint.is_terminal,
    )


@app.post("/grade", response_model=GradeOut)
def submit_grade(req: GradeRequest):
    sess = persistence.load_session(req.session_id)
    if not sess:
        raise HTTPException(404, "session not found")
    round_row = persistence.load_round(req.round_id)
    if not round_row:
        raise HTTPException(404, "round not found")
    if round_row["session_id"] != req.session_id:
        raise HTTPException(400, "round/session mismatch")
    if round_row["graded"]:
        raise HTTPException(400, "round already graded")

    truth = _deserialize_truth(round_row["truth_json"])
    domain_id = truth.get("domain_id", round_row.get("domain_id", "algebra"))
    difficulty = round_row.get("difficulty", 2)
    record = _MiniRecord(truth)

    decision = PlayerDecision(req.decision)
    action = PlayerAction(
        decision=decision,
        flagged_step_index=req.flagged_step_index,
        flagged_misconception_id=req.flagged_misconception_id,
    )

    hint_cost = persistence.hint_total_cost(req.round_id)
    g = grade_engine(action, record, hint_cost=hint_cost)
    base_points = g.points + hint_cost

    state_dict = json.loads(sess["state_json"])
    pre_unlocked = {
        a["id"] for a in achievements_module.evaluate(state_dict)
    }
    state = _state_from_dict(state_dict)
    won = g.outcome in (GradeOutcome.CORRECT_TRUST, GradeOutcome.CORRECT_CATCH)
    state.update_rating(difficulty, won, domain_id=domain_id)
    state.record(g, record, domain_id=domain_id)
    post_state = state.to_dict()
    new_achievements = [
        a for a in achievements_module.evaluate(post_state)
        if a["id"] not in pre_unlocked
    ]
    persistence.update_session(req.session_id, json.dumps(post_state))
    persistence.mark_round_graded(req.round_id)

    seed = g.explanation_seed
    explanation = ""
    if not record.is_clean and seed.get("misconception_name"):
        explanation = llm_module.explain_misconception(
            seed["misconception_name"],
            seed["misconception_description"],
            seed["truth_step_latex"],
            seed["shown_step_latex"],
        )

    narration = []
    for st in truth["displayed_steps"]:
        narration.append(llm_module.phrase_step(
            st["latex"], st["operation"], st["note"]))

    return GradeOut(
        outcome=g.outcome.value,
        points=g.points,
        base_points=base_points,
        hint_cost=hint_cost,
        is_clean=record.is_clean,
        corrupted_step_index=record.corrupted_step_index,
        misconception_id=record.misconception_id,
        misconception_name=seed.get("misconception_name"),
        truth_step_latex=seed.get("truth_step_latex"),
        shown_step_latex=seed.get("shown_step_latex"),
        step_narration=narration,
        misconception_explanation=explanation,
        achievements_unlocked=[
            AchievementOut(**a) for a in new_achievements
        ],
    )


def _state_from_dict(d: dict) -> CalibrationState:
    s = CalibrationState()
    c = d.get("counts", {})
    s.counts = OutcomeCounts(
        correct_trust=c.get("correct_trust", 0),
        correct_catch=c.get("correct_catch", 0),
        over_trust=c.get("over_trust", 0),
        over_suspicion=c.get("over_suspicion", 0),
        wrong_step_catch=c.get("wrong_step_catch", 0),
    )
    s.score_history = list(d.get("score_history", []))
    s.point_history = list(d.get("point_history", []))
    s.per_misconception = dict(d.get("per_misconception", {}))
    s.rating = float(d.get("rating", 1000.0))
    per_domain = d.get("per_domain", {})
    s.per_domain = {}
    for did, info in per_domain.items():
        s.per_domain[did] = {
            "counts": info.get("counts", {}),
            "rating": info.get("rating", 1000.0),
            "score_history": list(info.get("score_history", [])),
            "point_history": list(info.get("point_history", [])),
        }
    return s


@app.get("/misconceptions", response_model=list[MisconceptionOut])
def list_misconceptions():
    out = []
    for d in all_domains():
        for m in d.misconceptions():
            out.append(MisconceptionOut(
                id=m.id, name=m.name, category=m.category,
                difficulty=m.difficulty, description=m.description,
                domain_id=d.id,
            ))
    return out


@app.post("/byoai", response_model=ByoaiResult)
def audit_byoai(req: ByoaiRequest):
    if not req.problem.strip():
        raise HTTPException(400, "problem is required")
    if not req.steps:
        raise HTTPException(400, "at least one step is required")
    result = byoai_module.audit_solution(req.problem, req.steps)
    return ByoaiResult(
        problem_latex=result["problem_latex"],
        steps=[ByoaiStepResult(**s) for s in result["steps"]],
        first_error_index=result["first_error_index"],
        final_answer_correct=result["final_answer_correct"],
        summary=result["summary"],
    )


# ===========================================================================
# V3 ENDPOINTS
# ===========================================================================

from fastapi import Header, UploadFile, File

try:
    from . import auditor as auditor_module
    from . import classroom as classroom_module
    from . import multiplayer as mp_module
    from . import image_input as image_input_module
except ImportError:
    import auditor as auditor_module
    import classroom as classroom_module
    import multiplayer as mp_module
    import image_input as image_input_module

classroom_module._init_classroom_tables()


# ---------- V5: Leaderboards & achievements ----------

@app.get("/leaderboard", response_model=LeaderboardOut)
@limiter.limit("120/hour")
def get_leaderboard(
    request: Request,
    period: str = "all_time",
    domain_id: Optional[str] = None,
    class_id: Optional[str] = None,
    limit: int = 50,
):
    if period not in ("all_time", "weekly", "daily"):
        raise HTTPException(400, "period must be all_time|weekly|daily")
    limit = max(1, min(100, limit))
    entries = lb_module.cached_leaderboard(period, domain_id, class_id, limit)
    return LeaderboardOut(
        period=period,
        domain_id=domain_id,
        class_id=class_id,
        entries=[LeaderboardEntryOut(**e) for e in entries],
        computed_at=time.time(),
    )


@app.post("/session/display")
def set_display_prefs(req: DisplayPrefRequest):
    if persistence.load_session(req.session_id) is None:
        raise HTTPException(404, "session not found")
    if req.opted_in and not (req.nickname and req.nickname.strip()):
        raise HTTPException(400, "nickname required to opt in")
    lb_module.set_display(
        req.session_id,
        req.nickname.strip() if req.nickname else None,
        req.opted_in,
    )
    return {"ok": True}


@app.get("/session/{sid}/display")
def get_display_prefs(sid: str):
    return lb_module.get_display(sid) or {"nickname": None, "opted_in": False}


@app.get("/session/{sid}/achievements", response_model=list[AchievementOut])
def session_achievements(sid: str):
    sess = persistence.load_session(sid)
    if not sess:
        raise HTTPException(404, "session not found")
    state_dict = json.loads(sess["state_json"])
    return [AchievementOut(**a) for a in achievements_module.evaluate(state_dict)]


# ---------- Universal Auditor ----------

@app.post("/audit", response_model=UniversalAuditResult)
@limiter.limit("60/hour")
def audit_universal(request: Request, req: UniversalAuditRequest):
    """Audit a free-form blob of chatbot output across any domain.

    Accepts messy LaTeX/markdown; auto-detects domain.
    """
    if not req.blob.strip():
        raise HTTPException(400, "blob is required")
    try:
        result = auditor_module.audit_universal(
            req.blob,
            domain_id=req.domain_id,
            problem_override=req.problem_override,
        )
    except Exception as exc:
        raise HTTPException(
            500,
            f"Audit failed: {type(exc).__name__}. Try simpler equations, one per line.",
        ) from exc
    return UniversalAuditResult(
        problem_latex=result["problem_latex"],
        steps=[ByoaiStepResult(**s) for s in result["steps"]],
        first_error_index=result["first_error_index"],
        final_answer_correct=result.get("final_answer_correct"),
        summary=result["summary"],
        detected_domain=result.get("detected_domain", "algebra"),
        domain_scores=result.get("domain_scores", {}),
    )


# ---------- Classroom ----------

@app.post("/class", response_model=ClassOut)
@limiter.limit("30/hour")
def create_class(request: Request, req: ClassCreateRequest):
    cls = classroom_module.create_class(req.name)
    return ClassOut(
        class_id=cls["class_id"],
        name=cls["name"],
        join_code=cls["join_code"],
        teacher_token=cls["teacher_token"],
        member_count=0,
        created_at=time.time(),
    )


@app.post("/class/join", response_model=ClassOut)
def join_class(req: ClassJoinRequest):
    # Confirm session exists.
    if persistence.load_session(req.session_id) is None:
        raise HTTPException(404, "session not found")
    try:
        cls = classroom_module.join_class(
            req.join_code, req.session_id, req.nickname)
    except KeyError as e:
        raise HTTPException(404, str(e))
    members = classroom_module.class_members(cls["class_id"])
    return ClassOut(
        class_id=cls["class_id"],
        name=cls["name"],
        join_code=cls["join_code"],
        member_count=len(members),
        created_at=cls.get("created_at", time.time()),
    )


@app.get("/class/by-session/{session_id}", response_model=Optional[ClassOut])
def get_session_class(session_id: str):
    """Which class is this session in? Returns null if not in any class."""
    info = classroom_module.session_class(session_id)
    if info is None:
        return None
    members = classroom_module.class_members(info["class_id"])
    return ClassOut(
        class_id=info["class_id"],
        name=info["name"],
        join_code=info["join_code"],
        member_count=len(members),
        created_at=info["joined_at"],
    )


@app.get("/class/dashboard", response_model=ClassAggregateOut)
def class_dashboard(x_teacher_token: str = Header(...)):
    """Teacher dashboard. Authenticates via X-Teacher-Token header.

    Privacy model (V4 hardening):
      - Per-student rows expose ONLY: nickname, score, rating, round count,
        and the outcome aggregate (catch count, over-trust count).
      - Per-student misconception breakdowns are NOT exposed; only the
        class-wide aggregate heatmap shows misconception detail, and that's
        unattributed.
    """
    cls = classroom_module.get_class_by_teacher_token(x_teacher_token)
    if cls is None:
        raise HTTPException(401, "Invalid teacher token")
    member_states = classroom_module.class_member_states(cls["class_id"])

    members_out: list[ClassMemberStat] = []
    score_sum = 0.0
    rating_sum = 0.0
    misconception_agg: dict = {}

    for m in member_states:
        state = m["state"]
        counts = state.get("counts", {})
        score = state.get("score", 0.0)
        rating = state.get("rating", 1000.0)
        score_sum += score
        rating_sum += rating
        members_out.append(ClassMemberStat(
            nickname=m["nickname"],
            score=score,
            rating=rating,
            total_rounds=counts.get("total", 0),
            over_trust_count=counts.get("over_trust", 0),
            correct_catch_count=counts.get("correct_catch", 0),
        ))
        # Aggregate misconception heatmap -unattributed.
        for mid, entry in state.get("per_misconception", {}).items():
            agg = misconception_agg.setdefault(
                mid, {"seen": 0, "caught": 0,
                      "name": entry.get("name", mid),
                      "category": entry.get("category", "")})
            agg["seen"] += entry.get("seen", 0)
            agg["caught"] += entry.get("caught", 0)

    # Compute catch_rate per misconception.
    for mid, agg in misconception_agg.items():
        agg["catch_rate"] = (agg["caught"] / agg["seen"]) if agg["seen"] else 0.0

    n = len(members_out) or 1
    return ClassAggregateOut(
        class_id=cls["class_id"],
        name=cls["name"],
        join_code=cls["join_code"],
        member_count=len(members_out),
        members=sorted(members_out, key=lambda m: -m.score),
        avg_score=score_sum / n if members_out else 0.0,
        avg_rating=rating_sum / n if members_out else 1000.0,
        misconception_heatmap=misconception_agg,
    )


# ---------- Multiplayer ----------

@app.post("/match", response_model=MatchOut)
@limiter.limit("30/hour")
def create_match(request: Request, req: MatchCreateRequest):
    if persistence.load_session(req.session_id) is None:
        raise HTTPException(404, "session not found")
    mp_module.prune_old_matches()
    match = mp_module.create_match(req.session_id, req.nickname)
    return MatchOut(**match.to_public_dict())


@app.post("/match/join", response_model=MatchOut)
def join_match(req: MatchJoinRequest):
    if persistence.load_session(req.session_id) is None:
        raise HTTPException(404, "session not found")
    try:
        match = mp_module.join_match(req.join_code, req.session_id, req.nickname)
    except KeyError as e:
        raise HTTPException(404, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))
    return MatchOut(**match.to_public_dict())


@app.get("/match/{match_id}", response_model=MatchOut)
def get_match(match_id: str):
    try:
        match = mp_module.get_match(match_id)
    except KeyError as e:
        raise HTTPException(404, str(e))
    return MatchOut(**match.to_public_dict())


@app.post("/match/{match_id}/start", response_model=MatchOut)
def start_match(match_id: str, req: MatchStartRequest):
    try:
        match = mp_module.start_match(match_id, req.session_id)
    except KeyError as e:
        raise HTTPException(404, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))
    except PermissionError as e:
        raise HTTPException(403, str(e))
    return MatchOut(**match.to_public_dict())


@app.post("/match/{match_id}/next-round", response_model=MatchOut)
def match_next_round(match_id: str, req: MatchStartRequest):
    """Both players call this to generate the next round.

    The FIRST call generates a new round and stores its id on the match.
    Subsequent calls (from the other player) return the same round_id.

    The same `req` shape as start; we just need session_id to confirm membership.
    """
    try:
        match = mp_module.get_match(match_id)
    except KeyError as e:
        raise HTTPException(404, str(e))
    if not any(p.session_id == req.session_id for p in match.players):
        raise HTTPException(403, "Not a player in this match")
    if match.state != "in_progress":
        raise HTTPException(400, f"Match state is {match.state}")
    if match.current_round_id:
        # Already a round; return as-is.
        return MatchOut(**match.to_public_dict())

    # Generate a fresh round (algebra, medium difficulty for now).
    from engine.domain import get_domain
    domain = get_domain("algebra")
    sol = domain.generate(random.choice(domain.problem_kinds()).id, difficulty=2)
    record = sabotage_domain(
        domain, sol,
        options=SabotageOptions(corrupt_probability=0.6, difficulty_range=(1, 3)),
    )

    # We store the round under BOTH players' sessions so /grade works for either.
    # Simplest approach: store under player 1's session (a single row), and
    # allow player 2 to grade against it.
    # For simplicity and correctness, we attach the round to the match creator's
    # session -both players will hit /match/submit (not /grade) so the session
    # constraint is enforced at the multiplayer layer, not the grade layer.
    rid = persistence.new_round(
        match.players[0].session_id,
        _serialize_truth(record, "algebra"),
        domain_id="algebra",
        difficulty=2,
    )
    match = mp_module.attach_round(match_id, rid)
    return MatchOut(**match.to_public_dict())


@app.post("/match/{match_id}/submit", response_model=MatchOut)
def match_submit(match_id: str, req: MatchSubmitRequest):
    try:
        match = mp_module.get_match(match_id)
    except KeyError as e:
        raise HTTPException(404, str(e))
    if not any(p.session_id == req.session_id for p in match.players):
        raise HTTPException(403, "Not a player in this match")
    if match.current_round_id != req.round_id:
        raise HTTPException(400, "Round id doesn't match current round")

    # Load truth and grade the action.
    round_row = persistence.load_round(req.round_id)
    if not round_row:
        raise HTTPException(404, "Round not found")
    truth = _deserialize_truth(round_row["truth_json"])
    mini = _MiniRecord(truth)
    action = PlayerAction(
        decision=PlayerDecision(req.decision),
        flagged_step_index=req.flagged_step_index,
    )
    g = grade_engine(action, mini)
    is_correct = g.outcome in (GradeOutcome.CORRECT_TRUST,
                               GradeOutcome.CORRECT_CATCH)

    try:
        match = mp_module.submit_round_answer(match_id, req.session_id, is_correct)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return MatchOut(**match.to_public_dict())


# ---------- Image input ----------

@app.get("/image/configured")
def image_configured():
    return {"configured": image_input_module.is_configured()}


@app.post("/image/transcribe", response_model=ImageTranscribeResult)
@limiter.limit("30/hour")
async def image_transcribe(request: Request,
                            file: UploadFile = File(...),
                            hint: Optional[str] = None):
    """Transcribe an uploaded image of math work to text.

    Accepts: JPG, PNG, WebP. Max 5 MB. Returns plain-text math, one step
    per line. Use the returned text as input to /audit.
    """
    if not image_input_module.is_configured():
        raise HTTPException(503, "Image transcription not configured on server.")
    content_type = file.content_type or "image/jpeg"
    if not content_type.startswith("image/"):
        raise HTTPException(400, "Upload must be an image")
    data = await file.read()
    if len(data) > 5 * 1024 * 1024:
        raise HTTPException(413, "Image larger than 5 MB")
    result = image_input_module.transcribe_image(data, content_type, hint=hint)
    if not result["ok"]:
        # Return 200 with ok=false so the frontend can show the error
        # message gracefully (not a 500).
        return ImageTranscribeResult(**result)
    return ImageTranscribeResult(**result)


# ---------- /round/{round_id}/public (V4 hardening) ----------
# Returns the displayed steps of a round to authorized callers WITHOUT leaking
# the truth label. Authorization: the requester's session_id must be either
# (a) the session that owns the round, or (b) a player in an active match
# whose current_round_id matches.

@app.get("/round/{round_id}/public", response_model=RoundOut)
def round_public(round_id: str, session_id: str):
    round_row = persistence.load_round(round_id)
    if not round_row:
        raise HTTPException(404, "round not found")

    # Owner can always read their own round.
    is_owner = round_row["session_id"] == session_id

    # OR: requester is a player on an active match using this round.
    is_match_player = False
    if not is_owner:
        for m in mp_module._MATCHES.values():
            if m.current_round_id == round_id and any(
                    p.session_id == session_id for p in m.players):
                is_match_player = True
                break

    if not (is_owner or is_match_player):
        raise HTTPException(403, "not authorized to view this round")

    truth = _deserialize_truth(round_row["truth_json"])
    steps = [
        StepOut(index=s["index"], latex=s["latex"], operation=s["operation"])
        for s in truth["displayed_steps"]
    ]
    return RoundOut(
        round_id=round_id,
        session_id=round_row["session_id"],
        domain_id=truth.get("domain_id", round_row.get("domain_id", "algebra")),
        problem_type=truth.get("problem_type", "unknown"),
        difficulty=round_row.get("difficulty", 2),
        problem_latex=truth["displayed_steps"][0]["latex"] if truth["displayed_steps"] else "",
        steps=steps,
    )
