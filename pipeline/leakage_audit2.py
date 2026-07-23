#!/usr/bin/env python3
"""Leakage audit for exam #2A (frozen protocol, identical rule to exam #1's
pipeline/leakage_audit.py). A blinded arm — same model, same stripped inputs, NO
judge identity, NO grounding — must not beat majority-class by >3 points.

Audit FAILS iff a one-sided paired test rejects H0: blinded <= majority + 3 pts
at p < .05. Fail => inputs leak; one rebuild allowed; fallback = docket-derived
inputs only (counts as audit-passed), per config.yaml.

Serial OpenAI consumer. Run pre-freeze; hash the output in FREEZE-2.
Usage: cd gatekeeper && python3 -u pipeline/leakage_audit2.py
Output: data/leakage_audit2.json
"""
from __future__ import annotations
import json
import math
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import arms
import arms2


def main() -> None:
    exam = arms2._load_jsonl("data/exam2.jsonl")
    grounding = arms2._load_jsonl("data/grounding2.jsonl")

    counts: dict = {}
    for g in grounding:
        counts.setdefault(g["motion_type"], {"Y": 0, "N": 0})[g["label"]] += 1
    majority = {mt: ("Y" if c["Y"] >= c["N"] else "N") for mt, c in counts.items()}

    n = 0
    blinded_hits = majority_hits = 0
    b_disc = c_disc = 0  # blinded-right/majority-wrong and reverse
    t0 = time.time()
    for i, item in enumerate(exam):
        if "label" not in item:
            continue
        # blinded: SYSTEM_BASE only, no identity, no court, no grounding
        blind = arms.call_model(arms.SYSTEM_BASE,
                                arms2.base_input(item, include_court=False))
        maj = majority.get(item["motion_type"], "N")
        br, mr = blind == item["label"], maj == item["label"]
        blinded_hits += br
        majority_hits += mr
        if br and not mr:
            b_disc += 1
        elif mr and not br:
            c_disc += 1
        n += 1
        if i % 50 == 0:
            print(f"{i}/{len(exam)}  {n/(max(time.time()-t0,1)):.1f}/s", flush=True)

    blinded_acc = 100 * blinded_hits / n
    majority_acc = 100 * majority_hits / n
    margin = blinded_acc - majority_acc
    # one-sided paired McNemar-style test of blinded > majority + 3pts:
    # shift threshold by 3 points worth of items, use normal approx on discordants.
    thresh_items = 0.03 * n
    b_adj = b_disc - thresh_items
    denom = math.sqrt(b_disc + c_disc) if (b_disc + c_disc) else 1.0
    z = (b_adj - c_disc) / denom
    # one-sided p that blinded exceeds majority+3
    p = 0.5 * math.erfc(z / math.sqrt(2))
    failed = p < 0.05 and margin > 3.0
    out = {
        "n": n,
        "blinded_accuracy": round(blinded_acc, 2),
        "majority_accuracy": round(majority_acc, 2),
        "margin_points": round(margin, 2),
        "discordant_blinded_right": b_disc,
        "discordant_majority_right": c_disc,
        "threshold_points": 3.0,
        "z": round(z, 3),
        "p_one_sided": round(p, 4),
        "audit_failed": failed,
        "verdict": ("FAIL — inputs may leak; rebuild or fall back to docket-derived"
                    if failed else "PASS — blinded arm does not beat majority+3"),
        "rule": "FAIL iff one-sided p<.05 that blinded > majority+3pts",
        "generated": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    json.dump(out, open("data/leakage_audit2.json", "w"), indent=2)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
