#!/usr/bin/env python3
"""Judge census for corpus expansion (Ultimate Evidence program, rule A).

Measures, per candidate SDNY/EDNY district judge, the post-cutoff RECAP
document volume on CourtListener, and projects exam-eligible n using exam #1's
MEASURED raw->exam yield ratio (never guessed).

Counts only — no outcomes, no docket entries are read here. This keeps the
census on the clean side of the exam wall: it informs the MECHANICAL judge-
selection rule that exam #2's pre-registration freezes, and nothing else.

Usage: python3 pipeline/census.py            (writes data/census.json)
"""
from __future__ import annotations
import json
import os
import sys
import time
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ingest import _headers

BASE = "https://www.courtlistener.com/api/rest/v4/search/"
CUTOFF_GPT = "2025-08-31"      # gpt-5.4 published cutoff (exam #1 anchor)
CUTOFF_FABLE = "2026-01-31"    # claude fable/mythos 5 cutoff — VERIFY before freeze
RATE_SECONDS = float(os.environ.get("CENSUS_RATE_SECONDS", "1.2"))

# Candidate roster. Volumes self-validate (a departed judge shows ~0 post-cutoff
# docs); an independent roster audit runs in parallel and is merged before the
# selection rule is frozen. Our three exam-1 judges are included for #2B
# (future-window) projections but EXCLUDED from exam #2A new-judge selection.
EXAM1_JUDGES = {"Liman", "Furman", "Subramanian"}
CANDIDATES = [
    # SDNY
    ("Abrams", "nysd"), ("Broderick", "nysd"), ("Caproni", "nysd"),
    ("Carter", "nysd"), ("Castel", "nysd"), ("Clarke", "nysd"),
    ("Cote", "nysd"), ("Cronan", "nysd"), ("Daniels", "nysd"),
    ("Engelmayer", "nysd"), ("Failla", "nysd"), ("Furman", "nysd"),
    ("Garnett", "nysd"), ("Halpern", "nysd"), ("Hellerstein", "nysd"),
    ("Ho", "nysd"), ("Kaplan", "nysd"), ("Karas", "nysd"),
    ("Koeltl", "nysd"), ("Liman", "nysd"), ("Marrero", "nysd"),
    ("McMahon", "nysd"), ("Oetken", "nysd"), ("Preska", "nysd"),
    ("Rakoff", "nysd"), ("Ramos", "nysd"), ("Rearden", "nysd"),
    ("Rochon", "nysd"), ("Roman", "nysd"), ("Schofield", "nysd"),
    ("Seibel", "nysd"), ("Stanton", "nysd"), ("Stein", "nysd"),
    ("Subramanian", "nysd"), ("Swain", "nysd"), ("Torres", "nysd"),
    ("Vargas", "nysd"), ("Vyskocil", "nysd"), ("Woods", "nysd"),
    # EDNY
    ("Amon", "nyed"), ("Azrack", "nyed"), ("Block", "nyed"),
    ("Brodie", "nyed"), ("Brown", "nyed"), ("Chen", "nyed"),
    ("Choudhury", "nyed"), ("Cogan", "nyed"), ("Dearie", "nyed"),
    ("Donnelly", "nyed"), ("Garaufis", "nyed"), ("Glasser", "nyed"),
    ("Gonzalez", "nyed"), ("Gujarati", "nyed"), ("Hall", "nyed"),
    ("Irizarry", "nyed"), ("Komitee", "nyed"), ("Kovner", "nyed"),
    ("Kuntz", "nyed"), ("Matsumoto", "nyed"), ("Merchant", "nyed"),
    ("Morrison", "nyed"), ("Ross", "nyed"), ("Seybert", "nyed"),
    ("Vitaliano", "nyed"),
]


