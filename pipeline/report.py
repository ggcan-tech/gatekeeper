#!/usr/bin/env python3
"""Bench Report generator v0 (SYSTEM.md component 5 — see specs/report-prd.md).

Distills an Arena engagement (data/arena_runs/<slug>/summary.json + run_{i}.json,
produced by pipeline/arena.py) into a customer-facing Bench Report: an attack map
(what kills this draft), a survival table (which arguments held), a labeled
outcome picture, and a "what we'd fix before filing" list.

Guardrails enforced in code, not policy:
  G1 — the outcome distribution carries the verbatim tier-3 label
       "[SIMULATED] — Arena output; no accuracy claim"; nothing else claims accuracy.
  G3 — below 20 runs the outcome picture flags "insufficient runs for a stable picture".
  G5 — every report opens with the "preparation intelligence, not legal advice" line.
Every model-written sentence cites the run(s) it draws from like [run 3, 7]; no
percentages or accuracy language appear anywhere but the labeled distribution.

Model access is via pipeline/arms.py seams only (call_model_long). Concierge
posture: the founder reviews every report before delivery.

Usage:
  python3 pipeline/report.py data/arena_runs/<slug> --out data/reports/<slug>.md
  python3 pipeline/report.py --selftest      # offline logic checks, no network
Output: <out>.md (markdown) + the sibling <out>.json (machine-readable, same content).
"""
from __future__ import annotations
import argparse
import datetime
import json
import os
import re
import sys
from typing import Callable, Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import arms  # frozen model access (call_model_long); the only network seam here

REPORTS_ROOT = "data/reports"
INPUT_CHAR_CAP = 1500   # trims each transcript excerpt fed to the model (cost cap, G-cheap)
MIN_STABLE_RUNS = 20    # G3 spirit: below this the outcome picture is flagged unstable
SIMULATED_LABEL = "[SIMULATED] — Arena output; no accuracy claim"   # G1 verbatim
DISCLAIMER = "Preparation intelligence, not legal advice."          # G5 verbatim phrase

# A "writer" produces the free-text sentences; defaults to the frozen model seam
# but is injectable so the offline selftest exercises the assembly logic sans cost.
Writer = Callable[[str, str], str]


# ---------------------------------------------------------------------------
# Pure helpers (no network) — exercised by --selftest.
# ---------------------------------------------------------------------------
def slug_of(runs_dir: str) -> str:
    return os.path.basename(os.path.normpath(runs_dir)) or "motion"


def _trim(text: str, cap: int = INPUT_CHAR_CAP) -> str:
    text = (text or "").strip()
    return text if len(text) <= cap else text[:cap].rstrip() + " …"


def format_citation(runs: List[int]) -> str:
    """Render run numbers as the required '[run 3, 7]' citation (deduped, sorted)."""
    nums = sorted({int(n) for n in runs})
    if not nums:
        return ""
    return "[run " + ", ".join(str(n) for n in nums) + "]"


def _sanitize(text: str) -> str:
    """Coerce model output to one clean sentence with NO percentages, bracketed
    citations, or bullet markers — citations are appended deterministically so the
    format is guaranteed and the run numbers are drawn from the data, not invented."""
    t = (text or "").strip()
    t = re.sub(r"\[[^\]]*\]", " ", t)          # drop any model-authored bracket citations
    t = re.sub(r"\bRUNS?\s*:\s*[\d,\s]+", " ", t, flags=re.I)  # drop leaked RUNS: tags
    t = re.sub(r"\d+(?:\.\d+)?\s*%", " ", t)   # G1: no percentages outside the distribution
    t = t.lstrip("-*• \t").strip()
    t = re.sub(r"\s+", " ", t)
    # Keep the first sentence only (PRD: "one ... sentence"). Split on . ! ? then a capital.
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z(“])", t)
    t = parts[0].strip() if parts and parts[0].strip() else t
    # Add a terminal period only if the sentence doesn't already end in sentence
    # punctuation (optionally wrapped by a closing quote/paren) — avoids `…”.`.
    if t and not re.search(r"[.!?][\"'’”)\]]*$", t):
        t += "."
    return t


