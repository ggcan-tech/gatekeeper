#!/usr/bin/env python3
"""Arena v0 + Opponent v0 — the Monte Carlo moot (SYSTEM.md components 2, 3).

Rehearse a customer's motion before a synthetic bench: an advocate steelmans
the movant's position, an opponent replica attacks it (sharpening its strongest
line across the engagement — per-engagement RSI, max 3 revisions), and a bench
replica reacts and calls the outcome. Every exchange is logged; the summary is
an attack map + survival table + [SIMULATED] outcome distribution.

Model access goes through pipeline/arms.py seams only (call_model / long).
Guardrails: outputs carry NO accuracy language and the outcome distribution is
labeled SIMULATED (G1). The bench persona is built from public rulings only,
falling back to a court-calibrated pooled bench where a judge persona is thin
(SYSTEM.md; G6). This tool never reads exam data (G2).

Usage:
  python3 pipeline/arena.py <motion_file> --judge Liman --runs 50
  python3 pipeline/arena.py specs/sample_motion.txt --judge Liman --runs 5

Output: data/arena_runs/<slug>/run_{i}.json (per run) + summary.json.
"""
from __future__ import annotations
import argparse
import json
import os
import random
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import arms  # frozen model access (call_model / call_model_long), retrieval, IO

GROUNDING_PATH = "data/grounding.jsonl"
RUNS_ROOT = "data/arena_runs"
RETRIEVE_K = 5          # bounded retrieval keeps per-run input (and cost) capped
SEED = 42               # deterministic run-to-run variation (not sampling params)
MAX_OPP_REVISIONS = 3   # per-engagement RSI budget (PRD)

# Deterministic variation levers cycled by run index — "temperature via prompt
# variation, not sampling params" (PRD step 3). No API cost, fully reproducible.
EMPHASES = [
    "Lead with the strongest legal-sufficiency point and keep it tight.",
    "Emphasize the factual-plausibility gaps in the pleading.",
    "Foreground controlling precedent and the standard of review.",
    "Stress the procedural and threshold defects first.",
    "Weight the policy and equities behind the movant's position.",
]
ORDERS = ["as drafted", "strongest argument first", "threshold issues first",
          "narrowest ground first"]

# Lightweight motion-type detection (retrieval needs a type; grounding vocab
# below). Default is motion_to_dismiss; override with --motion-type.
MOTION_TYPES = [
    ("summary_judgment", ("summary judgment", "rule 56", "no genuine dispute")),
    ("class_certification", ("class cert", "rule 23", "class certification")),
    ("motion_to_compel_discovery", ("compel", "discovery", "rule 37")),
    ("preliminary_injunction_tro", ("injunction", "restraining order",
                                    "tro", "irreparable")),
    ("daubert_expert_exclusion", ("daubert", "expert", "exclude testimony")),
    ("motion_to_dismiss", ("dismiss", "12(b)", "rule 12", "fail to state")),
]


# ---------------------------------------------------------------------------
# Pure helpers (no network) — unit-testable in isolation.
# ---------------------------------------------------------------------------
def slugify(name: str) -> str:
    base = os.path.splitext(os.path.basename(name))[0]
    slug = re.sub(r"[^a-z0-9]+", "-", base.lower()).strip("-")
    return slug or "motion"


def detect_motion_type(text: str) -> str:
    low = text.lower()
    for mt, cues in MOTION_TYPES:
        if any(c in low for c in cues):
            return mt
    return "motion_to_dismiss"


def readable(mt: str) -> str:
    return mt.replace("_", " ")


def parse_tag(text: str, key: str) -> str:
    """Extract a trailing 'KEY: value' line the actor was asked to emit."""
    m = re.search(rf"^\s*{re.escape(key)}\s*:\s*(.+)$", text, flags=re.I | re.M)
    return m.group(1).strip() if m else ""