def count_query(court: str, after: str, assigned_to: str | None = None,
                description: str | None = None, q: str = "") -> int:
    params = {
        "type": "rd", "q": q, "court": court,
        "entry_date_filed_after": after, "count": "on",
    }
    if assigned_to:
        params["assigned_to"] = assigned_to
    if description:
        params["description"] = description
    url = BASE + "?" + urllib.parse.urlencode(params)
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers=_headers())
            with urllib.request.urlopen(req, timeout=60) as r:
                data = json.load(r)
            c = data.get("count")
            if c is None and "results" in data:
                c = data.get("count", -1)
            return int(c) if c is not None else -1
        except Exception as e:  # noqa: BLE001
            wait = 30 * (attempt + 1)
            print(f"  retry {attempt+1}: {str(e)[:70]} — {wait}s", file=sys.stderr)
            time.sleep(wait)
    return -1


def exam1_calibration() -> dict:
    """Measured raw->exam ratio on the SAME query types, post-cutoff window."""
    raw_post = 0
    for j in ("liman", "furman", "subramanian"):
        for kind in ("order", "opinion"):
            path = f"data/raw_{j}_{kind}.jsonl"
            if not os.path.exists(path):
                continue
            for line in open(path, encoding="utf-8"):
                rec = json.loads(line)
                d = rec.get("entry_date_filed") or rec.get("dateFiled") or ""
                if str(d)[:10] > CUTOFF_GPT:
                    raw_post += 1
    exam_n = sum(1 for _ in open("data/exam.jsonl"))
    return {"raw_post_cutoff_docs": raw_post, "exam_n": exam_n,
            "ratio": exam_n / raw_post if raw_post else None}


def main() -> None:
    cal = exam1_calibration()
    print(f"calibration: {cal['raw_post_cutoff_docs']} post-cutoff raw docs "
          f"-> {cal['exam_n']} exam items (ratio {cal['ratio']:.4f})")

    out = {"calibration": cal, "cutoffs": {"gpt": CUTOFF_GPT, "fable": CUTOFF_FABLE},
           "judges": [], "pi_booster": {}}

    for i, (name, court) in enumerate(CANDIDATES):
        rec = {"judge": name, "court": court, "exam1": name in EXAM1_JUDGES}
        for label, after in (("post_gpt", CUTOFF_GPT), ("post_fable", CUTOFF_FABLE)):
            total = 0
            for desc in ("order", "opinion"):
                c = count_query(court, after, assigned_to=name, description=desc)
                time.sleep(RATE_SECONDS)
                if c >= 0:
                    total += c
            rec[label + "_docs"] = total
        r = cal["ratio"] or 0
        rec["proj_exam_gpt"] = round(rec["post_gpt_docs"] * r)
        rec["proj_exam_fable"] = round(rec["post_fable_docs"] * r)
        out["judges"].append(rec)
        print(f"[{i+1}/{len(CANDIDATES)}] {court}:{name:14s} "
              f"postGPT={rec['post_gpt_docs']:5d} projExam={rec['proj_exam_gpt']:4d} "
              f"postFable={rec['post_fable_docs']:5d}")

    # PI/TRO booster: court-wide preliminary-injunction order volume (the
    # judge-decisive motion type with the thinnest cells — power.py E-B4)
    for court in ("nysd", "nyed"):
        c = count_query(court, CUTOFF_GPT, q='"preliminary injunction"',
                        description="order")
        time.sleep(RATE_SECONDS)
        out["pi_booster"][court] = c
        print(f"PI booster {court}: {c} post-cutoff PI-order docs (court-wide)")

    with open("data/census.json", "w") as f:
        json.dump(out, f, indent=1)

    ranked = sorted((j for j in out["judges"] if not j["exam1"]),
                    key=lambda j: -j["proj_exam_gpt"])
    print("\n== TOP NEW JUDGES BY PROJECTED EXAM YIELD (gpt window) ==")
    for j in ranked[:20]:
        print(f"  {j['court']}:{j['judge']:14s} proj_exam={j['proj_exam_gpt']:4d} "
              f"fable_window={j['proj_exam_fable']:4d}")
    top12 = ranked[:12]
    print(f"\ntop-12 new-judge projected exam n (gpt window): "
          f"{sum(j['proj_exam_gpt'] for j in top12)}")
    print(f"top-12 new-judge projected exam n (fable window): "
          f"{sum(j['proj_exam_fable'] for j in top12)}")


if __name__ == "__main__":
    main()
