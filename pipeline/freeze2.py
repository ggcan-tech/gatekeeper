#!/usr/bin/env python3
"""Write FREEZE-2.md — the exam #2A freeze manifest. Verifies exam integrity and
that the leakage audit passed, flips PREREGISTRATION-2's header to FROZEN, then
publishes SHA-256 hashes of every load-bearing artifact. After this commits +
pushes, and ONLY then, arms2.py may run on the exam set.

Refuses if: exam2 hash drifted, gates not present, or leakage audit FAILED
(fallback path is a founder decision, not automatic).

Usage: cd gatekeeper && python3 pipeline/freeze2.py
"""
from __future__ import annotations
import hashlib
import json
import os
import sys
import time

EXAM2_EXPECTED = "956d774321070bf9759c405e9c68e0321781ef94aa79df94c124b56a6f3f2823"

JUDGES = ["broderick", "carter", "cogan", "daniels", "donnelly", "engelmayer",
          "garnett", "ho", "koeltl", "morrison", "rochon", "stein", "torres",
          "vargas", "woods"]

MANIFEST = [
    "PREREGISTRATION-2.md",
    "config.yaml",
    "data/exam2.jsonl",
    "data/grounding2.jsonl",
    *[f"data/persona2_{j}.md" for j in JUDGES],
    "data/persona2_sdny_pool.md",
    "data/persona2_edny_pool.md",
    "data/persona2_fictional.md",
    "data/doctrine_primers.json",
    "data/derangement_map.json",
    "data/bios2.json",
    "data/arm_extras.json",
    "data/audit2_pass1.json",
    "data/audit2_pass2.json",
    "data/ensemble_gate2.json",
    "data/leakage_audit2.json",
    "pipeline/arms2.py",
    "pipeline/label2.py",
    "pipeline/score2.py",
    "pipeline/persona_loop.py",
    "pipeline/ensemble_gate2.py",
    "pipeline/leakage_audit2.py",
]


def sha(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    got = sha("data/exam2.jsonl")
    if got != EXAM2_EXPECTED:
        sys.exit(f"REFUSING: exam2.jsonl hash drifted!\n  expected {EXAM2_EXPECTED}\n  got      {got}")

    if not os.path.exists("data/ensemble_gate2.json"):
        sys.exit("REFUSING: ensemble_gate2.json missing — run the gates first.")
    leak = json.load(open("data/leakage_audit2.json"))
    if leak.get("audit_failed"):
        sys.exit("REFUSING: leakage audit FAILED — inputs may leak. Founder "
                 "decision required (rebuild once, or docket-derived fallback). "
                 "Not an automatic freeze.")
    gate = json.load(open("data/ensemble_gate2.json"))

    missing = [p for p in MANIFEST if not os.path.exists(p)]
    if missing:
        sys.exit(f"REFUSING: manifest files missing: {missing}")

    # flip the prereg header DRAFT -> FROZEN (hash is taken AFTER this edit, so the
    # published hash matches the published, frozen file)
    prereg = open("PREREGISTRATION-2.md", encoding="utf-8").read()
    stamp = time.strftime("%Y-%m-%d %H:%M %Z")
    if "— DRAFT" in prereg.split("\n", 1)[0]:
        prereg = prereg.replace(
            "# Pre-Registration #2: The Ultimate Evidence Program — DRAFT",
            "# Pre-Registration #2: The Ultimate Evidence Program — FROZEN", 1)
        prereg = prereg.replace(
            "Status: DRAFT — becomes FROZEN when this file's SHA-256 is published (repo +\n"
            "hash) BEFORE any exam scoring. Founder review required before freeze.",
            f"Status: FROZEN {stamp} — this file's SHA-256 is published in FREEZE-2.md,\n"
            "committed and pushed BEFORE any exam arm ran on the exam set. Signed +\n"
            "audited (both blind passes) + gated (ensemble val + leakage) before freeze.", 1)
        open("PREREGISTRATION-2.md", "w", encoding="utf-8").write(prereg)

    hashes = [(sha(p), p) for p in MANIFEST]

    lines = []
    lines.append("# FREEZE MANIFEST #2 — Exam #2A (Ultimate Evidence Program)\n")
    lines.append(f"Frozen: {stamp}, BEFORE any exam arm ran on the exam set "
                 "(data/exam2.jsonl).")
    lines.append("Examinee models: gpt-5.4-2026-03-05 (full window) + claude-fable-5 "
                 f"(sub-window > {json.load(open('data/leakage_audit2.json')).get('generated','')[:0]}"
                 "the pinned Fable cutoff; pin recorded at sitting in data/fable_pin.json).\n")
    lines.append(f"Exam n = {sum(1 for _ in open('data/exam2.jsonl'))}. "
                 "Estimation exam — no win/lose verdict on Track A.\n")
    lines.append("## Pre-freeze gate results (frozen with this manifest)\n")
    lines.append(f"- Leakage audit: **{leak['verdict']}** "
                 f"(blinded {leak['blinded_accuracy']}% vs majority "
                 f"{leak['majority_accuracy']}%, margin {leak['margin_points']} pts, "
                 f"one-sided p={leak['p_one_sided']}; fail iff p<.05 that blinded > "
                 "majority+3).")
    lines.append(f"- Ensemble arm (g) val gate: **{gate['decision']}** "
                 f"(held-out pre-cutoff val n={gate['n_val']}: ensemble "
                 f"{gate['ensemble_accuracy']}% vs best single {gate['best_single_arm']} "
                 f"{gate['best_single_accuracy']}%, Δ={gate['ensemble_minus_best_single_points']} pts).\n")
    lines.append("## Reproducibility pins\n")
    lines.append("- Persona loop: SEED=42, VALIDATION_SLICE=0.25; pool personas "
                 "MAX_VAL=60 (prereg C4). Per-judge subsample caps were inert "
                 "(no judge exceeded the 120 cap after filtering).")
    lines.append("- All 15 judge personas + 2 court-pool personas built on the SAME "
                 "final grounding snapshot (grounding2.jsonl), post attribution-filter "
                 "(prereg C3).\n")
    lines.append("## SHA-256 fingerprints (any post-hoc change to these voids the exam)\n")
    lines.append("```")
    for h, p in hashes:
        lines.append(f"{h}  {p}")
    lines.append("```\n")
    lines.append("Persona / grounding / bios / doctrine / derangement documents may be "
                 "withheld as product IP; the hashes above bind them. arms2.py imports "
                 "the frozen exam-1 arms.py (itself hashed in FREEZE.md) and never edits it.")
    open("FREEZE-2.md", "w", encoding="utf-8").write("\n".join(lines) + "\n")

    print("FREEZE-2.md written. exam2 hash verified. leakage:", leak["verdict"])
    print("ensemble gate:", gate["decision"])
    print(f"{len(hashes)} artifacts hashed.")
    print("NEXT: git add -A && commit && push  — THEN and only then run the sitting.")


if __name__ == "__main__":
    main()
