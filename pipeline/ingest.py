#!/usr/bin/env python3
"""Pull RECAP docket documents for the target judges from CourtListener.

Usage:
  python3 pipeline/ingest.py --smoke          # 1 request/judge, verify API shape
  python3 pipeline/ingest.py                  # full pull (rate-limited)

Auth: export COURTLISTENER_TOKEN=...  (Tier-2 membership recommended;
unauthenticated works at ~5 req/min for smoke tests).
Output: data/raw_{judge}.jsonl — one docket-document record per line.
"""
from __future__ import annotations
import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request

BASE = "https://www.courtlistener.com/api/rest/v4/search/"
WINDOW_START = "2023-07-14"
JUDGES = [("Liman", "nysd"), ("Furman", "nysd"), ("Subramanian", "nysd")]
RATE_SECONDS = int(os.environ.get("INGEST_RATE_SECONDS", "16"))  # ~4/min default; raise when unauthenticated


def fetch(url: str) -> dict:
    req = urllib.request.Request(url, headers=_headers())
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def _get_token() -> str | None:
    token = os.environ.get("COURTLISTENER_TOKEN")
    if token:
        return token
    here = os.path.dirname(os.path.abspath(__file__))
    for p in (os.path.join(here, "..", "token.txt"), "token.txt"):
        try:
            with open(p, encoding="utf-8") as f:
                t = f.read().strip()
            if t and "PASTE" not in t.upper():
                return t
        except OSError:
            continue
    return None


def _headers() -> dict:
    h = {"User-Agent": "gatekeeper-experiment/0.1 (research; contact in repo)"}
    token = _get_token()
    if token:
        h["Authorization"] = f"Token {token}"
    return h


def build_url(judge: str, court: str, cursor: str | None = None, description: str = "opinion") -> str:
    params = {
        "type": "rd",                      # RECAP documents
        "q": "",
        "court": court,
        "assigned_to": judge,
        "description": description,
        "entry_date_filed_after": WINDOW_START,
        "order_by": "entry_date_filed desc",
    }
    if cursor:
        params["cursor"] = cursor
    return BASE + "?" + urllib.parse.urlencode(params)


def pull_judge(judge: str, court: str, out_path: str, smoke: bool = False,
               description: str = "opinion", stop_before: str | None = None) -> int:
    n, cursor, page = 0, None, 0
    with open(out_path, "a", encoding="utf-8") as out:
        while True:
            url = build_url(judge, court, cursor, description)
            data = None
            for attempt in range(5):
                try:
                    data = fetch(url)
                    break
                except Exception as e:  # noqa: BLE001 - back off on 429/timeouts
                    wait = 90 * (attempt + 1)
                    print(f"[{judge}] fetch error p{page} (try {attempt+1}/5): "
                          f"{e} — backing off {wait}s", file=sys.stderr)
                    time.sleep(wait)
            if data is None:
                print(f"[{judge}] giving up on page {page} after 5 tries", file=sys.stderr)
                break
            results = data.get("results", [])
            for rec in results:
                rec["_judge"] = judge
                rec["_pulled_query_description"] = description
                out.write(json.dumps(rec) + "\n")
            n += len(results)
            page += 1
            print(f"[{judge}] page {page}: +{len(results)} (total {n}, "
                  f"count~{data.get('count')})")
            if stop_before and results:
                oldest = min((r.get("entry_date_filed") or "9999") for r in results)
                if oldest < stop_before:
                    print(f"[{judge}] reached {oldest} < stop-before {stop_before}; stopping")
                    break
            nxt = data.get("next")
            if smoke or not nxt:
                break
            cursor = urllib.parse.parse_qs(urllib.parse.urlparse(nxt).query).get(
                "cursor", [None])[0]
            if cursor is None:
                break
            time.sleep(RATE_SECONDS)
    return n


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true", help="one request per judge")
    ap.add_argument("--description", default="opinion",
                    help='docket-entry description filter (also run with "order" for label volume)')
    ap.add_argument("--judge", default=None, help="pull only this judge (e.g. Furman)")
    ap.add_argument("--stop-before", default=None,
                    help="stop paging once entries are older than this date (YYYY-MM-DD)")
    args = ap.parse_args()
    os.makedirs("data", exist_ok=True)
    total = 0
    judges = [(j, c) for j, c in JUDGES if not args.judge or j == args.judge]
    for judge, court in judges:
        out_path = f"data/raw_{judge.lower()}_{args.description}.jsonl"
        total += pull_judge(judge, court, out_path, smoke=args.smoke,
                            description=args.description, stop_before=args.stop_before)
        if not args.smoke:
            time.sleep(RATE_SECONDS)
    print(f"done: {total} records")


if __name__ == "__main__":
    main()