def _sentence_with_citation(text: str, runs: List[int]) -> str:
    """One clean sentence followed by its run citation, e.g. '… dismissed. [run 1, 3]'.
    _sanitize guarantees a terminal-punctuation ending, so the citation just trails it."""
    body = _sanitize(text)
    cite = format_citation(runs)
    if not cite:
        return body
    return f"{body} {cite}" if body else cite


def load_engagement(runs_dir: str) -> Tuple[dict, List[dict]]:
    """Load summary.json + all run_{i}.json, runs sorted by run number (PRD step 1)."""
    summary_path = os.path.join(runs_dir, "summary.json")
    if not os.path.isfile(summary_path):
        sys.exit(f"REFUSING TO RUN: {summary_path} missing — is this an Arena runs dir?")
    with open(summary_path, encoding="utf-8") as f:
        summary = json.load(f)
    runs: List[dict] = []
    for name in os.listdir(runs_dir):
        m = re.fullmatch(r"run_(\d+)\.json", name)
        if not m:
            continue
        with open(os.path.join(runs_dir, name), encoding="utf-8") as f:
            runs.append(json.load(f))
    runs.sort(key=lambda r: int(r.get("run", 0)))
    if not runs:
        sys.exit(f"REFUSING TO RUN: no run_*.json files in {runs_dir}.")
    return summary, runs


def index_runs(runs: List[dict]) -> Dict[str, Dict[str, List[int]]]:
    """Map each label to the run numbers where it appeared, so citations are
    derived from the transcripts rather than asked of (and possibly hallucinated by)
    the model. Keys: 'attack' (attack_label), 'arg' (advocate_args), 'decisive'."""
    idx: Dict[str, Dict[str, List[int]]] = {"attack": {}, "arg": {}, "decisive": {}}
    for r in runs:
        n = int(r.get("run", 0))
        atk = r.get("attack_label") or ""
        if atk:
            idx["attack"].setdefault(atk, []).append(n)
        for a in r.get("advocate_args", []) or []:
            idx["arg"].setdefault(a, []).append(n)
        dec = r.get("decisive_arg") or ""
        if dec:
            idx["decisive"].setdefault(dec, []).append(n)
    return idx


def parse_fix_bullets(raw: str, valid_runs: List[int]) -> List[Dict[str, object]]:
    """Parse model fix bullets of the form '- <sentence> RUNS: 1,3'. Each bullet's
    citation is validated against the real run set; unknown/blank -> cite all runs."""
    valid = set(valid_runs)
    fixes: List[Dict[str, object]] = []
    for line in raw.splitlines():
        line = line.strip()
        if not re.match(r"^[-*•]\s+|^\d+[.)]\s+", line):
            continue
        m = re.search(r"\bRUNS?\s*:\s*([\d,\s]+)", line, flags=re.I)
        cited = [int(x) for x in re.findall(r"\d+", m.group(1))] if m else []
        cited = [n for n in cited if n in valid]
        if not cited:
            cited = list(valid_runs)
        sentence = _sanitize(line)
        if sentence and sentence != ".":
            fixes.append({"text": sentence, "runs": sorted(set(cited))})
    return fixes[:5]


# ---------------------------------------------------------------------------
# Model-written prose (network) — grounded strictly in the transcripts.
# ---------------------------------------------------------------------------
_ATTACK_SYS = (
    "You explain, in exactly one plain sentence, what a line of legal attack "
    "exploits in the movant's motion. Ground every word in the quoted attack "
    "text; introduce no new claims. Do not use numbers, percentages, citations, "
    "or any accuracy/probability/likelihood language."
)
_FIX_ARG_SYS = (
    "You suggest, in exactly one plain sentence, how the movant could strengthen "
    "an argument that failed to hold at a moot. Ground it in the bench's reaction; "
    "invent no facts. Do not use numbers, percentages, citations, or any "
    "accuracy/probability/likelihood language."
)
_FIXLIST_SYS = (
    "You prepare a 'what we'd fix before filing' list from a moot-court simulation. "
    "Synthesize the bench's recurring pressure points into 3 to 5 concrete fixes. "
    "Invent no facts; use no percentages and no accuracy/probability language. "
    "Output only bullet lines, one fix per line, each formatted exactly as:\n"
    "- <one sentence fix> RUNS: <comma-separated run numbers this fix draws from>"
)


