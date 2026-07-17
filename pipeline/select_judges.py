#!/usr/bin/env python3
"""Apply the PREREGISTRATION-2.md mechanical selection rule to census.json
and write data/judges2.json (the exam #2A judge list, immutable at freeze).

Rule: top-12 SDNY + top-3 EDNY among NEW judges by proj_exam_gpt.
Exclusions: exam-1 judges; roster-departed (never censused); former
magistrates (flagged in census supplement); proj_exam_gpt < 40.
"""
from __future__ import annotations
import json

QUOTA = {"nysd": 12, "nyed": 3}
FLOOR = 40

census = json.load(open("data/census.json"))
pool = [j for j in census["judges"]
        if not j["exam1"] and not j.get("excluded")
        and j["proj_exam_gpt"] >= FLOOR]

selected, table = [], []
for court, k in QUOTA.items():
    ranked = sorted((j for j in pool if j["court"] == court),
                    key=lambda j: (-j["proj_exam_gpt"], -j["post_gpt_docs"]))
    for j in ranked[:k]:
        selected.append({"judge": j["judge"], "court": j["court"],
                         "query_name": j.get("query_name", j["judge"])})
        table.append(j)

out = {
    "rule": "top-12 nysd + top-3 nyed by proj_exam_gpt; floor 40; "
            "exclusions per PREREGISTRATION-2.md; frozen at pre-registration",
    "selected": selected,
    "projected_exam_n_gpt": sum(j["proj_exam_gpt"] for j in table),
    "projected_exam_n_fable": sum(j["proj_exam_fable"] for j in table),
    "cap_per_judge": 120,
}
with open("data/judges2.json", "w") as f:
    json.dump(out, f, indent=1)

print(f"{'judge':14s} {'court':5s} {'projGPT':>7s} {'projFable':>9s}")
for j in table:
    print(f"{j['judge']:14s} {j['court']:5s} {j['proj_exam_gpt']:7d} "
          f"{j['proj_exam_fable']:9d}")
print(f"\nprojected exam n (gpt window):   {out['projected_exam_n_gpt']}")
print(f"projected exam n (fable window): {out['projected_exam_n_fable']}")
print(f"cap 120/judge -> capped n (gpt): "
      f"{sum(min(j['proj_exam_gpt'], 120) for j in table)}")
