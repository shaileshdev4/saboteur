#!/usr/bin/env python3
"""Run all backend tests. Usage: cd backend && python run_tests.py"""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TESTS = [
    "tests/test_verifier.py",
    "tests/test_generators.py",
    "tests/test_misconceptions.py",
    "tests/test_integration.py",
    "tests/test_api.py",
]


def main() -> int:
    os.chdir(ROOT)
    env = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}
    failed = []
    for rel in TESTS:
        print(f"\n--- {rel} ---")
        r = subprocess.run([sys.executable, rel], env=env)
        if r.returncode:
            failed.append(rel)
    if failed:
        print("FAILED:", ", ".join(failed))
        return 1
    print("\nAll tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
