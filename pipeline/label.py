#!/usr/bin/env python3
"""Extract binary outcome labels from RECAP docket-entry descriptions.

Frozen schema (PREREGISTRATION.md): relief_substantially_granted y/n.
Deterministic rules first; ambiguous rows go to needs_review.jsonl for the
LLM extractor + the 20% hand-verification pass (min 40 items, >=95% agreement).

Usage: python3 pipeline/label.py data/raw_*.jsonl
Output: data/labeled.jsonl, data/needs_review.jsonl, stderr summary.
"""
from __future__ import annotations
import glob
import json
import re
import sys

# Contested substantive motions only (frozen inclusion list).
MOTION_PATTERNS = {
    "motion_to_dismiss": r"\bmotion(s)? to dismiss\b|\b12\(b\)",
    "summary_judgment": r"\bsummary judgment\b|\brule 56\b",
    "class_certification": r"\bclass certification\b|\bcertify (the )?class\b",
    "preliminary_injunction_tro": r"\bpreliminary injunction\b|\btemporary restraining\b|\bTRO\b",
    "motion_to_compel_discovery": r"\bmotion(s)? to compel\b|\bprotective order\b",
    "daubert_expert_exclusion": r"\bdaubert\b|\bexclude .{0,40}expert\b",
}
EXCLUDE = (r"\bextension\b|\bseal(ing)?\b|\bpro hac vice\b|\bschedul|\badjourn|\bunopposed\b"
           r"|\bspeedy trial\b|\bCJA funds\b|\bshow cause\b|\border to answer\b"
           r"|\bwithdraw(n|ing|al)?\b|\bdeadline .{0,30}extended\b")
MOOT_OR_ADMIN = r"\bmoot\b|\badministrativ|\breferred to (the )?magistrate\b"
# Party filings are not rulings (audit finding 2026-07-15: briefs leaked into corpus)
PARTY_FILING = (r"^\s*(memorandum of law|declaration|affidavit|reply memorandum|notice of|"
                r"letter addressed|brief|response in|opposition)")
# Signature checks (audit finding: magistrate + cross-judge orders leaked in)
MAGISTRATE_SIG = r"signed by magistrate judge"
JUDGE_FULL = {"Liman": "lewis j. liman", "Furman": "jesse m. furman",
              "Subramanian": "arun subramanian"}


def signature_ok(text: str, judge: str) -> bool:
    t = text.lower()
    if re.search(MAGISTRATE_SIG, t):
        return False
    if "signed by clerk of court" in t or "clerk's judgment" in t:
        return True  # clerk judgments record the district judge's ruling
    m = re.search(r"signed by (?:judge|district judge) ([a-z.\s]+?)(?:\s+on\b|\))", t)
    if m:
        return JUDGE_FULL.get(judge, "").split()[-1] in m.group(1)
    if re.search(r"hereby ordered by judge", t):
        return JUDGE_FULL.get(judge, "").split()[-1] in t
    return True  # no signature block visible: keep, let outcome rules decide

GRANT = r"\bgrant(s|ed|ing)?\b"
DENY = r"\bden(y|ies|ied|ying)\b"
PART = r"\bin part\b"


def classify_motion(text: str) -> str | None:
    t = text.lower()
    if re.search(EXCLUDE, t):
        return None
    for mtype, pat in MOTION_PATTERNS.items():
        if re.search(pat, t, re.I):
            return mtype
    return None


def label_outcome(text: str) -> str | None:
    """Return 'Y', 'N', 'EXCLUDED', or None (ambiguous -> review)."""
    t = text.lower()
    if re.search(MOOT_OR_ADMIN, t):
        return "EXCLUDED"
    g, d, p = re.search(GRANT, t), re.search(DENY, t), re.search(PART, t)
    if g and not d:
        return "Y"
    if d and not g:
        return "N"
    if g and d and p:
        # granted in part / denied in part -> YES per frozen rule (movant obtained
        # relief on >=1 claim). Flag for hand-verify pool at elevated priority.
        return "Y"
    return None


def main() -> None:
    paths = sys.argv[1:] or glob.glob("data/raw_*.jsonl")
    labeled, review, stats = [], [], {"in": 0, "kept": 0, "excluded": 0, "review": 0}
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
                # content-hash dedup (cross-listed cases produce same entry, new id)
                chash = (rec.get("_judge"), rec.get("entry_date_filed"),
                         re.sub(r"\s+", " ", desc)[:200])
                if chash in seen:
                    continue
                seen.add(chash)
                if re.match(PARTY_FILING, desc, re.I):
                    continue
                if not signature_ok(desc, rec.get("_judge", "")):
                    continue
                mtype = classify_motion(desc)
                if not mtype:
                    continue
                outcome = label_outcome(desc)
                row = {
                    "id": doc_id,
                    "judge": rec.get("_judge"),
                    "date": rec.get("entry_date_filed"),
                    "docket": rec.get("docketNumber") or rec.get("docket_id"),
                    "case": rec.get("caseName"),
                    "motion_type": mtype,
                    "description": desc,
                    "label": outcome,
                }
                if outcome in ("Y", "N"):
                    labeled.append(row)
                    stats["kept"] += 1
                elif outcome == "EXCLUDED":
                    stats["excluded"] += 1
                else:
                    review.append(row)
                    stats["review"] += 1
    with open("data/labeled.jsonl", "w", encoding="utf-8") as f:
        f.writelines(json.dumps(r) + "\n" for r in labeled)
    with open("data/needs_review.jsonl", "w", encoding="utf-8") as f:
        f.writelines(json.dumps(r) + "\n" for r in review)
    print(json.dumps(stats), file=sys.stderr)


if __name__ == "__main__":
    main()
