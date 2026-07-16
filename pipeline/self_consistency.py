#!/usr/bin/env python3
"""Lab task #0: estimate judge self-consistency (the empirical ceiling proxy).

Method (proxy, honestly labeled): within each (judge, motion_type) cell, the
outcome homogeneity — how often a randomly drawn pair of decisions in the same
cell agrees — approximates an upper bound context: if a judge's own decisions
in a cell agree X% of the time, no predictor can exceed X% within-cell without
case-specific information. This is a coarse proxy (real test-retest would need
near-identical motions); it bounds expectations, not claims.

Usage: python3 pipeline/self_consistency.py
"""
from __future__ import annotations
import json
from collections import defaultdict


def main() -> None:
    rows = [json.loads(l) for l in open("data/labeled.jsonl", encoding="utf-8")]
    cells: dict = defaultdict(list)
    for r in rows:
        cells[(r["judge"], r["motion_type"])].append(r["label"])
    report = []
    total_pairs_agree = total_pairs = 0
    for (judge, mt), labels in sorted(cells.items()):
        n = len(labels)
        if n < 5:
            continue
        y = labels.count("Y")
        agree_pairs = y * (y - 1) / 2 + (n - y) * (n - y - 1) / 2
        pairs = n * (n - 1) / 2
        total_pairs_agree += agree_pairs
        total_pairs += pairs
        report.append({"judge": judge, "motion_type": mt, "n": n,
                       "y_rate": round(y / n, 3),
                       "pair_agreement": round(agree_pairs / pairs, 3)})
    overall = total_pairs_agree / total_pairs if total_pairs else 0
    out = {"overall_within_cell_pair_agreement": round(overall, 4),
           "note": "coarse ceiling proxy — pair agreement within (judge, motion type) cells; case facts explain the rest",
           "cells": report}
    json.dump(out, open("data/self_consistency.json", "w"), indent=2)
    print(json.dumps({"overall": out["overall_within_cell_pair_agreement"],
                      "cells": len(report)}, indent=2))


if __name__ == "__main__":
    main()
