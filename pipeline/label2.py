#!/usr/bin/env python3
"""Exam #2 labeling driver — same FROZEN schema and rules as exam #1.

Reuses pipeline/label.py's rule functions verbatim (regexes, signature check,
outcome rules). Differences, all mechanical:
- JUDGE_FULL extended to the exam-2 bench (from data/judges2.json + roster
  full names) — label.py hardcoded only exam-1's three judges.
- Reads raw2_* files (both windows) + the two legacy full-window v1 files.
- Writes labeled2.jsonl / needs_review2.jsonl — exam-1's labeled.jsonl and
  needs_review.jsonl are freeze-hashed and are never touched.

Usage: python3 pipeline/label2.py
"""
from __future__ import annotations
import glob
import json
import re
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import label as L

# last-name -> signature-matchable full name (no Jr./suffixes: the check uses
# the LAST token of this string against the "Signed by Judge ..." block)
EXAM2_FULL = {
    "Daniels": "george b. daniels", "Stein": "sidney h. stein",
    "Rochon": "jennifer l. rochon", "Torres": "analisa torres",
    "Woods": "gregory h. woods", "Ho": "dale e. ho",
    "Carter": "andrew l. carter", "Broderick": "vernon s. broderick",
    "Garnett": "margaret m. garnett", "Vargas": "jeannette a. vargas",
    "Koeltl": "john g. koeltl", "Engelmayer": "paul a. engelmayer",
    "Cogan": "brian m. cogan", "Donnelly": "ann m. donnelly",
    "Morrison": "nina r. morrison",
}
L.JUDGE_FULL.update(EXAM2_FULL)

# Pre-freeze amendment (2026-07-21, blind-audit pass 1): the 15-judge corpus
# surfaces procedural entries that carry motion-type words but are not
# substantive rulings on that motion. Categories named by the blind rater;
# excluded BEFORE classification. Logged in PREREGISTRATION-2.md.
EXTRA_EXCLUDE = [
    re.compile(r"pre-?motion (letter|conference)", re.I),
    re.compile(r"stay(ed|ing)?\b.{0,60}pending", re.I),
    re.compile(r"briefing schedule|schedul(e|ing) (order|for)", re.I),
    re.compile(r"^clerk'?s judgment", re.I),
    re.compile(r"\b23\(f\)|mandate of the .{0,40}court of appeals", re.I),
    re.compile(r"reconsider(ation)?", re.I),
    re.compile(r"\bbond\b.{0,40}(releas|exonerat)", re.I),
]


def main() -> None:
    paths = sorted(glob.glob("data/raw2_*.jsonl"))
    if not paths:
        sys.exit("no raw2 files")
    labeled, review = [], []
    stats = {"in": 0, "kept": 0, "excluded": 0, "review": 0, "sig_drop": 0,
             "party_drop": 0}
    seen = set()
    for path in paths:
        with open(path, encoding="utf-8") as f:
            for line in f:
                rec = json.loads(line)
                stats["in"] += 1
                doc_id = rec.get("id") or rec.get("docket_entry_id")
                if doc_id in seen:
                    continue
                seen.add(doc_id)
                desc = (rec.get("description") or rec.get("short_description") or "")
                chash = (rec.get("_judge"), rec.get("entry_date_filed"),
                         re.sub(r"\s+", " ", desc)[:200])
                if chash in seen:
                    continue
                seen.add(chash)
                if re.match(L.PARTY_FILING, desc, re.I):
                    stats["party_drop"] += 1
                    continue
                if any(p.search(desc) for p in EXTRA_EXCLUDE):
                    stats["excluded"] += 1
                    continue
                judge = rec.get("_judge", "")
                if judge not in L.JUDGE_FULL:
                    continue  # never label a judge outside the bench map
                if not L.signature_ok(desc, judge):
                    stats["sig_drop"] += 1
                    continue
                mtype = L.classify_motion(desc)
                if not mtype:
                    continue
                outcome = L.label_outcome(desc)
                row = {"id": doc_id, "judge": judge,
                       "date": rec.get("entry_date_filed"),
                       "docket": rec.get("docketNumber") or rec.get("docket_id"),
                       "case": rec.get("caseName"),
                       "motion_type": mtype, "description": desc,
                       "label": outcome}
                if outcome in ("Y", "N"):
                    labeled.append(row)
                    stats["kept"] += 1
                elif outcome == "EXCLUDED":
                    stats["excluded"] += 1
                else:
                    review.append(row)
                    stats["review"] += 1
    with open("data/labeled2.jsonl", "w", encoding="utf-8") as f:
        f.writelines(json.dumps(r) + "\n" for r in labeled)
    with open("data/needs_review2.jsonl", "w", encoding="utf-8") as f:
        f.writelines(json.dumps(r) + "\n" for r in review)
    post = sum(1 for r in labeled if (r["date"] or "") > "2025-08-31")
    per_j = {}
    for r in labeled:
        if (r["date"] or "") > "2025-08-31":
            per_j[r["judge"]] = per_j.get(r["judge"], 0) + 1
    print(json.dumps({**stats, "rule_labeled_post_cutoff": post,
                      "post_per_judge": per_j}, indent=1))


if __name__ == "__main__":
    main()