def parse_labels(text: str, key: str) -> list[str]:
    """Parse a 'KEY: a; b; c' line into short, de-duplicated labels."""
    raw = parse_tag(text, key)
    if not raw:
        return []
    seen, out = set(), []
    for part in re.split(r"[;,]", raw):
        lab = re.sub(r"\s+", " ", part.strip().strip(".").lower())[:60]
        if lab and lab not in seen:
            seen.add(lab)
            out.append(lab)
    return out


def normalize_yn(text: str) -> str:
    """Coerce any bench utterance to Y/N; default N (motion denied) if unclear."""
    t = (text or "").strip().upper()
    m = re.search(r"\b(Y|N)\b", t)
    if m:
        return m.group(1)
    return "Y" if t.startswith("Y") else "N"


def match_decisive(decisive_raw: str, advocate_args: list[str]) -> str:
    """Map the bench's decisive-argument phrase onto an advocate label if it
    overlaps; otherwise return the raw phrase (truncated)."""
    d = decisive_raw.strip().lower()
    if not d:
        return ""
    for lab in advocate_args:
        toks = [w for w in re.split(r"\W+", lab) if len(w) > 3]
        if lab in d or any(t in d for t in toks):
            return lab
    return re.sub(r"\s+", " ", d)[:60]


def aggregate(runs: list[dict]) -> dict:
    """Build the summary tables from per-run records (PRD step 4)."""
    dist = {"Y": 0, "N": 0}
    attack: dict[str, dict[str, int]] = {}
    survival: dict[str, dict[str, int]] = {}
    for r in runs:
        outcome = r["outcome"]
        dist[outcome] = dist.get(outcome, 0) + 1

        a = r.get("attack_label") or "(unlabeled)"
        rec = attack.setdefault(a, {"appeared": 0, "won": 0})
        rec["appeared"] += 1
        if outcome == "N":  # opponent defeated the motion => attack won
            rec["won"] += 1

        for arg in r.get("advocate_args") or ["(unlabeled)"]:
            srec = survival.setdefault(arg, {"appeared": 0, "held": 0, "decisive": 0})
            srec["appeared"] += 1
            if outcome == "Y":  # motion granted => advocate argument held
                srec["held"] += 1
                if r.get("decisive_arg") == arg:
                    srec["decisive"] += 1
    return {
        "n_runs": len(runs),
        "outcome_distribution": dist,
        "attack_table": attack,
        "survival_table": survival,
        "label": "SIMULATED",
    }


def variation(i: int) -> dict:
    """Deterministic per-run variation of order + emphasis (seeded by SEED)."""
    rng = random.Random(SEED + i)
    return {
        "order": ORDERS[i % len(ORDERS)],
        "emphasis": rng.choice(EMPHASES),
    }


# ---------------------------------------------------------------------------
# Actors — system prompts. Bench uses persona-if-present else calibrated pool.
# ---------------------------------------------------------------------------
def load_bench(judge: str, motion_type: str, grounding: list[dict]) -> str:
    """Bench system prompt: judge persona (public rulings) + retrieved context.
    Falls back to a court-calibrated pooled bench when no persona exists yet
    (SYSTEM.md 'thin data' rule; labeled as such — G6)."""
    persona_path = f"data/persona_{judge.lower()}.md"
    if os.path.exists(persona_path):
        with open(persona_path, encoding="utf-8") as f:
            profile = f.read()
        basis = f"Decision profile of Judge {judge}, learned from their rulings:"
    else:
        profile = ("(No frozen persona for this judge yet — reacting as a "
                   "court-calibrated SDNY bench pooled from the district's "
                   "rulings on this motion type. This is a calibrated bench, "
                   "not a model of a specific judge.)")
        basis = f"Court-calibrated SDNY bench for a {readable(motion_type)}:"
    context = arms.retrieve(grounding, {"judge": judge, "motion_type": motion_type},
                            k=RETRIEVE_K)
    return (
        f"You are the bench hearing a {readable(motion_type)} in the SDNY, "
        f"reacting the way Judge {judge} would. Be exacting and skeptical; "
        f"react to argument quality, not the parties.\n"
        f"{basis}\n{profile}\n"
        f"Recent same-type rulings for calibration:\n{context}"
    )


