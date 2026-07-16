#!/usr/bin/env python3
"""Leakage audit (frozen protocol): a blinded arm — same model, same stripped
inputs, NO judge identity, NO grounding — must not beat the majority-class arm
by more than 3 points. Exact rule: audit FAILS iff a one-sided paired test
rejects H0: blinded accuracy <= majority + 3 pts at p < .05.

If the blinded model can guess outcomes from the input text alone, the inputs
leak their answers and the exam is invalid until inputs are rebuilt (one
rebuild allowed; fallback = docket-derived inputs only).

Usage: python3 pipeline/leakage_audit.py
Output: data/leakage_audit.json
"""
from __future__ import annotations
import json
import math
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import arms


def main() -> None:
    exam = [json.loads(l) for l in open("data/exam.jsonl", encoding="utf-8")]
    grounding = [json.loads(l) for l in open("data/grounding.jsonl", encoding="utf-8")]

    counts: dict = {}
    for g in grounding:
        counts.setdefault(g["motion_type"], {"Y": 0, "N": 0})[g["label"]] += 1
    majority = {mt: ("Y" if c["Y"] >= c["N"] else "N") for mt, c in counts.items()}

    n = len(exam)
    blinded_hits = majority_hits = 0
    b_disc = c_disc = 0  # blinded-right/majority-wrong and the reverse
    for i, item in enumerate(exam):
        blind = arms.call_model(arms.SYSTEM_BASE, arms.build_inputs(item))
        maj = majority.get(item["motion_type"], "N")
        br, mr = blind == item["label"], maj == item["label"]
        blinded_hits += br
        majority_hits += mr
        if br and not mr:
            b_disc += 1
        elif mr and not br:
            c_disc += 1
        if i % 25 == 0:
            print(f"{i}/{n}", file=sys.stderr)
        time.sleep(0.2)

    blind_acc = blinded_hits / n * 100
    maj_acc = majority_hits / n * 100
    margin = blind_acc - maj_acc
    # One-sided paired exact test of H0: blinded <= majority + 3 pts.
    # Handicap the majority arm by 3 points (0.03*n extra wins) and test discordants.
    handicap = round(0.03 * n)
    b, c = b_disc, c_disc + handicap
    total = b + c
    p = sum(math.comb(total, k) for k in range(b, total + 1)) / (2 ** total) if total else 1.0
    audit_fail = p < 0.05

    result = {"n": n, "blinded_acc": round(blind_acc, 1), "majority_acc": round(maj_acc, 1),
              "margin_points": round(margin, 1), "p_one_sided_vs_majority_plus_3": round(p, 4),
              "verdict": "FAIL — inputs leak; rebuild required" if audit_fail else "PASS"}
    json.dump(result, open("data/leakage_audit.json", "w"), indent=2)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
