#!/usr/bin/env python3
"""Lab lever #1: fetch full opinion texts for the grounding corpus.

Dev track only — enriches PRE-cutoff grounding (persona training + retrieval).
Exam items are NOT touched here; a future sealed run may fetch its own inputs
under its own pre-registration.

For each grounding item, pull the RECAP document's plain_text where the archive
has it (free PDFs that were OCR'd). Coverage will be partial; that's fine —
partial full-texts beat zero.

Usage: python3 pipeline/fetch_opinions.py
Output: data/opinion_texts.jsonl  {"id":..., "judge":..., "chars":N, "text":...}
"""
from __future__ import annotations
import json
import os
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ingest import _headers  # token-aware headers

BASE = "https://www.courtlistener.com/api/rest/v4/recap-documents/"
RATE_SECONDS = int(os.environ.get("FETCH_RATE_SECONDS", "12"))
MAX_CHARS = 40000  # cap per opinion; persona digests don't need more


def fetch_text(doc_id) -> str | None:
    url = f"{BASE}{doc_id}/?fields=plain_text,is_available"
    req = urllib.request.Request(url, headers=_headers())
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.load(r)
        text = (data.get("plain_text") or "").strip()
        return text[:MAX_CHARS] if len(text) > 200 else None
    except Exception as e:  # noqa: BLE001
        print(f"  {doc_id}: {str(e)[:80]}", file=sys.stderr)
        return None


def main() -> None:
    grounding = [json.loads(l) for l in open("data/grounding.jsonl", encoding="utf-8")]
    done = set()
    out_path = "data/opinion_texts.jsonl"
    if os.path.exists(out_path):
        done = {json.loads(l)["id"] for l in open(out_path, encoding="utf-8")}
    todo = [g for g in grounding if g["id"] not in done]
    print(f"grounding items: {len(grounding)} | already fetched: {len(done)} | todo: {len(todo)}")
    hits = 0
    with open(out_path, "a", encoding="utf-8") as out:
        for i, g in enumerate(todo):
            text = fetch_text(g["id"])
            if text:
                out.write(json.dumps({"id": g["id"], "judge": g["judge"],
                                      "motion_type": g["motion_type"],
                                      "date": g.get("date"), "label": g["label"],
                                      "chars": len(text), "text": text}) + "\n")
                out.flush()
                hits += 1
            if i % 20 == 0:
                print(f"{i}/{len(todo)} fetched, {hits} with text")
            time.sleep(RATE_SECONDS)
    print(f"done: {hits}/{len(todo)} grounding items have full text")


if __name__ == "__main__":
    main()
