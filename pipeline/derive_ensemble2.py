#!/usr/bin/env python3
"""ERRATUM E2 derivation — add the frozen arm (g) ensemble columns to predictions2.jsonl.

FREEZE-2 gated arm (g) as PRIMARY (ensemble >= best single arm on held-out
pre-cutoff val), but arms2.py never wrote an {model}_ensemble column, so the
frozen-primary arm was silently absent from scorecard2.json. The vote rule is
parameter-free and frozen in pipeline/ensemble_gate2.py:

    ens = "Y" if [L2, L3, L4].count("Y") >= 2 else "N"

This script derives that column mechanically from the ALREADY-RECORDED sitting
answers — no model is called, no answer is changed, no exam item is touched.
Anyone can re-run it and get byte-identical output. See FREEZE-2.md ERRATUM E2.

Usage: cd gatekeeper && python3 pipeline/derive_ensemble2.py
"""
from __future__ import annotations
import json

ARMS = ["L2", "L3", "L4"]
PATH = "data/predictions2.jsonl"

def main() -> None:
    rows = [json.loads(l) for l in open(PATH) if l.strip()]
    n_added = 0
    for r in rows:
        for m in ("gpt", "fable"):
            key = f"{m}_ensemble"
            votes = [r.get(f"{m}_{a}") for a in ARMS]
            if any(v is None for v in votes):
                continue
            ens = "Y" if votes.count("Y") >= 2 else "N"
            if r.get(key) != ens:
                r[key] = ens
                n_added += 1
    with open(PATH, "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    print(f"rows={len(rows)} ensemble cells written={n_added}")

if __name__ == "__main__":
    main()
