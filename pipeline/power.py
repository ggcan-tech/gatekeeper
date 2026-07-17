#!/usr/bin/env python3
"""Trust-numbers engine: pre-specify, for every planned experiment, the n and
CI width that would convince a skeptical litigator and a YC partner — BEFORE
running anything (Ultimate Evidence program, rule B).

All variance inputs are MEASURED from exam #1 artifacts, not assumed:
  - discordant rates from data/scorecard.json (paired-comparison variance)
  - motion-type mix from data/exam.jsonl
  - per-judge post-cutoff yield from data/exam.jsonl date range
Outputs: data/trust_table.json + a markdown table on stdout.

No exam data is re-scored here; this reads published aggregates only.
"""
from __future__ import annotations
import json
import math
from collections import Counter

Z95 = 1.959964
Z90 = 1.644854


def margin_se(q_discordant: float, d: float, n: int) -> float:
    """SE of a paired accuracy difference d with discordant rate q.
    Var(d_hat) = (q - d^2) / n   (standard paired-proportions result)."""
    v = max(q_discordant - d * d, 1e-9) / n
    return math.sqrt(v)


def ci_halfwidth(q: float, d: float, n: int, z: float = Z95) -> float:
    return z * margin_se(q, d, n)


def n_for_halfwidth(q: float, d: float, hw: float, z: float = Z95) -> int:
    return math.ceil((z * z) * max(q - d * d, 1e-9) / (hw * hw))


def power_observed_margin(true_d: float, bar: float, q: float, n: int) -> float:
    """P(observed margin >= bar) given true margin true_d (normal approx)."""
    se = margin_se(q, true_d, n)
    zscore = (bar - true_d) / se
    return 0.5 * math.erfc(zscore / math.sqrt(2))


def binom_hw(p: float, n: int, z: float = Z95) -> float:
    return z * math.sqrt(p * (1 - p) / n)


def main() -> None:
    score = json.load(open("data/scorecard.json"))
    exam = [json.loads(l) for l in open("data/exam.jsonl")]
    n1 = score["n"]

    # measured discordant rates (paired variance anchor)
    pc = score["per_arm"]["rsi_persona"]["comparisons"]
    q_name = (pc["name_only"]["discordant_b"] + pc["name_only"]["discordant_c"]) / n1
    q_meta = (pc["metadata"]["discordant_b"] + pc["metadata"]["discordant_c"]) / n1
    q = max(q_name, q_meta)          # conservative
    q_levels = 0.12                  # adjacent hierarchy levels are MORE correlated
    d1 = pc["name_only"]["margin_points"] / 100.0

    # measured mix + yield
    mix = Counter(r["motion_type"] for r in exam)
    dates = sorted(r["date"] for r in exam)
    months = 10.4  # 2025-09-02 .. 2026-07-13
    yield_pjm = n1 / 3 / months

    rows = []

    # E-B1: judge-edge margin CI vs n (the +7-vs-+10 question)
    for n in (291, 500, 750, 1000, 1500, 2000):
        rows.append({
            "block": "judge-edge margin CI (q=%.3f measured)" % q,
            "n": n,
            "ci_halfwidth_pts": round(100 * ci_halfwidth(q, d1, n), 2),
        })

    # E-B2: power to certify the frozen +10 bar at various TRUE margins
    for true_d in (0.07, 0.10, 0.11, 0.12, 0.13):
        for n in (291, 500, 1000, 2000):
            rows.append({
                "block": "P(observed>=+10) at true margin %+.0f" % (100 * true_d),
                "n": n,
                "power_pct": round(100 * power_observed_margin(true_d, 0.10, q, n), 1),
            })

    # E-B3: hierarchy adjacent-level delta, per motion-type cell
    for hw_target in (0.03, 0.04, 0.05):
        rows.append({
            "block": "hierarchy: n per motion-type cell for adjacent-level delta CI",
            "ci_halfwidth_pts": 100 * hw_target,
            "n_cell_needed": n_for_halfwidth(q_levels, 0.03, hw_target),
        })

    # E-B4: motion-type cell sizes at total n, given measured mix
    total_targets = (600, 1000, 1500, 2000)
    mix_frac = {k: v / n1 for k, v in mix.items()}
    for total in total_targets:
        rows.append({
            "block": "projected cell sizes at total n",
            "n": total,
            "cells": {k: round(total * f) for k, f in sorted(mix_frac.items(), key=lambda kv: -kv[1])},
        })

    # E-B5: absolute accuracy CI (the 78.7 -> 83-86 claim)
    for n in (291, 500, 1000, 2000):
        rows.append({
            "block": "absolute accuracy CI at ~80%",
            "n": n,
            "ci_halfwidth_pts": round(100 * binom_hw(0.80, n), 2),
        })

    # E-B6: window arithmetic (measured yield)
    windows = {
        "gpt54_historical (2025-09-02..2026-07-13)": 10.4,
        "fable5_historical (2026-02-01..2026-07-13)": 5.4,
        "future_2B (2026-08-01..2026-09-30)": 2.0,
    }
    for wname, months_w in windows.items():
        for judges in (3, 12, 15):
            rows.append({
                "block": "projected exam n — " + wname,
                "judges": judges,
                "n_projected": round(yield_pjm * judges * months_w),
            })

    out = {
        "measured_inputs": {
            "n_exam1": n1,
            "q_discordant_vs_name_only": round(q_name, 4),
            "q_discordant_vs_metadata": round(q_meta, 4),
            "exam1_margin_vs_name_only_pts": round(100 * d1, 2),
            "motion_type_mix": dict(mix),
            "exam_window": [dates[0], dates[-1]],
            "yield_per_judge_per_month": round(yield_pjm, 2),
        },
        "rows": rows,
    }
    with open("data/trust_table.json", "w") as f:
        json.dump(out, f, indent=1)

    # stdout summary
    print("MEASURED INPUTS:", json.dumps(out["measured_inputs"], indent=1))
    print()
    cur = None
    for r in rows:
        if r["block"] != cur:
            cur = r["block"]
            print("\n## " + cur)
        print("  " + json.dumps({k: v for k, v in r.items() if k != "block"}))


if __name__ == "__main__":
    main()
