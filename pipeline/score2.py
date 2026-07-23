#!/usr/bin/env python3
"""Score exam #2A — the pre-registered ESTIMATION report. No win/lose verdict.

PREREGISTRATION-2.md Track A, section "Pre-registered report": the SIX
estimands below are the ONLY quantities computed; nothing exploratory.
Every accuracy carries a 95% CI (Wilson score interval for single
proportions; normal approximation on discordant pairs for paired deltas —
the same counts score.py feeds McNemar, reported here as estimation CIs,
NOT pass/fail tests). Two-numbers rule: every replica-arm absolute accuracy
is reported next to its paired edge over name_only.

  1. hierarchy_curve        L0->L4 + controls (a,b,c) [+ ensemble if frozen],
                            pooled and per motion type
  2. judge_relevance_index  between-judge ACTUAL grant-rate spread (max-min)
                            per motion type; judges with >=10 items in cell
  3. dual_model_attribution per model: floor = name_only - majority,
                            lift = best of {L2,L3,L4} - name_only, absolute
  4. named_vs_court_delta   L4 - L2, pooled + per motion type + stratified by
                            pre-cutoff grounding size (0 / <40 / >=40 rows,
                            counted from data/grounding2.jsonl)
  5. self_consistency_v2    computed separately by self_consistency.py
  6. best_arm_absolute      best hierarchy arm, pooled + per motion type
  +  amendment_deltas       amendment log A2-A4 registered deltas: L4-L4X
                            (judge signal), L4-L4F (persona content), D0-L0
                            (doctrine lift), L4D-L4 (doctrine marginal value)

Amendment A1 (inference robustness): every POOLED paired-delta CI is reported
twice — naive item-level AND a wild cluster bootstrap clustered by judge
(Rademacher weights on judge-level score residuals, 999 resamples, seed
20260722). boot_headline=true flags deltas where the bootstrap half-width
exceeds 1.5x the naive half-width — there the bootstrap CI is the headline.

Input: data/predictions2.jsonl (pipeline/arms2.py pivot) — per row: id, label,
judge, court, motion_type, date, fable_window, then {model}_{arm} answers:
  Y | N     scored against label
  X         abstain/refusal — scored WRONG, stays in the denominator
  SKIP      arm not applicable (e.g. Vargas L4) — out of that arm's denominator
  MISSING   transport/parse error — counted + reported, out of accuracy
Models: gpt scored on all rows; fable on fable_window rows only, against
fable's own controls on that sub-window.

Usage:  python3 pipeline/score2.py [predictions2.jsonl] [grounding2.jsonl]
        SELFTEST=1 python3 pipeline/score2.py    # synthetic end-to-end check
Output: data/scorecard2.json + readable summary on stdout.
"""
from __future__ import annotations
import json
import math
import os
import random
import sys
import time
from collections import Counter, defaultdict

Z95 = 1.959964
CONTROLS = ["majority", "metadata", "name_only"]
LEVELS = ["L0", "L1", "L2", "L3", "L4"]
LIFT_ARMS = ["L2", "L3", "L4"]     # prereg: system lift = best replica arm vs (c)
AMENDMENT_ARMS = ["L4X", "L4F", "D0", "L4D"]   # amendment log A2-A4
PLACEBO_ARMS = ("L4X", "L4F")      # placebo/controls — never best-arm candidates
AMENDMENT_DELTAS = [               # (name, arm_a, arm_b): delta = a - b
    ("L4_minus_L4X", "L4", "L4X"),
    ("L4_minus_L4F", "L4", "L4F"),
    ("D0_minus_L0", "D0", "L0"),
    ("L4D_minus_L4", "L4D", "L4")]
AMENDMENT_DEFS = {
    "L4_minus_L4X": "judge-specific signal in the persona (A2 derangement placebo)",
    "L4_minus_L4F": "persona CONTENT beyond persona-shaped text (A3 fictional control)",
    "D0_minus_L0": "doctrine lift over generic (A4)",
    "L4D_minus_L4": "doctrine's marginal value on top of the named-judge persona (A4)"}
