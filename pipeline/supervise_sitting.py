#!/usr/bin/env python3
"""Operational supervisor for one model's sitting: re-launch arms2.py (which
resumes from its incremental per-(model,arm,item) cache) until it exits 0.

This is NOT a scored artifact and touches NO freeze-hashed file — arms2.py,
personas, exam, and all manifest files are byte-identical across restarts. It
only defends the single sitting against transient network timeouts (the frozen
arms.py has no retry). Every (model,arm,item) is scored exactly once and cached;
a restart re-scores nothing. One sitting, completed across restarts.

Usage: cd gatekeeper && MODEL_FILTER=gpt nohup python3 -u pipeline/supervise_sitting.py >> data/sit_gpt.log 2>&1 &
"""
from __future__ import annotations
import os
import subprocess
import sys
import time

MF = os.environ.get("MODEL_FILTER", "")
MAX_ATTEMPTS = 60


def log(m: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] SUPERVISOR({MF}) {m}", flush=True)


def main() -> None:
    if MF not in ("gpt", "fable"):
        sys.exit("set MODEL_FILTER=gpt|fable")
    for attempt in range(1, MAX_ATTEMPTS + 1):
        log(f"attempt {attempt}: launching arms2.py")
        rc = subprocess.run([sys.executable, "-u", "pipeline/arms2.py"],
                            env=dict(os.environ, MODEL_FILTER=MF)).returncode
        if rc == 0:
            log(f"COMPLETE after {attempt} attempt(s)")
            return
        log(f"arms2 exited rc={rc} (likely transient timeout); resuming from cache in 15s")
        time.sleep(15)
    log(f"GAVE UP after {MAX_ATTEMPTS} attempts")
    sys.exit(1)


if __name__ == "__main__":
    main()
