#!/usr/bin/env python3
"""Date-split labeled items into grounding corpus vs exam set.

FROZEN rule: an item is EXAM iff its decision/docket-entry date is strictly
after the pinned model's training cutoff. Everything else is GROUNDING.
Refuses to run until the model cutoff is pinned in config.yaml.

Usage: python3 pipeline/split.py 2026-03-01   # cutoff date (must match config)
"""
from __future__ import annotations
import json
import sys


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1].startswith("PIN"):
        sys.exit("REFUSING TO SPLIT: pin the exam model cutoff first "
                 "(config.yaml exam.model_cutoff), then pass it explicitly.")
    cutoff = sys.argv[1]  # ISO date string; string compare works for ISO
    rows = [json.loads(l) for l in open("data/labeled.jsonl", encoding="utf-8")]
    exam = [r for r in rows if (r.get("date") or "") > cutoff]
    grounding = [r for r in rows if (r.get("date") or "") <= cutoff]
    with open("data/exam.jsonl", "w", encoding="utf-8") as f:
        f.writelines(json.dumps(r) + "\n" for r in exam)
    with open("data/grounding.jsonl", "w", encoding="utf-8") as f:
        f.writelines(json.dumps(r) + "\n" for r in grounding)
    per_judge = {}
    for r in exam:
        per_judge[r["judge"]] = per_judge.get(r["judge"], 0) + 1
    print(json.dumps({"cutoff": cutoff, "exam_n": len(exam),
                      "grounding_n": len(grounding), "exam_per_judge": per_judge,
                      "pooled_target_met": len(exam) >= 200}))


if __name__ == "__main__":
    main()
