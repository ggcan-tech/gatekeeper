#!/usr/bin/env python3
"""Run both pre-freeze gates in sequence in ONE python process (robust under
nohup): ensemble arm-g val gate, then leakage audit. Writes data/gates.log
markers so a waiter can chain FREEZE-2.

Usage: cd gatekeeper && nohup python3 -u pipeline/run_gates.py >> data/gates_run.log 2>&1 &
"""
from __future__ import annotations
import os
import sys
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def mark(m: str) -> None:
    with open("data/gates.log", "a", encoding="utf-8") as f:
        f.write(f"{time.strftime('%H:%M:%S')} {m}\n")
    print(m, flush=True)


def main() -> None:
    try:
        import ensemble_gate2
        mark("ENSEMBLE_GATE_START")
        ensemble_gate2.main()
        mark("ENSEMBLE_GATE_DONE")

        import leakage_audit2
        mark("LEAKAGE_AUDIT_START")
        leakage_audit2.main()
        mark("LEAKAGE_AUDIT_DONE")

        mark("ALL_GATES_DONE")
    except Exception:
        mark("GATES_ERROR")
        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()
