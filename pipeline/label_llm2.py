#!/usr/bin/env python3
"""Exam #2 LLM extractor — identical frozen method to exam #1's label_llm.py
(same SYSTEM prompt, same extractor model, same one-character protocol),
pointed at the exam-2 review pool. Writes labeled2.jsonl; never touches
exam-1's freeze-hashed files.

Usage: python3 pipeline/label_llm2.py
"""
from __future__ import annotations
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import arms
from label_llm import SYSTEM, EXTRACT_MODEL


def main() -> None:
    rows = [json.loads(l) for l in open("data/needs_review2.jsonl", encoding="utf-8")]
    done_ids = set()
    if os.path.exists("data/labeled2_llm.done"):
        done_ids = {l.strip() for l in open("data/labeled2_llm.done")}
    todo = [r for r in rows if str(r["id"]) not in done_ids]
    print(f"review pool {len(rows)}, already resolved {len(done_ids)}, todo {len(todo)}",
          file=sys.stderr)
    arms.MODEL_ID = EXTRACT_MODEL
    resolved, unknown = 0, 0
    out_f = open("data/labeled2.jsonl", "a", encoding="utf-8")
    done_f = open("data/labeled2_llm.done", "a", encoding="utf-8")
    for i, r in enumerate(todo):
        user = (f"Motion type (regex guess): {r['motion_type']}\n"
                f"Docket entry: {r['description'][:1200]}\nOne character:")
        out = None
        for attempt in range(6):
            try:
                out = arms._post_chat({
                    "model": EXTRACT_MODEL,
                    "messages": [{"role": "system", "content": SYSTEM},
                                 {"role": "user", "content": user}],
                    "max_completion_tokens": 4,
                    "reasoning_effort": "none",
                })["choices"][0]["message"]["content"].strip().upper()[:1]
                break
            except Exception as e:  # noqa: BLE001
                msg = str(e)
                if "429" in msg and attempt < 5:
                    wait = 30 * (attempt + 1)
                    print(f"429 on {r['id']} — retry in {wait}s", file=sys.stderr)
                    time.sleep(wait)
                    continue
                print(f"error on {r['id']}: {msg[:120]}", file=sys.stderr)
                out = "U"
                break
        if out in ("Y", "N"):
            r["label"] = out
            r["label_source"] = "llm"
            out_f.write(json.dumps(r) + "\n")
            out_f.flush()
            resolved += 1
        else:
            unknown += 1
        done_f.write(f"{r['id']}\n")
        done_f.flush()
        if i % 50 == 0:
            print(f"{i}/{len(todo)} resolved={resolved}", file=sys.stderr)
        time.sleep(0.2)
    print(f"resolved {resolved} / {len(todo)} (excluded/unknown: {unknown})")


if __name__ == "__main__":
    main()
