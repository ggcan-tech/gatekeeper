#!/usr/bin/env python3
"""Exam #2A corpus pull: RECAP docket documents for the SELECTED new judges.

Reads the frozen selection from data/judges2.json (written after census +
roster merge, per the mechanical rule in PREREGISTRATION-2.md), then pulls
each judge's full 3-year window using exam #1's ingest machinery — one pull,
split into pre-cutoff grounding / post-cutoff exam by split.py later, exactly
as exam #1 did.

Usage:
  python3 pipeline/ingest2.py --smoke      # 1 page/judge, verify shapes
  python3 pipeline/ingest2.py              # full pull (rate-limited, hours)

data/judges2.json format:
  {"selected": [{"judge": "Rakoff", "court": "nysd"}, ...]}
"""
from __future__ import annotations
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ingest


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()

    sel_path = "data/judges2.json"
    if not os.path.exists(sel_path):
        sys.exit(f"{sel_path} missing — freeze the selection first "
                 "(census + roster merge, PREREGISTRATION-2.md rule)")
    selected = json.load(open(sel_path))["selected"]
    print(f"pulling {len(selected)} judges, window start {ingest.WINDOW_START}")

    for i, rec in enumerate(selected):
        judge, court = rec["judge"], rec["court"]
        for desc in ("order", "opinion"):
            out = f"data/raw2_{judge.lower()}_{desc}.jsonl"
            print(f"[{i+1}/{len(selected)}] {court}:{judge} ({desc}) -> {out}")
            n = ingest.pull_judge(judge, court, out, smoke=args.smoke,
                                  description=desc)
            print(f"  {n} docs")


if __name__ == "__main__":
    main()