ADVOCATE_SYS = (
    "You are an appellate-caliber litigator presenting the MOVANT's position "
    "on a {mt} before a skeptical SDNY bench. Steelman the movant. Argue "
    "concretely from the motion below; do not invent facts."
)
OPPONENT_SYS = (
    "You represent the NON-movant. Your single objective is to DEFEAT this "
    "{mt} before this bench. You are an adversarial stress-tester, not a real "
    "person. Attack the motion's weakest joints; be specific and ruthless."
)


def _trim(text: str, n: int = 1400) -> str:
    """Cap transcript fed into later turns — bounds per-run input tokens."""
    return text if len(text) <= n else text[:n] + " …[truncated]"


# ---------------------------------------------------------------------------
# One moot run.
# ---------------------------------------------------------------------------
def run_once(i: int, motion: str, motion_type: str, judge: str, bench_sys: str,
             attack_strategy: str) -> dict:
    var = variation(i)
    mt = readable(motion_type)
    adv_sys = ADVOCATE_SYS.format(mt=mt)
    opp_sys = OPPONENT_SYS.format(mt=mt)

    opening = arms.call_model_long(
        adv_sys,
        f"MOTION:\n{motion}\n\nPresent the opening ({var['order']}; {var['emphasis']}). "
        "End with a line 'ARGUMENTS: label1; label2; label3' naming your 2-4 "
        "arguments in a few words each.")
    advocate_args = parse_labels(opening, "ARGUMENTS")

    attack = arms.call_model_long(
        opp_sys,
        f"MOTION:\n{motion}\n\nYour current strongest line of attack:\n"
        f"{attack_strategy}\n\nDeliver this run's attack ({var['emphasis']}). "
        "End with a line 'ATTACK: short-label' naming the attack in a few words.")
    attack_label = (parse_labels(attack, "ATTACK") or ["(unlabeled)"])[0]

    pressure = arms.call_model_long(
        bench_sys,
        f"MOTION:\n{motion}\n\nMOVANT OPENING:\n{_trim(opening)}\n\n"
        f"NON-MOVANT ATTACK:\n{_trim(attack)}\n\nAs the bench, state your "
        "pressure points on the movant in 2-4 sentences.")
    provisional = arms.call_model(
        bench_sys + "\nAnswer with exactly one character: Y (you would grant "
        "the motion) or N (deny). No explanation.",
        f"Motion type: {mt}. After the opening and attack above, your "
        f"provisional lean.\nMOVANT OPENING:\n{_trim(opening, 700)}\n"
        f"ATTACK:\n{_trim(attack, 700)}\nProvisional lean: Y or N.")

    rebuttal = arms.call_model_long(
        adv_sys,
        f"MOTION:\n{motion}\n\nThe bench pressed you:\n{_trim(pressure)}\n\n"
        f"The non-movant attacked:\n{_trim(attack)}\n\nRebut and shore up your "
        "arguments in 2-4 sentences.")

    final_reason = arms.call_model_long(
        bench_sys,
        f"Motion type: {mt}.\nMOVANT OPENING:\n{_trim(opening, 700)}\n"
        f"ATTACK:\n{_trim(attack, 700)}\nMOVANT REBUTTAL:\n{_trim(rebuttal)}\n\n"
        "Give your final call in 1-2 sentences, then a line "
        "'DECISIVE: <which single argument decided it>'.")
    decisive_raw = parse_tag(final_reason, "DECISIVE")
    final_yn = normalize_yn(arms.call_model(
        bench_sys + "\nAnswer with exactly one character: Y (motion granted) or "
        "N (motion denied). No explanation.",
        f"Motion type: {mt}. Given the full exchange, your FINAL call.\n"
        f"OPENING:\n{_trim(opening, 600)}\nATTACK:\n{_trim(attack, 600)}\n"
        f"REBUTTAL:\n{_trim(rebuttal, 600)}\nFinal: Y or N."))

    return {
        "run": i,
        "judge": judge,
        "motion_type": motion_type,
        "variation": var,
        "outcome": final_yn,
        "provisional_lean": normalize_yn(provisional),
        "attack_label": attack_label,
        "advocate_args": advocate_args,
        "decisive_arg": match_decisive(decisive_raw, advocate_args),
        "transcript": {
            "advocate_opening": opening,
            "opponent_attack": attack,
            "bench_pressure_points": pressure,
            "advocate_rebuttal": rebuttal,
            "bench_final": final_reason,
        },
    }