def attack_sentence(label: str, runs_for: List[int], run_by_num: Dict[int, dict],
                    write: Writer) -> str:
    excerpts = "\n\n".join(
        f"[run {n}] {_trim(run_by_num[n]['transcript'].get('opponent_attack', ''))}"
        for n in runs_for if n in run_by_num)
    user = (f"Attack label: {label}\n\nAttack text(s) from the moot:\n{excerpts}\n\n"
            "In one sentence, what does this attack exploit in the movant's motion?")
    return _sentence_with_citation(write(_ATTACK_SYS, user), runs_for)


def weak_arg_fix(label: str, runs_for: List[int], run_by_num: Dict[int, dict],
                 write: Writer) -> str:
    excerpts = "\n\n".join(
        f"[run {n}] {_trim(run_by_num[n]['transcript'].get('bench_pressure_points', ''))}"
        for n in runs_for if n in run_by_num)
    user = (f"Movant argument that did not always hold: {label}\n\n"
            f"Bench reactions where it was tested:\n{excerpts}\n\n"
            "In one sentence, how should the movant strengthen this argument?")
    return _sentence_with_citation(write(_FIX_ARG_SYS, user), runs_for)


def fix_list(runs: List[dict], write: Writer) -> List[Dict[str, object]]:
    pressure = "\n\n".join(
        f"[run {int(r.get('run', 0))}] "
        f"{_trim(r['transcript'].get('bench_pressure_points', ''))}"
        for r in runs)
    user = ("Bench pressure points, by run:\n\n" + pressure +
            "\n\nWrite 3 to 5 fix bullets in the required format.")
    valid = [int(r.get("run", 0)) for r in runs]
    return parse_fix_bullets(write(_FIXLIST_SYS, user), valid)


# ---------------------------------------------------------------------------
# Report assembly.
# ---------------------------------------------------------------------------
def build_report(slug: str, summary: dict, runs: List[dict], write: Writer,
                 date: Optional[str] = None) -> Tuple[str, dict]:
    """Assemble the Bench Report markdown + machine-readable object (PRD steps 2-4)."""
    date = date or datetime.date.today().isoformat()
    idx = index_runs(runs)
    run_by_num = {int(r.get("run", 0)): r for r in runs}
    n_runs = int(summary.get("n_runs", len(runs)))
    judges = sorted({r.get("judge", "") for r in runs if r.get("judge")})
    bench = ", ".join(judges) if judges else "unspecified bench"

    # --- Attack Map: one model sentence per attack, cited to where it appeared. ---
    attack_rows: List[Dict[str, object]] = []
    for label, stats in (summary.get("attack_table") or {}).items():
        runs_for = idx["attack"].get(label, [])
        attack_rows.append({
            "attack": label,
            "appeared": int(stats.get("appeared", 0)),
            "won": int(stats.get("won", 0)),
            "runs": sorted(set(runs_for)),
            "sentence": attack_sentence(label, runs_for, run_by_num, write)
            if runs_for else "",
        })

    # --- Survival Table: all args listed; a fix sentence only for weak ones. ---
    survival_rows: List[Dict[str, object]] = []
    for label, stats in (summary.get("survival_table") or {}).items():
        appeared = int(stats.get("appeared", 0))
        held = int(stats.get("held", 0))
        decisive = int(stats.get("decisive", 0))
        weak = held < appeared
        runs_for = idx["arg"].get(label, [])
        survival_rows.append({
            "argument": label, "appeared": appeared, "held": held,
            "decisive": decisive, "weak": weak, "runs": sorted(set(runs_for)),
            "fix": weak_arg_fix(label, runs_for, run_by_num, write)
            if (weak and runs_for) else "",
        })

    # --- Outcome picture (G1 label verbatim; G3 flag under 20 runs). ---
    dist = summary.get("outcome_distribution") or {}
    unstable = n_runs < MIN_STABLE_RUNS
    outcome = {
        "distribution": dist,
        "label": SIMULATED_LABEL,
        "note": "insufficient runs for a stable picture" if unstable else "",
    }

    # --- What we'd fix before filing (synthesized across pressure points). ---
    fixes = fix_list(runs, write)

    obj = {
        "slug": slug, "bench": bench, "n_runs": n_runs, "date": date,
        "disclaimer": DISCLAIMER, "label": "SIMULATED",
        "attack_map": attack_rows, "survival_table": survival_rows,
        "outcome": outcome, "fixes": fixes,
    }
    md = render_markdown(obj)
    obj["markdown"] = md
    return md, obj


