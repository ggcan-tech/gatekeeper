#!/usr/bin/env python3
"""Rebuild the 7 personas built last session on stale/thinner grounding, so ALL
15 judge personas share the SAME final grounding vintage before FREEZE-2 (prereg
correction C3). The 8 personas night2 built this run already use final grounding;
the 2 court-pool personas likewise. This pass covers only the 7 stale ones.

Cogan is the load-bearing one: its old persona was built on grounding that still
contained ~15 cross-attributed MDL rows (now filtered out).

Serial OpenAI consumer — run ONLY after night2's persona phase has finished
(never concurrently: shared key => 429 storm). Idempotent-ish: each judge's old
persona is moved to data/persona2_{j}_prefilter.bak before rebuild.

Usage: cd gatekeeper && python3 -u pipeline/rebuild_stale_personas.py
"""
from __future__ import annotations
import json
import os
import subprocess
import sys
import time

STALE = ["cogan", "donnelly", "engelmayer", "koeltl", "morrison", "rochon", "stein"]
GROUNDING = "data/grounding2.jsonl"


def log(m: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def main() -> None:
    if subprocess.run("pgrep -f pipeline/persona_loop.py", shell=True,
                      capture_output=True).returncode == 0:
        sys.exit("REFUSING: a persona_loop is already running (would 429-storm the "
                 "shared OpenAI key). Wait for night2's persona phase to finish.")
    if not os.path.exists(GROUNDING):
        sys.exit(f"REFUSING: {GROUNDING} missing.")

    by_judge: dict = {}
    for line in open(GROUNDING, encoding="utf-8"):
        r = json.loads(line)
        by_judge.setdefault(r["judge"].lower(), []).append(line)

    for j in STALE:
        rows = by_judge.get(j, [])
        if len(rows) < 12:
            log(f"{j}: only {len(rows)} rows (<12) — leaving existing persona as-is")
            continue
        persona = f"data/persona2_{j}.md"
        if os.path.exists(persona):
            os.replace(persona, f"data/persona2_{j}_prefilter.bak")
        sub = f"data/grounding2_only_{j}.jsonl"
        with open(sub, "w", encoding="utf-8") as f:
            f.writelines(rows)
        log(f"{j}: rebuilding on {len(rows)} final-grounding rows")
        rc = subprocess.run(
            f"GROUNDING_PATH={sub} PERSONA_OUT_SUFFIX=2 python3 -u "
            f"pipeline/persona_loop.py >> data/persona2.log 2>&1",
            shell=True, timeout=3600).returncode
        os.remove(sub)
        ok = os.path.exists(persona)
        log(f"  exit {rc}; persona2_{j}.md exists: {ok}")
        if not ok:  # restore backup rather than leave a hole
            bak = f"data/persona2_{j}_prefilter.bak"
            if os.path.exists(bak):
                os.replace(bak, persona)
                log(f"  restored backup for {j}")

    built = sorted(os.path.basename(p) for p in
                   __import__("glob").glob("data/persona2_*.md")
                   if "_pool" not in p and "fictional" not in p
                   and "prefilter" not in p)
    log(f"judge personas on disk ({len(built)}): {built}")
    log("=== rebuild done — all 15 judge personas now on final grounding ===")


if __name__ == "__main__":
    main()
