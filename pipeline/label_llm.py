#!/usr/bin/env python3
"""LLM extractor for the ambiguous-label review pool (frozen labeling method).

Reads data/needs_review.jsonl, classifies each docket description under the
frozen schema, appends resolved rows to data/labeled.jsonl with source=llm.
Not the exam model's job — any strong extractor is allowed by the protocol;
we use a cheap sibling of the pinned model.

Usage: python3 pipeline/label_llm.py
"""
from __future__ import annotations
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import arms  # reuse _post_chat / key handling

EXTRACT_MODEL = os.environ.get("LABEL_MODEL_ID", "gpt-5.4-mini")

SYSTEM = """You classify the OUTCOME of a contested motion from a US federal
docket entry description, under this frozen schema:
- Y  = relief substantially granted (incl. granted-in-part where the movant
       obtained dismissal/judgment/compulsion on >=1 claim of the primary motion)
- N  = denied
- X  = excluded (denied as moot, administrative termination, referral to
       magistrate, or the entry is not actually a ruling on a contested
       substantive motion)
- U  = cannot tell from this text
Answer with exactly one character: Y, N, X, or U."""


def main() -> None:
    rows = [json.loads(l) for l in open("data/needs_review.jsonl", encoding="utf-8")]
    resolved, unknown = [], 0
    arms.MODEL_ID = EXTRACT_MODEL
    for i, r in enumerate(rows):
        user = (f"Motion type (regex guess): {r['motion_type']}\n"
                f"Docket entry: {r['description'][:1200]}\nOne character:")
        try:
            out = arms._post_chat({
                "model": EXTRACT_MODEL,
                "messages": [{"role": "system", "content": SYSTEM},
                             {"role": "user", "content": user}],
                "max_completion_tokens": 4,
                "reasoning_effort": "none",
            })["choices"][0]["message"]["content"].strip().upper()[:1]
        except Exception as e:  # noqa: BLE001
            print(f"error on {r['id']}: {str(e)[:120]}", file=sys.stderr)
            out = "U"
        if out in ("Y", "N"):
            r["label"] = out
            r["label_source"] = "llm"
            resolved.append(r)
        else:
            unknown += 1
        if i % 20 == 0:
            print(f"{i}/{len(rows)}", file=sys.stderr)
        time.sleep(0.2)
    with open("data/labeled.jsonl", "a", encoding="utf-8") as f:
        f.writelines(json.dumps(r) + "\n" for r in resolved)
    print(f"resolved {len(resolved)} / {len(rows)} (excluded/unknown: {unknown})")


if __name__ == "__main__":
    main()
