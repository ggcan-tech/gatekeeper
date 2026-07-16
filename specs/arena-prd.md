# PRD: Arena v0 + Opponent v0 (feat/arena)

Read SYSTEM.md first — this builds components 2 (Opponent only) and 3.
Constraints: Python 3.9+, stdlib + repo conventions only (see pipeline/),
model access via pipeline/arms.py seams (call_model / call_model_long),
`from __future__ import annotations` in every file. Guardrails G1-G6 apply.

## Deliverable

`pipeline/arena.py` — CLI: `python3 pipeline/arena.py <motion_file> --judge Liman --runs 50`

## Behavior

1. Load the motion (plain text file: the customer's draft argument summary).
2. Build actors:
   - Bench: system prompt from data/persona_{judge}.md (exists) + retrieval
     context from data/grounding.jsonl (reuse arms.retrieve pattern).
   - Opponent: seeded with "you must defeat this motion before this bench";
     each round it may revise its strongest attack based on the bench's last
     reaction (per-engagement RSI, max 3 revisions).
   - Advocate: steelmans the motion's position.
3. One run = advocate opening → opponent attack → bench reaction (pressure
   points + provisional lean Y/N) → advocate rebuttal → bench final call
   (Y/N + which argument was decisive). Vary across runs: argument order,
   emphasis, opponent attack line (temperature via prompt variation, not
   sampling params).
4. Output data/arena_runs/<slug>/run_{i}.json per run: transcript, bench
   pressure points, decisive argument, outcome call. Plus summary.json:
   outcome distribution, attack frequency table (which attacks appeared and
   how often they won), survival table (which advocate arguments held).
5. Label every outcome figure [SIMULATED] in summary.json (G1). No accuracy
   language anywhere in output.

## Non-goals (v0)

No PDF parsing (plain text in), no report prose (report generator is
feat/report), no UI, no parallelism beyond simple sequential runs, no
persistence beyond the runs directory.

## Acceptance

- Runs end-to-end on a sample motion (create specs/sample_motion.txt — a
  2-paragraph motion-to-dismiss argument) with --runs 5 against Liman.
- summary.json fields exactly: {"n_runs", "outcome_distribution",
  "attack_table", "survival_table", "label": "SIMULATED"}.
- Total cost of a 50-run engagement ≤ $10 in API calls (cap tokens per turn).
- No file outside pipeline/arena.py + specs/sample_motion.txt is modified.