BOOT_RESAMPLES = 999               # amendment A1, frozen
BOOT_SEED = 20260722               # amendment A1, frozen
MOTION_ORDER = ["motion_to_dismiss", "summary_judgment",
                "preliminary_injunction_tro", "motion_to_compel_discovery",
                "class_certification", "daubert_expert_exclusion"]
UNDERPOWERED_N = 100               # trust-numbers: cells under 100 are flagged
MIN_JUDGE_CELL = 10                # judge-relevance: >=10 items per judge-cell
STRATA = ["0_rows", "thin_lt40", "normal_ge40"]
VALID = ("Y", "N", "X")            # X = abstain, scored wrong, in denominator


def pts(x: float) -> float:
    return round(x * 100, 2)


def wilson_ci(k: int, n: int, z: float = Z95):
    """95% Wilson score interval for a single proportion, in accuracy points."""
    if n == 0:
        return None
    p = k / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    hw = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return [pts(center - hw), pts(center + hw)]


def tally(rows: list[dict], model: str, arm: str) -> Counter:
    c: Counter = Counter()
    for r in rows:
        a = r.get(f"{model}_{arm}")
        if a in VALID:
            c[a] += 1
            if a == r["label"]:
                c["correct"] += 1
        elif a == "SKIP":
            c["SKIP"] += 1
        else:                       # None, "MISSING", or unrecognized = error
            c["MISSING"] += 1
    return c


def _wild_cluster_boot(diffs_by_judge: dict, d: float, n: int):
    """Amendment A1: wild cluster bootstrap CI clustered by judge. Rademacher
    weights (+/-1) on judge-level residual sums of the per-item score
    differences; 999 resamples, seed 20260722, percentile interval. Returns
    (lo, hi) as proportions (unrounded)."""
    rnd = random.Random(BOOT_SEED)
    resid = [sum(diffs) - len(diffs) * d
             for _, diffs in sorted(diffs_by_judge.items())]
    stats = sorted(
        d + sum(r if rnd.random() < 0.5 else -r for r in resid) / n
        for _ in range(BOOT_RESAMPLES))
    return stats[24], stats[974]        # 2.5th / 97.5th of 999


def paired_delta(rows: list[dict], model: str, arm_a: str, arm_b: str,
                 boot: bool = False) -> dict:
    """Paired accuracy difference arm_a - arm_b on items where BOTH arms gave a
    valid answer (Y/N/X; X scores wrong). CI: normal approximation on the
    discordant pairs — score.py's McNemar counts, reported as an estimation
    interval, not a hypothesis test (Var(d) = (q - d^2)/n, as pipeline/power.py).
    boot=True (pooled deltas): also the A1 judge-clustered wild bootstrap CI;
    boot_headline flags boot half-width > 1.5x naive half-width."""
    b = c = n = 0
    diffs_by_judge: dict[str, list[int]] = defaultdict(list)
    for r in rows:
        va, vb = r.get(f"{model}_{arm_a}"), r.get(f"{model}_{arm_b}")
        if va not in VALID or vb not in VALID:
            continue
        n += 1
        s = (1 if va == r["label"] else 0) - (1 if vb == r["label"] else 0)
        if s > 0:
            b += 1
        elif s < 0:
            c += 1
        diffs_by_judge[r["judge"]].append(s)
    if n == 0:
        return {"n_pairs": 0, "delta_points": None, "ci95_points": None,
                "discordant_b": 0, "discordant_c": 0,
                "note": "no items where both arms gave a valid answer"}
    d = (b - c) / n
    q = (b + c) / n
    se = math.sqrt(max(q - d * d, 0.0) / n)
    out = {"n_pairs": n, "delta_points": pts(d),
           "ci95_points": [pts(d - Z95 * se), pts(d + Z95 * se)],
           "discordant_b": b, "discordant_c": c}
    if boot:
        blo, bhi = _wild_cluster_boot(diffs_by_judge, d, n)
        out["ci95_boot_points"] = [pts(blo), pts(bhi)]
        out["boot_n_judges"] = len(diffs_by_judge)
        out["boot_headline"] = (bhi - blo) / 2 > 1.5 * (Z95 * se)
        if len(diffs_by_judge) == 1:
            out["boot_note"] = ("single judge cluster — wild cluster bootstrap "
                                "degenerate (interval collapses to the point)")
    return out