def render_markdown(obj: dict) -> str:
    L: List[str] = []
    L.append(f"# Bench Report — {obj['slug']}")
    L.append("")
    L.append(f"**Bench:** {obj['bench']} · **Runs:** {obj['n_runs']} "
             f"· **Date:** {obj['date']}")
    L.append("")
    L.append(f"_{obj['disclaimer']}_")
    L.append("")

    # Attack Map
    L.append("## Attack Map")
    L.append("")
    L.append("| Attack | Appeared | Won |")
    L.append("| --- | ---: | ---: |")
    for a in obj["attack_map"]:
        L.append(f"| {a['attack']} | {a['appeared']} | {a['won']} |")
    L.append("")
    for a in obj["attack_map"]:
        if a["sentence"]:
            L.append(f"- **{a['attack']}** — {a['sentence']}")
    L.append("")

    # Survival Table
    L.append("## Survival Table")
    L.append("")
    L.append("| Argument | Appeared | Held | Decisive |")
    L.append("| --- | ---: | ---: | ---: |")
    for s in obj["survival_table"]:
        L.append(f"| {s['argument']} | {s['appeared']} | {s['held']} "
                 f"| {s['decisive']} |")
    L.append("")
    weak_fixes = [s for s in obj["survival_table"] if s["weak"] and s["fix"]]
    if weak_fixes:
        L.append("**Weak arguments — suggested fixes:**")
        L.append("")
        for s in weak_fixes:
            L.append(f"- **{s['argument']}** — {s['fix']}")
    else:
        L.append("_Every tracked argument held across the simulated runs._")
    L.append("")

    # Outcome picture
    L.append("## Outcome picture")
    L.append("")
    dist = obj["outcome"]["distribution"]
    parts = ", ".join(f"{k}: {v}" for k, v in dist.items())
    L.append(f"Simulated outcome distribution across {obj['n_runs']} runs — {parts}.")
    L.append("")
    L.append(obj["outcome"]["label"])
    if obj["outcome"]["note"]:
        L.append("")
        L.append(f"_{obj['outcome']['note']}_")
    L.append("")

    # What we'd fix before filing
    L.append("## What we'd fix before filing")
    L.append("")
    if obj["fixes"]:
        for fx in obj["fixes"]:
            L.append(f"- {_sentence_with_citation(fx['text'], fx['runs'])}")
    else:
        L.append("_No fixes synthesized — review the transcripts directly._")
    L.append("")

    return "\n".join(L).rstrip() + "\n"


def write_outputs(md: str, obj: dict, out_md: str) -> str:
    os.makedirs(os.path.dirname(out_md) or ".", exist_ok=True)
    with open(out_md, "w", encoding="utf-8") as f:
        f.write(md)
    out_json = re.sub(r"\.md$", "", out_md) + ".json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
    return out_json


# ---------------------------------------------------------------------------
# CLI + offline selftest.
# ---------------------------------------------------------------------------
def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Bench Report generator v0.")
    p.add_argument("runs_dir", nargs="?", help="data/arena_runs/<slug>")
    p.add_argument("--out", default=None, help="output .md path (json emitted alongside)")
    p.add_argument("--selftest", action="store_true",
                   help="run offline logic checks (no network) and exit")
    return p.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> None:
    args = parse_args(argv)
    if args.selftest:
        _selftest()
        return
    if not args.runs_dir:
        sys.exit("usage: python3 pipeline/report.py <runs_dir> [--out …] | --selftest")
    slug = slug_of(args.runs_dir)
    out_md = args.out or os.path.join(REPORTS_ROOT, f"{slug}.md")
    if not out_md.endswith(".md"):
        out_md += ".md"
    summary, runs = load_engagement(args.runs_dir)
    md, obj = build_report(slug, summary, runs, arms.call_model_long)
    out_json = write_outputs(md, obj, out_md)
    print(json.dumps({"slug": slug, "n_runs": obj["n_runs"],
                      "markdown": out_md, "json": out_json,
                      "sections": ["Attack Map", "Survival Table",
                                   "Outcome picture", "What we'd fix before filing"]}))