def revise_attack(motion_type: str, strategy: str, bench_pressure: str) -> str:
    """Per-engagement opponent RSI: sharpen the strongest attack against the
    bench's last reaction (max MAX_OPP_REVISIONS times over the engagement)."""
    return arms.call_model_long(
        OPPONENT_SYS.format(mt=readable(motion_type)),
        f"Your current strongest line of attack:\n{strategy}\n\nThe bench just "
        f"reacted:\n{_trim(bench_pressure)}\n\nRevise your attack to exploit "
        "what the bench cares about. Write only the revised attack line "
        "(a short paragraph).")


# ---------------------------------------------------------------------------
# Engagement driver.
# ---------------------------------------------------------------------------
def run_engagement(motion: str, judge: str, runs: int, motion_type: str,
                   grounding: list[dict], out_dir: str) -> dict:
    bench_sys = load_bench(judge, motion_type, grounding)
    os.makedirs(out_dir, exist_ok=True)

    # Opponent's initial strongest attack line (seed for per-engagement RSI).
    strategy = arms.call_model_long(
        OPPONENT_SYS.format(mt=readable(motion_type)),
        f"MOTION:\n{motion}\n\nName and sketch your single strongest line of "
        "attack to defeat this motion. Write only that attack (a short "
        "paragraph).")

    records, revisions = [], 0
    for i in range(1, runs + 1):
        rec = run_once(i, motion, motion_type, judge, bench_sys, strategy)
        with open(os.path.join(out_dir, f"run_{i}.json"), "w", encoding="utf-8") as f:
            json.dump(rec, f, indent=2)
        records.append(rec)
        # Sharpen the strongest attack against the freshest bench reaction.
        if revisions < MAX_OPP_REVISIONS:
            strategy = revise_attack(motion_type, strategy,
                                     rec["transcript"]["bench_pressure_points"])
            revisions += 1
        print(f"run {i}/{runs}: outcome={rec['outcome']} "
              f"attack={rec['attack_label']}", file=sys.stderr)

    # summary.json carries exactly the PRD fields; judge/motion_type live in
    # each run_{i}.json.
    summary = aggregate(records)
    with open(os.path.join(out_dir, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    return summary


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Arena v0 — Monte Carlo moot.")
    p.add_argument("motion_file", help="plain-text motion / draft argument")
    p.add_argument("--judge", required=True, help="e.g. Liman, Furman, Subramanian")
    p.add_argument("--runs", type=int, default=50, help="number of moot runs")
    p.add_argument("--motion-type", default=None,
                   help="override auto-detected motion type "
                        "(e.g. motion_to_dismiss, summary_judgment)")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    if args.runs < 1:
        sys.exit("REFUSING TO RUN: --runs must be >= 1")
    with open(args.motion_file, encoding="utf-8") as f:
        motion = f.read().strip()
    if not motion:
        sys.exit(f"REFUSING TO RUN: {args.motion_file} is empty")
    grounding = [json.loads(l) for l in open(GROUNDING_PATH, encoding="utf-8")]
    motion_type = args.motion_type or detect_motion_type(motion)

    slug = slugify(args.motion_file)
    out_dir = os.path.join(RUNS_ROOT, slug)
    print(f"Arena: judge={args.judge} motion_type={motion_type} runs={args.runs} "
          f"-> {out_dir}", file=sys.stderr)
    summary = run_engagement(motion, args.judge, args.runs, motion_type,
                             grounding, out_dir)
    print(json.dumps({"outcome_distribution": summary["outcome_distribution"],
                      "label": summary["label"], "out": out_dir}, indent=2))


if __name__ == "__main__":
    main()