def acc_entry(rows: list[dict], model: str, arm: str, with_edge: bool,
              boot_edge: bool = False) -> dict:
    c = tally(rows, model, arm)
    n = c["Y"] + c["N"] + c["X"]
    entry = {"n": n, "correct": c["correct"],
             "acc_points": pts(c["correct"] / n) if n else None,
             "ci95_points": wilson_ci(c["correct"], n),
             "x_count": c["X"], "skip_count": c["SKIP"],
             "missing_count": c["MISSING"],
             "underpowered": n < UNDERPOWERED_N}
    if with_edge:                   # two-numbers rule: absolute never travels alone
        entry["edge_over_name_only"] = paired_delta(rows, model, arm, "name_only",
                                                    boot=boot_edge)
    return entry


def motion_types(rows: list[dict]) -> list[str]:
    present = {r["motion_type"] for r in rows}
    return [m for m in MOTION_ORDER if m in present] + sorted(present - set(MOTION_ORDER))


# ---- estimand 1: hierarchy curve --------------------------------------------

def hierarchy_curve(scope: list[dict], model: str, arms_all: list[str]) -> dict:
    def block(rows, boot):
        return {arm: acc_entry(rows, model, arm, with_edge=arm not in CONTROLS,
                               boot_edge=boot)
                for arm in arms_all}
    return {"pooled": block(scope, True),   # A1: pooled deltas carry boot CI
            "per_motion_type": {mt: block([r for r in scope
                                           if r["motion_type"] == mt], False)
                                for mt in motion_types(scope)}}


# ---- estimand 2: judge-relevance index (labels only, model-independent) -----

def judge_relevance(rows: list[dict]) -> dict:
    out = {}
    for mt in motion_types(rows):
        mt_rows = [r for r in rows if r["motion_type"] == mt]
        by_judge: dict[str, list[str]] = defaultdict(list)
        for r in mt_rows:
            by_judge[r["judge"]].append(r["label"])
        per_judge = {}
        for judge, labels in sorted(by_judge.items()):
            nj = len(labels)
            if nj < MIN_JUDGE_CELL:
                continue
            y = labels.count("Y")
            per_judge[judge] = {"n": nj, "grant_rate_points": pts(y / nj),
                                "ci95_points": wilson_ci(y, nj)}
        entry = {"n_items": len(mt_rows), "n_judges_qualifying": len(per_judge),
                 "min_items_per_judge": MIN_JUDGE_CELL, "per_judge": per_judge}
        if len(per_judge) >= 2:
            hi = max(per_judge, key=lambda j: per_judge[j]["grant_rate_points"])
            lo = min(per_judge, key=lambda j: per_judge[j]["grant_rate_points"])
            entry["spread_points"] = round(per_judge[hi]["grant_rate_points"]
                                           - per_judge[lo]["grant_rate_points"], 2)
            entry["max_judge"], entry["min_judge"] = hi, lo
        else:
            entry["spread_points"] = None
            entry["note"] = f"fewer than 2 judges with >={MIN_JUDGE_CELL} items"
        out[mt] = entry
    return out


# ---- estimand 3: dual-model attribution -------------------------------------

def best_by_pooled_acc(scope: list[dict], model: str, candidates: list[str]):
    best, best_acc = None, -1.0
    for arm in candidates:
        c = tally(scope, model, arm)
        n = c["Y"] + c["N"] + c["X"]
        if n and c["correct"] / n > best_acc:
            best, best_acc = arm, c["correct"] / n
    return best