def _selftest() -> None:
    """Offline verification of assembly, citation, sanitization, and guardrails.
    Uses a stub writer so no API is touched (respects the <=$2 and no-network path)."""
    def stub(system: str, user: str) -> str:
        if "fix bullets" in user:                       # fix_list
            return ("- Plead the operative contractual promise explicitly RUNS: 1, 2\n"
                    "- Add who-what-when to the fraud count RUNS: 2\n"
                    "- Tie damages to the identified breach 40% RUNS: 99\n")
        return "This exploits a pleading gap [run 999] and needs 50% more detail."

    summary = {
        "n_runs": 2,
        "outcome_distribution": {"Y": 1, "N": 1},
        "attack_table": {"rule 9(b) knockout": {"appeared": 1, "won": 1}},
        "survival_table": {
            "solid arg": {"appeared": 2, "held": 2, "decisive": 1},
            "shaky arg": {"appeared": 2, "held": 1, "decisive": 0},
        },
        "label": "SIMULATED",
    }
    runs = [
        {"run": 1, "judge": "Liman", "attack_label": "rule 9(b) knockout",
         "advocate_args": ["solid arg", "shaky arg"], "decisive_arg": "solid arg",
         "transcript": {"opponent_attack": "attack one", "bench_pressure_points": "press one"}},
        {"run": 2, "judge": "Liman", "attack_label": "",
         "advocate_args": ["solid arg", "shaky arg"], "decisive_arg": "solid arg",
         "transcript": {"opponent_attack": "attack two", "bench_pressure_points": "press two"}},
    ]
    md, obj = build_report("selftest-motion", summary, runs, stub, date="2026-07-16")

    checks = []
    def check(name: str, cond: bool) -> None:
        checks.append((name, cond))

    check("citation format helper", format_citation([7, 3, 3]) == "[run 3, 7]")
    check("all five sections present", all(
        h in md for h in ("# Bench Report", "## Attack Map", "## Survival Table",
                          "## Outcome picture", "## What we'd fix before filing")))
    check("G1 label verbatim", SIMULATED_LABEL in md)
    check("G5 disclaimer present", DISCLAIMER in md)
    check("G3 low-run flag", "insufficient runs for a stable picture" in md)
    check("attack sentence cited to real run", "[run 1]" in obj["attack_map"][0]["sentence"])
    check("no model-authored [run 999] leaked", "run 999" not in md and "run 999" not in json.dumps(obj))
    check("no percentages anywhere in body", "%" not in md)
    check("weak arg got a fix sentence", any(s["weak"] and s["fix"] for s in obj["survival_table"]))
    check("strong arg got no fix sentence",
          all(not s["fix"] for s in obj["survival_table"] if not s["weak"]))
    check("fixes parsed with valid citations", len(obj["fixes"]) == 3)
    check("invalid run 99 fell back to all runs", obj["fixes"][2]["runs"] == [1, 2])
    check("every fix bullet cites a run",
          all(re.search(r"\[run [\d, ]+\]", f"{fx['text']} {format_citation(fx['runs'])}")
              for fx in obj["fixes"]))
    check("machine-readable json round-trips", json.loads(json.dumps(obj))["slug"] == "selftest-motion")

    failed = [name for name, ok in checks if not ok]
    for name, ok in checks:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    if failed:
        sys.exit(f"SELFTEST FAILED: {len(failed)} check(s): {failed}")
    print(f"SELFTEST OK — {len(checks)} checks passed")


if __name__ == "__main__":
    main()
