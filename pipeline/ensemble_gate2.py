#!/usr/bin/env python3
"""Arm (g) pre-cutoff validation gate (PREREGISTRATION-2: arm g registered only if
its method is frozen and developed on pre-cutoff validation slices exclusively).

The ensemble is parameter-free (majority vote of L2/L3/L4), so there is nothing to
tune — this is a SOUNDNESS gate: on held-out pre-cutoff data the personas never
trained on, does majority{L2,L3,L4} at least match the best single arm? If yes,
arm (g) is reported as a primary arm; if no, it is reported SUPPLEMENTARY only.
Either way the numbers are frozen here, before the sitting, and disclosed.

Val slice = each judge's persona-loop validation slice (SEED=42, 25%), which was
held out of that judge's L4 persona training. For fairness the L3 retrieval pool
excludes the val items themselves. (Disclosed limitation: the L2 pooled persona
and the retrieval pools of OTHER judges did see these rows; one row's influence on
a pooled persona is negligible. Reported, not hidden.)

Serial OpenAI consumer. Usage: cd gatekeeper && python3 -u pipeline/ensemble_gate2.py
Output: data/ensemble_gate2.json
"""
from __future__ import annotations
import json
import os
import random
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import arms
import arms2

SEED = 42
VAL_SLICE = 0.25
ARMS = ["L2", "L3", "L4"]


def main() -> None:
    grounding = arms2._load_jsonl("data/grounding2.jsonl")
    exam = arms2._load_jsonl("data/exam2.jsonl")
    ctx = arms2.load_context(exam)  # personas, pool_personas, bios, grounding

    by_judge: dict = {}
    for g in grounding:
        by_judge.setdefault(g["judge"], []).append(g)

    val_items, val_ids = [], set()
    for judge, items in by_judge.items():
        if judge in arms2.NO_PERSONA_JUDGES:
            continue
        it = list(items)
        random.Random(SEED).shuffle(it)
        n_val = max(10, round(len(it) * VAL_SLICE))
        for v in it[:n_val]:
            val_items.append(v)
            val_ids.add(v.get("id") or id(v))

    # retrieval pool excludes the held-out val items (no self-leak into L3)
    clean_ground = [g for g in grounding if (g.get("id") or id(g)) not in val_ids]
    gate_ctx = dict(ctx, grounding=clean_ground)

    hits = {a: 0 for a in ARMS}
    ens_hits = 0
    n = 0
    t0 = time.time()
    for i, item in enumerate(val_items):
        if "label" not in item:
            continue
        preds = {}
        for a in ARMS:
            system, user = arms2.build_arm_prompt(a, item, gate_ctx)
            preds[a] = arms.call_model(system, user)
            hits[a] += preds[a] == item["label"]
        votes = [preds[a] for a in ARMS]
        ens = "Y" if votes.count("Y") >= 2 else "N"
        ens_hits += ens == item["label"]
        n += 1
        if i % 25 == 0:
            print(f"{i}/{len(val_items)}  {n/(max(time.time()-t0,1)):.1f}/s", flush=True)

    acc = {a: round(100 * hits[a] / n, 2) for a in ARMS}
    ens_acc = round(100 * ens_hits / n, 2)
    best_single = max(acc.values())
    best_arm = max(acc, key=acc.get)
    passed = ens_acc >= best_single
    out = {
        "n_val": n,
        "single_arm_accuracy": acc,
        "best_single_arm": best_arm,
        "best_single_accuracy": best_single,
        "ensemble_accuracy": ens_acc,
        "ensemble_minus_best_single_points": round(ens_acc - best_single, 2),
        "gate_passed": passed,
        "decision": ("arm_g PRIMARY (ensemble >= best single arm on held-out "
                     "pre-cutoff val)" if passed else
                     "arm_g SUPPLEMENTARY (ensemble did not beat best single arm "
                     "on val; reported but not primary)"),
        "method": "majority vote of L2,L3,L4 — parameter-free, frozen in arms2.py",
        "val_definition": "per-judge persona-loop val slice (SEED=42, 25%), held "
                          "out of L4 training; L3 retrieval pool excludes val items",
        "disclosed_limitation": "L2 pooled persona and other judges' retrieval pools "
                                "saw these rows; per-row influence on a pooled "
                                "persona is negligible.",
        "generated": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    json.dump(out, open("data/ensemble_gate2.json", "w"), indent=2)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