def attribution(scope: list[dict], model: str) -> dict:
    best = best_by_pooled_acc(scope, model, LIFT_ARMS)
    return {"model_floor_name_only_minus_majority":
                paired_delta(scope, model, "name_only", "majority", boot=True),
            "best_replica_arm": best,
            "system_lift_best_minus_name_only":
                paired_delta(scope, model, best, "name_only", boot=True)
                if best else None,
            "best_replica_absolute":
                acc_entry(scope, model, best, with_edge=True, boot_edge=True)
                if best else None}


# ---- estimand 4: named-vs-court delta ---------------------------------------

def stratum_of(count: int) -> str:
    return "0_rows" if count == 0 else ("thin_lt40" if count < 40 else "normal_ge40")


def grounding_rows_per_judge(grounding_path: str, judges: list[str]) -> dict:
    counts: Counter = Counter()
    for l in open(grounding_path, encoding="utf-8"):
        counts[json.loads(l)["judge"]] += 1
    return {j: counts.get(j, 0) for j in sorted(judges)}


def named_vs_court(scope: list[dict], model: str, gcounts: dict) -> dict:
    strata = {}
    for s in STRATA:
        srows = [r for r in scope if stratum_of(gcounts.get(r["judge"], 0)) == s]
        strata[s] = {"judges": sorted({r["judge"] for r in srows}),
                     "n_rows": len(srows),
                     "L4_minus_L2": paired_delta(srows, model, "L4", "L2")}
    return {"pooled": paired_delta(scope, model, "L4", "L2", boot=True),
            "per_motion_type": {mt: paired_delta(
                [r for r in scope if r["motion_type"] == mt], model, "L4", "L2")
                for mt in motion_types(scope)},
            "by_grounding_stratum": strata}


# ---- amendment log A2-A4: registered deltas ---------------------------------

def amendment_delta_block(scope: list[dict], model: str,
                          arms_present: list[str]) -> dict:
    out = {}
    for name, arm_a, arm_b in AMENDMENT_DELTAS:
        absent = [a for a in (arm_a, arm_b) if a not in arms_present]
        if absent:
            out[name] = {"status": f"not scored — arm {absent[0]} not "
                                   "registered/frozen (no column in predictions)"}
            continue
        out[name] = {"pooled": paired_delta(scope, model, arm_a, arm_b, boot=True),
                     "per_motion_type": {mt: paired_delta(
                         [r for r in scope if r["motion_type"] == mt],
                         model, arm_a, arm_b) for mt in motion_types(scope)}}
    return out


# ---- estimand 6: absolute accuracy of the best arm --------------------------

def best_arm_absolute(scope: list[dict], model: str, candidates: list[str]) -> dict:
    best = best_by_pooled_acc(scope, model, candidates)
    if best is None:
        return {"arm": None, "note": "no hierarchy arm with any valid answers"}
    return {"arm": best, "candidates": candidates,
            "pooled": acc_entry(scope, model, best, with_edge=True, boot_edge=True),
            "per_motion_type": {mt: acc_entry(
                [r for r in scope if r["motion_type"] == mt], model, best,
                with_edge=True) for mt in motion_types(scope)}}


# ---- bookkeeping: X / SKIP / MISSING per model/arm --------------------------

def answer_counts(scope: list[dict], model: str, arms_all: list[str]) -> dict:
    out = {}
    for arm in arms_all:
        c = tally(scope, model, arm)
        out[arm] = {"Y": c["Y"], "N": c["N"], "X": c["X"],
                    "SKIP": c["SKIP"], "MISSING": c["MISSING"]}
    return out


# ---- the scorecard ----------------------------------------------------------

