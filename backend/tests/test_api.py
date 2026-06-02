"""API tests - run from backend/: python tests/test_api.py"""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

_tmpdir = tempfile.mkdtemp(prefix="saboteur_test_")
os.environ["SABOTEUR_DB_PATH"] = os.path.join(_tmpdir, "test.db")

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["domains_loaded"] == 4
    assert body["misconceptions_loaded"] == 37


def test_session_and_round_clean():
    sid = client.post("/session").json()["session_id"]
    body = client.get(
        f"/session/{sid}/round",
        params={"corrupt_prob": 0.0},
    ).json()
    assert body["round_id"]
    assert len(body["steps"]) >= 2


def test_session_and_round_corrupt():
    sid = client.post("/session").json()["session_id"]
    for _ in range(15):
        body = client.get(
            f"/session/{sid}/round",
            params={"corrupt_prob": 1.0, "problem_type": "linear_one_var"},
        ).json()
        gr = client.post("/grade", json={
            "session_id": sid,
            "round_id": body["round_id"],
            "decision": "trust",
        }).json()
        if not gr["is_clean"]:
            assert gr["corrupted_step_index"] is not None
            return
    raise AssertionError("expected at least one sabotaged round")


def test_grade_over_trust_path():
    sid = client.post("/session").json()["session_id"]
    for _ in range(10):
        body = client.get(
            f"/session/{sid}/round",
            params={"corrupt_prob": 1.0, "problem_type": "linear_one_var"},
        ).json()
        gr = client.post("/grade", json={
            "session_id": sid,
            "round_id": body["round_id"],
            "decision": "trust",
        }).json()
        if not gr["is_clean"]:
            assert gr["outcome"] == "over_trust"
            assert gr["points"] < 0
            return


def test_dashboard_updates():
    sid = client.post("/session").json()["session_id"]
    for _ in range(3):
        body = client.get(f"/session/{sid}/round").json()
        client.post("/grade", json={
            "session_id": sid,
            "round_id": body["round_id"],
            "decision": "trust",
        })
    d = client.get(f"/session/{sid}/dashboard").json()
    assert d["counts"]["total"] == 3
    assert len(d["score_history"]) == 3


def test_misconceptions_list():
    r = client.get("/misconceptions")
    assert r.status_code == 200
    assert len(r.json()) == 37


def test_byoai_correct_solution():
    r = client.post("/byoai", json={
        "problem": "2*x + 6 = 10",
        "steps": ["2*x = 4", "x = 2"],
    })
    body = r.json()
    assert body["first_error_index"] is None
    assert body["final_answer_correct"] is True


def test_byoai_broken_solution():
    r = client.post("/byoai", json={
        "problem": "2*x + 6 = 10",
        "steps": ["2*x = 16", "x = 8"],
    })
    body = r.json()
    assert body["first_error_index"] is not None


def test_byoai_quadratic_correct():
    r = client.post("/byoai", json={
        "problem": "x**2 - 5*x + 6 = 0",
        "steps": ["(x - 2)*(x - 3) = 0", "x = 2"],
    })
    body = r.json()
    assert body["first_error_index"] is None


if __name__ == "__main__":
    from tests._console import say

    test_health()
    say("[OK] /health")
    test_session_and_round_clean()
    say("[OK] session + round")
    test_session_and_round_corrupt()
    say("[OK] sabotage round")
    test_grade_over_trust_path()
    say("[OK] grade")
    test_dashboard_updates()
    say("[OK] dashboard")
    test_misconceptions_list()
    say("[OK] misconceptions")
    test_byoai_correct_solution()
    say("[OK] byoai correct")
    test_byoai_broken_solution()
    say("[OK] byoai broken")
    test_byoai_quadratic_correct()
    say("[OK] byoai quadratic")
    say("\n[OK] All API tests passed.")
