#!/usr/bin/env python3
"""Resume step after an OpenAI top-up: build the 2 court-pool personas (L2) and
rebuild the 7 stale judge personas on final grounding. Refuses if OpenAI has no
credit (probes first) or if a persona_loop is already running.

Pool personas use MAX_VAL=60 (prereg C4). Serial — one OpenAI consumer.

Usage: cd gatekeeper && python3 -u pipeline/finish_personas.py
"""
from __future__ import annotations
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

STALE = ["cogan", "donnelly", "engelmayer", "koeltl", "morrison", "rochon", "stein"]
GROUNDING = "data/grounding2.jsonl"
POOL_MAX_VAL = "60"


def log(m: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def credit_ok() -> bool:
    key = open("openai_key.txt").read().strip()
    body = {"model": "gpt-5.4-2026-03-05",
            "messages": [{"role": "user", "content": "Y"}],
            "max_completion_tokens": 16, "reasoning_effort": "none"}
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {key}", "content-type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=60).read()
        return True
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")
        if "insufficient_quota" in detail:
            log("OpenAI still OUT OF CREDITS (insufficient_quota) — top up first.")
            return False
        log(f"probe HTTP {e.code}: {detail[:200]} — treating as not-ready")
        return False


def build(judge_key: str, rows: list[str], env: dict) -> bool:
    sub = f"data/grounding2_build_{judge_key}.jsonl"
    with open(sub, "w", encoding="utf-8") as f:
        f.writelines(rows)
    e = dict(os.environ, GROUNDING_PATH=sub, PERSONA_OUT_SUFFIX="2", **env)
    rc = subprocess.run("python3 -u pipeline/persona_loop.py >> data/persona2.log 2>&1",
                        shell=True, env=e, timeout=3600).returncode
    os.remove(sub)
    return rc == 0


def main() -> None:
    if subprocess.run("pgrep -f pipeline/persona_loop.py", shell=True,
                      capture_output=True).returncode == 0:
        sys.exit("REFUSING: a persona_loop is already running.")
    if not credit_ok():
        sys.exit(1)

    rows_by_judge: dict = {}
    courts = {r["judge"]: ("EDNY" if r["court"] == "nyed" else "SDNY")
              for r in json.load(open("data/judges2.json"))["selected"]}
    pool_rows: dict = {"SDNY": [], "EDNY": []}
    for line in open(GROUNDING, encoding="utf-8"):
        r = json.loads(line)
        rows_by_judge.setdefault(r["judge"].lower(), []).append(line)
        c = courts.get(r["judge"])
        if c:
            pr = dict(r)
            pr["judge"] = f"{c}_POOL"
            pool_rows[c].append(json.dumps(pr) + "\n")

    # L2 pooled personas (capped validation)
    for court in ("SDNY", "EDNY"):
        out = f"data/persona2_{court.lower()}_pool.md"
        if os.path.exists(out):
            log(f"{out} exists — skip")
            continue
        log(f"{court} pool: {len(pool_rows[court])} rows (MAX_VAL={POOL_MAX_VAL})")
        ok = build(court.lower() + "_pool", pool_rows[court], {"MAX_VAL": POOL_MAX_VAL})
        log(f"  {out} exists: {os.path.exists(out)} (rc ok={ok})")

    # rebuild 7 stale judge personas on final grounding (C3)
    for j in STALE:
        rows = rows_by_judge.get(j, [])
        if len(rows) < 12:
            log(f"{j}: {len(rows)} rows (<12) — leaving as-is")
            continue
        bak = f"data/persona2_{j}_prefilter.bak"
        if os.path.exists(f"data/persona2_{j}.md") and not os.path.exists(bak):
            os.replace(f"data/persona2_{j}.md", bak)
        log(f"{j}: rebuild on {len(rows)} rows")
        ok = build(j, rows, {})
        if not ok and os.path.exists(bak) and not os.path.exists(f"data/persona2_{j}.md"):
            os.replace(bak, f"data/persona2_{j}.md")
            log(f"  {j} failed — restored backup")

    import glob
    judge_p = [p for p in glob.glob("data/persona2_*.md")
               if not any(x in p for x in ("_pool", "fictional", "prefilter"))]
    pool_p = glob.glob("data/persona2_*_pool.md")
    log(f"judge personas: {len(judge_p)}/15  pool personas: {len(pool_p)}/2")
    log("=== finish_personas done — READY FOR: ensemble gate, leakage audit, FREEZE-2 ==="
        if len(judge_p) >= 15 and len(pool_p) >= 2 else
        "=== INCOMPLETE — inspect log ===")


if __name__ == "__main__":
    main()
