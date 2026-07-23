#!/usr/bin/env python3
"""Night driver: pull-complete -> labels -> grounding2 -> personas -> pooled personas.

Stops BEFORE the ensemble gate / leakage audit / FREEZE-2 / sitting: those need a
human decision (amendment log + hash publication), which is the point of freeze.

Sequencing rule honored: only ONE OpenAI consumer at a time (labeling, then each
persona loop, strictly serial). Deadline fallback: if the CourtListener pull has
not reached 54/54 by DEADLINE, proceed with whatever grounding exists — judges
with no persona file are scored L0-L3 and land in the pre-registered
thin/zero-grounding stratum (arms2.py decides L4 eligibility mechanically).

Usage: cd gatekeeper && nohup python3 -u pipeline/night2.py >> data/night2.log 2>&1 &
"""
from __future__ import annotations
import glob
import json
import os
import re
import subprocess
import sys
import time

DEADLINE = os.environ.get("NIGHT_DEADLINE", "06:00")   # local clock, Thursday
CUTOFF = "2025-08-31"
POLL_S = 300


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def pull_done() -> int:
    return len(glob.glob("data/raw2_*.done"))


def past_deadline() -> bool:
    hh, mm = (int(x) for x in DEADLINE.split(":"))
    now = time.localtime()
    return (now.tm_hour, now.tm_min) >= (hh, mm) and now.tm_hour < 12


def wait_for_pull() -> None:
    while True:
        n = pull_done()
        if n >= 54:
            log(f"pull COMPLETE {n}/54")
            return
        if past_deadline():
            log(f"DEADLINE {DEADLINE} reached at {n}/54 — proceeding with available "
                "grounding (ungrounded judges -> pre-registered zero-grounding stratum)")
            return
        alive = subprocess.run("pgrep -f pipeline/ingest2.py", shell=True,
                               capture_output=True).returncode == 0
        if not alive:
            log(f"ingest2 NOT RUNNING at {n}/54 — proceeding with what exists")
            return
        log(f"pull {n}/54 — waiting")
        time.sleep(POLL_S)


def run(cmd: str, timeout: int | None = None) -> int:
    log(f"$ {cmd}")
    try:
        r = subprocess.run(cmd, shell=True, timeout=timeout)
        log(f"  -> exit {r.returncode}")
        return r.returncode
    except subprocess.TimeoutExpired:
        log("  -> TIMEOUT (continuing)")
        return -1


SIG = re.compile(r"(?:Signed by|Ordered by)\s+(?:Chief\s+)?(?:District\s+)?Judge\s+"
                 r"([A-Z][\w.'\-]*(?:\s+[A-Z][\w.'\-]*)*)")


def attribution_ok(row: dict) -> bool:
    """Drop grounding rows whose signature block names a DIFFERENT judge (MDL
    cross-listing noise; measured at ~10% for Cogan). Exam set is untouched."""
    m = SIG.findall(row.get("description", "") or "")
    if not m:
        return True
    signer = m[-1].split()[-1].lower().rstrip(".,")
    j = row["judge"].lower()
    return not signer or j in signer or signer in j


def build_grounding() -> dict:
    """grounding2 = pre-cutoff rows from the fresh labeling UNION the certified
    backup's pre-cutoff rows (preserves LLM-resolved rows earlier personas saw),
    minus attribution-mismatched rows. Monotonic: nothing already used is lost."""
    rows: dict = {}
    for path in ("data/labeled2_certified_backup.jsonl", "data/labeled2.jsonl"):
        if not os.path.exists(path):
            continue
        for line in open(path, encoding="utf-8"):
            r = json.loads(line)
            if (r.get("date") or "") <= CUTOFF:
                rows[r["id"]] = r
    kept = [r for r in rows.values() if attribution_ok(r)]
    dropped = len(rows) - len(kept)
    kept.sort(key=lambda r: (r["judge"], r.get("date") or ""))
    with open("data/grounding2.jsonl", "w", encoding="utf-8") as f:
        for r in kept:
            f.write(json.dumps(r) + "\n")
    per: dict = {}
    for r in kept:
        per[r["judge"]] = per.get(r["judge"], 0) + 1
    log(f"grounding2.jsonl: {len(kept)} rows across {len(per)} judges "
        f"(dropped {dropped} attribution-mismatched)")
    for j, c in sorted(per.items(), key=lambda x: -x[1]):
        log(f"    {j:12s} {c}")
    json.dump(per, open("data/grounding2_counts.json", "w"), indent=1)
    return per


