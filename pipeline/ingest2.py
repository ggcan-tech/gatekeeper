#!/usr/bin/env python3
"""Exam #2A corpus pull v2 — QUOTA-AWARE.

CourtListener search API allows 1,200 requests/day on our token (measured
2026-07-18: '429 ... Rate limit exceeded: 1200/day' with Retry-After). v1
burned retries against a closed quota and its give-up logic skipped judges.
v2 fixes both:

- On 429 it reads Retry-After and sleeps EXACTLY until the window reopens
  (plus jitter), then resumes the same page. It never gives up on quota.
- Tasks are prioritized: post-cutoff (exam-critical, labels can start as
  soon as a judge completes) before pre-cutoff grounding (persona fuel),
  smallest judges first so the most judges complete earliest.
- Each (judge, desc, window) writes its own file: raw2_{judge}_{desc}_{win}.jsonl
  Legacy full-window files from v1 (stein, rochon-order) satisfy both windows.

Usage: python3 pipeline/ingest2.py            (resumable; skips complete tasks)
"""
from __future__ import annotations
import json
import os
import random
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ingest import _headers

BASE = "https://www.courtlistener.com/api/rest/v4/search/"
CUTOFF = "2025-08-31"          # gpt-5.4 cutoff — exam/grounding boundary
WINDOW_START = "2023-07-14"    # same 3-year window as exam #1
RATE = float(os.environ.get("INGEST_RATE_SECONDS", "8"))


def build_url(judge: str, court: str, desc: str, after: str,
              before: str | None, cursor: str | None) -> str:
    p = {"type": "rd", "q": "", "court": court, "assigned_to": judge,
         "description": desc, "entry_date_filed_after": after,
         "order_by": "entry_date_filed desc"}
    if before:
        p["entry_date_filed_before"] = before
    if cursor:
        p["cursor"] = cursor
    return BASE + "?" + urllib.parse.urlencode(p)


def fetch_patient(url: str) -> dict | None:
    """Fetch with quota-awareness: 429 -> sleep Retry-After, never give up.
    Returns None only after repeated NON-quota failures."""
    soft_fails = 0
    while True:
        try:
            req = urllib.request.Request(url, headers=_headers())
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                ra = int(e.headers.get("Retry-After") or 1800)
                # re-probe hourly at most: probes appear to count against the
                # window on this API, and at a 250/day fallback tier they are
                # no longer free
                nap = min(ra, 3600)
                wake = time.strftime("%H:%M", time.localtime(time.time() + nap))
                print(f"  quota closed (RA {ra}s) — napping {nap}s (~{wake})",
                      flush=True)
                time.sleep(nap + random.uniform(30, 90))
                continue
            soft_fails += 1
            print(f"  http {e.code} (fail {soft_fails}/8)", flush=True)
        except Exception as ex:  # noqa: BLE001
            soft_fails += 1
            print(f"  {str(ex)[:70]} (fail {soft_fails}/8)", flush=True)
        if soft_fails >= 8:
            return None
        time.sleep(60 * soft_fails)


def pull_task(judge: str, court: str, qname: str, desc: str, win: str) -> int:
    after = CUTOFF if win == "post" else WINDOW_START
    before = None if win == "post" else CUTOFF
    out = f"data/raw2_{judge.lower()}_{desc}_{win}.jsonl"
    done_marker = out + ".done"
    if os.path.exists(done_marker):
        return -1
    n, cursor, page = 0, None, 0
    mode = "a" if os.path.exists(out) else "w"
    # resume: if partial file exists, restart the task clean (cursor unknown);
    # dedupe downstream handles any overlap
    with open(out, mode, encoding="utf-8") as f:
        while True:
            data = fetch_patient(build_url(qname, court, desc, after, before, cursor))
            if data is None:
                print(f"  ABANDON {out} p{page} after soft failures", flush=True)
                return n
            results = data.get("results", [])
            if page == 0 and before and results:
                newest = max((r.get("entry_date_filed") or "") for r in results)
                if newest and newest > before:
                    print(f"  WARNING: before-filter ignored (saw {newest}); "
                          "grounding will contain post-cutoff dups — split "
                          "handles by date", flush=True)
            for rec in results:
                rec["_judge"] = judge
                rec["_win"] = win
                rec["_pulled_query_description"] = desc
                f.write(json.dumps(rec) + "\n")
            n += len(results)
            page += 1
            if page % 10 == 0 or not data.get("next"):
                print(f"  {out}: p{page} total {n} (count~{data.get('count')})",
                      flush=True)
            nxt = data.get("next")
            if not nxt:
                break
            cursor = urllib.parse.parse_qs(
                urllib.parse.urlparse(nxt).query).get("cursor", [None])[0]
            if cursor is None:
                break
            time.sleep(RATE)
    open(done_marker, "w").write(str(n))
    return n


def main() -> None:
    sel = json.load(open("data/judges2.json"))["selected"]
    census = {(j["judge"], j["court"]): j
              for j in json.load(open("data/census.json"))["judges"]}

    def size(rec):
        c = census.get((rec["judge"], rec["court"]), {})
        return c.get("post_gpt_docs", 99999)

    ordered = sorted(sel, key=size)
    tasks = []
    for win in ("post", "ground"):        # exam-critical window first
        for rec in ordered:
            for desc in ("order", "opinion"):
                legacy = f"data/raw2_{rec['judge'].lower()}_{desc}.jsonl"
                if os.path.exists(legacy) and os.path.getsize(legacy) > 0:
                    continue              # v1 full-window file covers both
                tasks.append((rec, desc, win))

    print(f"{len(tasks)} tasks, quota-aware, rate {RATE}s", flush=True)
    for i, (rec, desc, win) in enumerate(tasks):
        j, c = rec["judge"], rec["court"]
        q = rec.get("query_name", j)
        print(f"[{i+1}/{len(tasks)}] {c}:{j} {desc}/{win}", flush=True)
        r = pull_task(j, c, q, desc, win)
        if r >= 0:
            print(f"  -> {r} docs", flush=True)
        time.sleep(RATE)
    print("ALL TASKS COMPLETE", flush=True)


if __name__ == "__main__":
    main()