def score(pred_path: str, grounding_path: str) -> dict:
    rows = [json.loads(l) for l in open(pred_path, encoding="utf-8")]
    scopes = {}
    for model, scope in (("gpt", rows),
                         ("fable", [r for r in rows if r.get("fable_window")])):
        if any(f"{model}_name_only" in r for r in scope):
            scopes[model] = scope
    if not scopes:
        sys.exit(f"REFUSING TO SCORE: no model answer columns in {pred_path}")
    gcounts = grounding_rows_per_judge(grounding_path,
                                       sorted({r["judge"] for r in rows}))
    arms_by_model = {m: CONTROLS + LEVELS
                        + [a for a in AMENDMENT_ARMS
                           if any(f"{m}_{a}" in r for r in s)]
                        + (["ensemble"] if any(f"{m}_ensemble" in r for r in s) else [])
                     for m, s in scopes.items()}

    sc = {"exam": "2A",
          "kind": "estimation report — no win/lose verdict (PREREGISTRATION-2.md Track A)",
          "generated": time.strftime("%Y-%m-%d"),
          "input": pred_path, "grounding": grounding_path, "n_rows": len(rows),
          "models": {m: {"n_rows": len(s), "arms": arms_by_model[m],
                         "window": "all rows" if m == "gpt"
                                   else "fable_window rows only, own controls"}
                     for m, s in scopes.items()},
          "notes": {
              "scoring": "X (abstain) scored wrong, in denominator; SKIP out of "
                         "that arm's denominator; MISSING counted, out of accuracy",
              "ci": "Wilson 95% for proportions; paired deltas: normal approx "
                    "on discordant pairs (estimation, not a test)",
              "underpowered": f"cells with n<{UNDERPOWERED_N} flagged per "
                              "docs/trust-numbers.md; CIs still shown",
              "two_numbers_rule": "every replica-arm absolute accuracy carries "
                                  "edge_over_name_only alongside",
              "boot": "A1: every POOLED paired delta carries ci95_boot_points "
                      f"(wild cluster bootstrap by judge, Rademacher weights, "
                      f"{BOOT_RESAMPLES} resamples, seed {BOOT_SEED}); "
                      "boot_headline=true where boot half-width > 1.5x naive "
                      "— there the boot CI is the headline number"}}

    sc["answer_counts"] = {m: answer_counts(s, m, arms_by_model[m])
                           for m, s in scopes.items()}
    sc["hierarchy_curve"] = {m: hierarchy_curve(s, m, arms_by_model[m])
                             for m, s in scopes.items()}
    sc["judge_relevance_index"] = {
        "note": "ACTUAL grant rates from labels — corpus property, model-independent",
        "full_window": judge_relevance(rows),
        "fable_window": judge_relevance([r for r in rows if r.get("fable_window")])}
    sc["dual_model_attribution"] = {m: attribution(s, m) for m, s in scopes.items()}
    sc["named_vs_court_delta"] = {
        "grounding_rows_per_judge": gcounts,
        "strata": {"0_rows": "no pre-cutoff grounding (L4 SKIP by construction)",
                   "thin_lt40": "1-39 pre-cutoff grounding rows",
                   "normal_ge40": ">=40 pre-cutoff grounding rows"},
        "per_model": {m: named_vs_court(s, m, gcounts) for m, s in scopes.items()}}
    sc["self_consistency_v2"] = {"status": "computed separately by self_consistency.py"}
    sc["best_arm_absolute"] = {m: best_arm_absolute(
        s, m, [a for a in arms_by_model[m]
               if a not in CONTROLS and a not in PLACEBO_ARMS])
        for m, s in scopes.items()}
    sc["amendment_deltas"] = {
        "definitions": AMENDMENT_DEFS,
        "per_model": {m: amendment_delta_block(s, m, arms_by_model[m])
                      for m, s in scopes.items()}}
    return sc


# ---- readable summary -------------------------------------------------------

def _f(e) -> str:
    if not e or e.get("acc_points") is None:
        return "(no data)"
    lo, hi = e["ci95_points"]
    s = f"{e['acc_points']:5.1f} [{lo:.1f}, {hi:.1f}] n={e['n']}"
    if e.get("underpowered"):
        s += " (underpowered)"
    return s


def _d(d) -> str:
    if not d or d.get("delta_points") is None:
        return "(no pairs)"
    lo, hi = d["ci95_points"]
    s = f"{d['delta_points']:+.1f} [{lo:+.1f}, {hi:+.1f}]"
    if d.get("ci95_boot_points"):
        blo, bhi = d["ci95_boot_points"]
        s += f" boot[{blo:+.1f}, {bhi:+.1f}]" + ("*" if d.get("boot_headline") else "")
    return s + f" pairs={d['n_pairs']}"