def personas(per: dict) -> None:
    """One judge at a time (serial OpenAI). Skip judges that already have a persona
    and judges with too little fuel for the loop's own validation slice."""
    todo = [j for j, c in sorted(per.items(), key=lambda x: -x[1])
            if c >= 12 and not os.path.exists(f"data/persona2_{j.lower()}.md")]
    log(f"personas to build: {todo or 'none'}")
    for j in todo:
        sub = f"data/grounding2_only_{j.lower()}.jsonl"
        with open(sub, "w", encoding="utf-8") as out:
            for line in open("data/grounding2.jsonl", encoding="utf-8"):
                if json.loads(line)["judge"] == j:
                    out.write(line)
        run(f"GROUNDING_PATH={sub} PERSONA_OUT_SUFFIX=2 python3 -u "
            f"pipeline/persona_loop.py >> data/persona2.log 2>&1", timeout=3600)
        os.remove(sub)
        log(f"  persona2_{j.lower()}.md exists: "
            f"{os.path.exists(f'data/persona2_{j.lower()}.md')}")


def pooled() -> None:
    """L2 court-pooled personas via the judge-field hack (HANDOFF §1.2)."""
    courts = {r["judge"]: ("EDNY" if r["court"] == "nyed" else "SDNY")
              for r in json.load(open("data/judges2.json"))["selected"]}
    for court in ("SDNY", "EDNY"):
        name = f"{court}_POOL"
        out_path = f"data/persona2_{name.lower()}.md"
        if os.path.exists(out_path):
            log(f"{out_path} exists — skip")
            continue
        sub = f"data/grounding2_pool_{court.lower()}.jsonl"
        n = 0
        with open(sub, "w", encoding="utf-8") as out:
            for line in open("data/grounding2.jsonl", encoding="utf-8"):
                r = json.loads(line)
                if courts.get(r["judge"]) == court:
                    r["judge"] = name
                    out.write(json.dumps(r) + "\n")
                    n += 1
        log(f"{court} pool: {n} rows")
        if n < 12:
            log(f"  too thin — skipping {court} pool persona")
            os.remove(sub)
            continue
        run(f"GROUNDING_PATH={sub} PERSONA_OUT_SUFFIX=2 python3 -u "
            f"pipeline/persona_loop.py >> data/persona2.log 2>&1", timeout=5400)
        os.remove(sub)
        log(f"  {out_path} exists: {os.path.exists(out_path)}")


def main() -> None:
    log("=== night2 start ===")
    before = os.path.exists("data/exam2.jsonl") and \
        subprocess.run("shasum -a 256 data/exam2.jsonl", shell=True,
                       capture_output=True, text=True).stdout.split()[0]
    log(f"exam2 hash at start: {before}")

    wait_for_pull()
    run("python3 -u pipeline/label2.py > data/label2_night.log 2>&1", timeout=1800)
    # LLM extractor pass (frozen method) — restores/extends LLM-resolved labels.
    run("python3 -u pipeline/label_llm2.py >> data/label_llm2_night.log 2>&1", timeout=7200)

    per = build_grounding()
    personas(per)
    pooled()

    after = subprocess.run("shasum -a 256 data/exam2.jsonl", shell=True,
                           capture_output=True, text=True).stdout.split()[0]
    log(f"exam2 hash at end:   {after}")
    log("EXAM2 UNCHANGED ✓" if before == after else "!!! EXAM2 CHANGED — INVESTIGATE !!!")
    built = sorted(os.path.basename(p) for p in glob.glob("data/persona2_*.md"))
    log(f"personas on disk ({len(built)}): {built}")
    log("=== night2 done — READY FOR: ensemble gate, leakage audit, FREEZE-2, sitting ===")


if __name__ == "__main__":
    main()
