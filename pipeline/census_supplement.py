#!/usr/bin/env python3
"""Supplementary census pass: candidates surfaced by the independent roster
audit that the initial census list missed. Same counts, same method; merges
into data/census.json. Run AFTER census.py completes.

Roster-driven exclusions recorded here (decided from the roster audit BEFORE
any volume numbers were read; census.json did not exist when this was
written):
- Reyes (nyed), Bulsara (nyed): former magistrate judges — pre-2023 history
  is magistrate R&Rs, not district rulings; grounding would be contaminated.
  Censused for the record, excluded from selection.
- Nathan, Sullivan, Haight (nysd), Keenan, Mauskopf: departed/elevated/out
  of district — never queried.
"""
from __future__ import annotations
import json
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from census import count_query, CUTOFF_GPT, CUTOFF_FABLE, RATE_SECONDS

EXTRA = [
    # (assigned_to query, display name, court, excluded_reason or None)
    ("Kimba Wood", "Wood", "nysd", None),      # full name: avoid Woods collision
    ("Berman", "Berman", "nysd", None),
    ("Buchwald", "Buchwald", "nysd", None),
    ("Crotty", "Crotty", "nysd", None),
    ("Gardephe", "Gardephe", "nysd", None),
    ("Briccetti", "Briccetti", "nysd", None),
    ("Korman", "Korman", "nyed", None),
    ("Gershon", "Gershon", "nyed", None),
    ("Hurley", "Hurley", "nyed", None),        # roster caution: verify intake
    ("Merle", "Merle", "nyed", None),
    ("Reyes", "Reyes", "nyed", "former_magistrate"),
    ("Bulsara", "Bulsara", "nyed", "former_magistrate"),
]


def main() -> None:
    out = json.load(open("data/census.json"))
    ratio = out["calibration"]["ratio"]
    have = {(j["judge"], j["court"]) for j in out["judges"]}
    for i, (q, name, court, excl) in enumerate(EXTRA):
        if (name, court) in have:
            continue
        rec = {"judge": name, "court": court, "exam1": False,
               "query_name": q, "excluded": excl}
        for label, after in (("post_gpt", CUTOFF_GPT), ("post_fable", CUTOFF_FABLE)):
            total = 0
            for desc in ("order", "opinion"):
                c = count_query(court, after, assigned_to=q, description=desc)
                time.sleep(RATE_SECONDS)
                if c >= 0:
                    total += c
            rec[label + "_docs"] = total
        rec["proj_exam_gpt"] = round(rec["post_gpt_docs"] * ratio)
        rec["proj_exam_fable"] = round(rec["post_fable_docs"] * ratio)
        out["judges"].append(rec)
        print(f"[{i+1}/{len(EXTRA)}] {court}:{name:10s} "
              f"postGPT={rec['post_gpt_docs']:5d} projExam={rec['proj_exam_gpt']:4d}"
              f"{'  EXCLUDED:' + excl if excl else ''}")
    with open("data/census.json", "w") as f:
        json.dump(out, f, indent=1)
    print("merged; total censused:", len(out["judges"]))


if __name__ == "__main__":
    main()