def print_summary(sc: dict) -> None:
    bar = "=" * 74
    print(bar)
    print(f"EXAM #2A SCORECARD — estimation report, NO VERDICT   rows={sc['n_rows']}")
    print(bar)
    for m, minfo in sc["models"].items():
        print(f"\n[{m}] {minfo['window']}  n={minfo['n_rows']}")
        print("  hierarchy, pooled (acc [95% CI]; edge = paired pts over name_only):")
        for arm, e in sc["hierarchy_curve"][m]["pooled"].items():
            line = f"    {arm:<10}{_f(e)}"
            if "edge_over_name_only" in e:
                line += f"   edge {_d(e['edge_over_name_only'])}"
            print(line)
        print("  hierarchy per motion type (acc pts L0/L1/L2/L3/L4):")
        for mt, blk in sc["hierarchy_curve"][m]["per_motion_type"].items():
            vals = "/".join("--" if blk[a]["acc_points"] is None
                            else f"{blk[a]['acc_points']:.1f}" for a in LEVELS)
            flag = " (underpowered)" if blk[LEVELS[0]]["underpowered"] else ""
            print(f"    {mt:<28}n={blk[LEVELS[0]]['n']:<5}{vals}{flag}")
        att = sc["dual_model_attribution"][m]
        print(f"  attribution: floor (name_only-majority) "
              f"{_d(att['model_floor_name_only_minus_majority'])}")
        print(f"               best replica={att['best_replica_arm']}  "
              f"lift {_d(att['system_lift_best_minus_name_only'])}  "
              f"abs {_f(att['best_replica_absolute'])}")
        nvc = sc["named_vs_court_delta"]["per_model"][m]
        print(f"  named-vs-court (L4-L2): pooled {_d(nvc['pooled'])}")
        for s_name, se in nvc["by_grounding_stratum"].items():
            judges = ",".join(se["judges"]) or "-"
            print(f"    {s_name:<13}[{judges}] {_d(se['L4_minus_L2'])}")
        amd = sc["amendment_deltas"]["per_model"][m]
        print("  amendment deltas (pooled; A2-A4):")
        for name, _, _ in AMENDMENT_DELTAS:
            e = amd[name]
            if "status" in e:
                print(f"    {name:<14}{e['status']}")
            else:
                print(f"    {name:<14}{_d(e['pooled'])}")
        ba = sc["best_arm_absolute"][m]
        print(f"  best arm absolute: {ba['arm']} {_f(ba.get('pooled'))}"
              f"   edge {_d(ba.get('pooled', {}).get('edge_over_name_only'))}")
        cnt = sc["answer_counts"][m]
        print(f"  abstain X={sum(a['X'] for a in cnt.values())}  "
              f"MISSING={sum(a['MISSING'] for a in cnt.values())}  "
              f"SKIP={sum(a['SKIP'] for a in cnt.values())}  (per-arm in JSON)")
    print("\njudge-relevance (full window, actual grant-rate spread, "
          f"judges with >={MIN_JUDGE_CELL} items):")
    for mt, e in sc["judge_relevance_index"]["full_window"].items():
        if e["spread_points"] is None:
            print(f"    {mt:<28}n={e['n_items']:<5}spread n/a "
                  f"({e['n_judges_qualifying']} qualifying judges)")
        else:
            pj = e["per_judge"]
            print(f"    {mt:<28}n={e['n_items']:<5}spread {e['spread_points']:5.1f} pts"
                  f"  ({e['min_judge']} {pj[e['min_judge']]['grant_rate_points']:.0f}"
                  f" -> {e['max_judge']} {pj[e['max_judge']]['grant_rate_points']:.0f},"
                  f" {e['n_judges_qualifying']} judges)")
    print("\nself-consistency v2: computed separately by self_consistency.py")
    print("boot[..] = A1 wild cluster bootstrap CI by judge (999 resamples, "
          "seed 20260722); * = boot is the headline (half-width > 1.5x naive)")


