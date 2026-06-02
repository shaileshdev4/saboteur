"""Cross-platform test output (Windows cp1252 consoles choke on Unicode checkmarks)."""
from __future__ import annotations

import sys


def say(msg: str) -> None:
    try:
        print(msg)
    except UnicodeEncodeError:
        safe = msg.replace("\u2713", "[OK]").replace("\u2717", "[FAIL]")
        print(safe.encode("ascii", "replace").decode("ascii"))


def configure_stdout_utf8() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
