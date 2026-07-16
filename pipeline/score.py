#!/usr/bin/env python3
"""Score the four arms against the frozen win rule. Runs ONCE on verdict day.

Win rule (PREREGISTRATION.md): replica (d) exceeds majority (a) as floor, and
beats metadata (b) AND name-only (c) each by >=10 accuracy points with
one-sided exact McNemar p<.05 per comparison, pooled post-cutoff set, n>=200.

Input: data/predictions.jsonl — one line per exam item:
  {"id":..., "label":"Y|N", "majority":"Y|N", "metadata":"Y|N",
   "name_only":"Y|N", "replica":"Y|N"}
Output: data/scorecard.json + human-readable verdict on stdout.
"""
from __future__ import annotations
import json
import math
import sys

MARGIN = 10.0
ALPHA = 0.025  # Bonferroni-corrected: two replica arms tested
MIN_N = 200
ARMS = ["majority", "metadata", "name_only", "retrieval", "rsi_persona"]
REPLICA_ARMS = ["retrieval", "rsi_persona"]


def mcnemar_one_sided(b: int, c: int) -> float:
    """Exact one-sided McNemar: P(X >= b) for X~Binomial(b+c, 0.5).
    b = items replica got right and rival got wrong; c = the reverse."""
    n = b + c
    if n == 0:
        return 1.0
    return sum(math.comb(n, k) for k in range(b, n + 1)) / (2 ** n)


def main() -> None:
    path = sys.argv[1] if len(sys.argv) > 1 else "data/predictions.jsonl"
    rows = [json.loads(l) for l in open(path, encoding="utf-8")]
    n = len(rows)
    acc = {a: sum(r[a] == r["label"] for r in rows) / n * 100 for a in ARMS}

    per_arm = {}
    for arm in REPLICA_ARMS:
        comparisons = {}
        for rival in ("metadata", "name_only"):
            b = sum(r[arm] == r["label"] and r[rival] != r["label"] for r in rows)
            c = sum(r[arm] != r["label"] and r[rival] == r["label"] for r in rows)
            comparisons[rival] = {
                "margin_points": acc[arm] - acc[rival],
                "discordant_b": b, "discordant_c": c,
                "p_one_sided": mcnemar_one_sided(b, c),
            }
        floor_ok = acc[arm] > acc["majority"]
        beats = all(
            comparisons[r]["margin_points"] >= MARGIN
            and comparisons[r]["p_one_sided"] < ALPHA
            for r in ("metadata", "name_only")
        )
        per_arm[arm] = {"comparisons": comparisons, "floor_ok": floor_ok,
                        "passes": floor_ok and beats}

    underpowered = n < MIN_N
    if underpowered:
        verdict = "UNDERPOWERED"
    elif any(per_arm[a]["passes"] for a in REPLICA_ARMS):
        verdict = "WIN"
    else:
        verdict = "LOSS"

    scorecard = {"n": n, "accuracy": acc, "per_arm": per_arm,
                 "winning_arms": [a for a in REPLICA_ARMS if per_arm[a]["passes"]],
                 "verdict": verdict}
    with open("data/scorecard.json", "w", encoding="utf-8") as f:
        json.dump(scorecard, f, indent=2)

    print(json.dumps(scorecard, indent=2))
    print(f"\nVERDICT: {verdict}"
          + ("" if verdict == "WIN" else "  -> named-judge replica dead for claims;"
             " written pivot memo due within 48h (PREREGISTRATION.md)"))


if __name__ == "__main__":
    main()