# ---- SELFTEST=1: synthetic end-to-end check ---------------------------------

def _walk_assert_finite(obj, path="$") -> None:
    if obj is None or isinstance(obj, bool):
        return
    if isinstance(obj, (int, float)):
        assert math.isfinite(obj), f"non-finite number at {path}: {obj}"
    elif isinstance(obj, dict):
        for k, v in obj.items():
            _walk_assert_finite(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            _walk_assert_finite(v, f"{path}[{i}]")


def selftest() -> None:
    import tempfile
    rnd = random.Random(20260722)
    tmp = tempfile.mkdtemp(prefix="score2_selftest_")
    motions = ["motion_to_dismiss", "summary_judgment", "preliminary_injunction_tro"]
    judges = {"Alpha": {"court": "SDNY", "grounding": 45,   # normal stratum
                        "grant": {"motion_to_dismiss": 0.80, "summary_judgment": 0.60,
                                  "preliminary_injunction_tro": 0.25}},
              "Zed": {"court": "EDNY", "grounding": 0,      # Vargas-like: L4 SKIP
                      "grant": {"motion_to_dismiss": 0.60, "summary_judgment": 0.50,
                                "preliminary_injunction_tro": 0.65}}}
    target = {"majority": 0.60, "metadata": 0.62, "name_only": 0.65, "L0": 0.55,
              "L1": 0.60, "L2": 0.68, "L3": 0.72, "L4": 0.80, "ensemble": 0.75,
              "L4X": 0.66, "L4F": 0.64, "D0": 0.61, "L4D": 0.82}

    def synth_answer(arm, label):
        r = rnd.random()
        if r < 0.03:
            return "X"                              # abstain
        if r < 0.045:
            return "MISSING"                        # transport error
        return label if rnd.random() < target[arm] \
            else ("N" if label == "Y" else "Y")

    ground_path = os.path.join(tmp, "grounding2_selftest.jsonl")
    with open(ground_path, "w", encoding="utf-8") as g:
        for j, info in judges.items():
            for i in range(info["grounding"]):
                g.write(json.dumps({"judge": j, "motion_type": motions[i % 3],
                                    "label": "Y" if i % 3 else "N",
                                    "date": f"2025-0{i % 8 + 1}-01"}) + "\n")

    rows, rid = [], 0
    for j, info in judges.items():
        for mt in motions:
            for i in range(10):                     # 2 judges x 3 motions x 10 = 60
                rid += 1
                label = "Y" if rnd.random() < info["grant"][mt] else "N"
                fable = i % 2 == 0
                row = {"id": rid, "label": label, "judge": j,
                       "court": info["court"], "motion_type": mt,
                       "date": (f"2026-0{i % 6 + 2}-15" if fable
                                else f"2025-10-0{i % 9 + 1}"),
                       "fable_window": fable}
                for model in (("gpt", "fable") if fable else ("gpt",)):
                    for arm in CONTROLS + LEVELS + AMENDMENT_ARMS + ["ensemble"]:
                        # mirrors arms2.py pivot: persona-bearing arms SKIP for
                        # zero-grounding judges; L4F and D0 scored for everyone
                        if arm in ("L4", "L4X", "L4D", "ensemble") \
                                and info["grounding"] == 0:
                            row[f"{model}_{arm}"] = "SKIP"
                            continue
                        row[f"{model}_{arm}"] = synth_answer(arm, label)
                rows.append(row)
    rows[0]["gpt_L0"] = "X"                         # guarantee the count paths
    rows[1]["gpt_L3"] = "MISSING"
    pred_path = os.path.join(tmp, "predictions2_selftest.jsonl")
    with open(pred_path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")

    sc = score(pred_path, ground_path)
    out_path = os.path.join(tmp, "scorecard2_selftest.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(sc, f, indent=2)

    for s in ("hierarchy_curve", "judge_relevance_index", "dual_model_attribution",
              "named_vs_court_delta", "self_consistency_v2", "best_arm_absolute",
              "amendment_deltas"):
        assert s in sc, f"missing section {s}"
    _walk_assert_finite(sc)

    def assert_boot(d, where):
        assert d.get("ci95_boot_points") is not None, f"no boot CI at {where}"
        assert all(math.isfinite(v) for v in d["ci95_boot_points"]), where
        assert isinstance(d["boot_headline"], bool), where

    for m in ("gpt", "fable"):
        pooled = sc["hierarchy_curve"][m]["pooled"]
        for arm in CONTROLS + LEVELS + AMENDMENT_ARMS + ["ensemble"]:
            assert pooled[arm]["acc_points"] is not None, (m, arm)
            assert pooled[arm]["ci95_points"] is not None, (m, arm)
        assert_boot(pooled["L4"]["edge_over_name_only"], f"{m} hierarchy L4 edge")
        att = sc["dual_model_attribution"][m]
        assert att["model_floor_name_only_minus_majority"]["delta_points"] is not None
        assert att["best_replica_arm"] in LIFT_ARMS
        assert att["system_lift_best_minus_name_only"]["delta_points"] is not None
        assert_boot(att["model_floor_name_only_minus_majority"], f"{m} floor")
        assert_boot(att["system_lift_best_minus_name_only"], f"{m} lift")
        nvc = sc["named_vs_court_delta"]["per_model"][m]
        assert nvc["pooled"]["delta_points"] is not None
        assert_boot(nvc["pooled"], f"{m} named_vs_court pooled")
        assert nvc["by_grounding_stratum"]["0_rows"]["L4_minus_L2"]["n_pairs"] == 0
        assert nvc["by_grounding_stratum"]["normal_ge40"]["L4_minus_L2"]["delta_points"] is not None
        amd = sc["amendment_deltas"]["per_model"][m]
        for name, _, _ in AMENDMENT_DELTAS:
            assert amd[name]["pooled"]["delta_points"] is not None, (m, name)
            assert_boot(amd[name]["pooled"], f"{m} {name}")
            assert amd[name]["per_motion_type"], (m, name)
        ba = sc["best_arm_absolute"][m]
        assert ba["pooled"]["edge_over_name_only"] is not None
        assert not set(ba["candidates"]) & set(PLACEBO_ARMS), "placebo arm a candidate"
        assert {"D0", "L4D"} <= set(ba["candidates"]), "D0/L4D missing from candidates"
    jr = sc["judge_relevance_index"]["full_window"]
    assert len(jr) == 3 and all(jr[mt]["spread_points"] is not None for mt in jr)
    cnt = sc["answer_counts"]["gpt"]
    assert sum(a["X"] for a in cnt.values()) >= 1
    assert sum(a["MISSING"] for a in cnt.values()) >= 1
    assert cnt["L4"]["SKIP"] == cnt["L4X"]["SKIP"] == cnt["L4D"]["SKIP"] == 30
    assert cnt["D0"]["SKIP"] == cnt["L4F"]["SKIP"] == 0   # scored for everyone
    assert sc["self_consistency_v2"]["status"] == \
        "computed separately by self_consistency.py"

    print_summary(sc)
    print(f"\nSELFTEST PASSED — synthetic scorecard at {out_path}")


def main() -> None:
    if os.environ.get("SELFTEST") == "1":
        selftest()
        return
    pred_path = sys.argv[1] if len(sys.argv) > 1 else "data/predictions2.jsonl"
    grounding_path = sys.argv[2] if len(sys.argv) > 2 else "data/grounding2.jsonl"
    if not os.path.exists(pred_path):
        sys.exit(f"REFUSING TO SCORE: {pred_path} not found — run the sitting "
                 "(pipeline/arms2.py) first. SELFTEST=1 for a synthetic check.")
    sc = score(pred_path, grounding_path)
    with open("data/scorecard2.json", "w", encoding="utf-8") as f:
        json.dump(sc, f, indent=2)
    print_summary(sc)
    print("\nwrote data/scorecard2.json")


if __name__ == "__main__":
    main()
