# PRD: Bench Report generator v0 (feat/report)

Read SYSTEM.md (component 5, guardrails G1/G3/G5) and specs/arena-prd.md.
Conventions: Python 3.9+, stdlib only, `from __future__ import annotations`,
model access via pipeline/arms.py seams only.

## Deliverable

`pipeline/report.py` — CLI:
`python3 pipeline/report.py data/arena_runs/<slug> --out data/reports/<slug>.md`

## Behavior

1. Load summary.json + all run_{i}.json from the runs directory.
2. Generate a markdown Bench Report with EXACTLY these sections:
   - **Header**: motion slug, judge/bench used, n_runs, date, and the G5
     disclaimer line ("preparation intelligence, not legal advice").
   - **Attack Map**: from attack_table — each attack line, how often it
     appeared, how often it won; one model-written sentence per attack
     explaining what it exploits (call_model_long, grounded in the run
     transcripts; no new claims).
   - **Survival Table**: from survival_table — which advocate arguments held,
     which were decisive; one fix-suggestion sentence per weak argument.
   - **Outcome picture**: the distribution, labeled exactly
     "[SIMULATED] — Arena output; no accuracy claim" (G1). If runs < 20,
     add "insufficient runs for a stable picture" (G3 spirit).
   - **What we'd fix before filing**: 3-5 bullets synthesized from pressure
     points across transcripts (model-written, cite run numbers).
3. Every model-written sentence must cite its run(s) like [run 3, 7]. No
   percentages or accuracy language anywhere except the labeled distribution.
4. Also emit the same content as data/reports/<slug>.json (machine-readable).

## Non-goals (v0)

No PDF, no styling, no email, no multi-motion batching, no UI.

## Acceptance

- Runs on the existing data/arena_runs/sample-motion (5 runs) end to end.
- Report contains all five sections, the G1 label string verbatim, the G5
  disclaimer, and >= 1 run citation per model-written sentence.
- Only pipeline/report.py is created; nothing else modified.
- Cost per report <= $2 in API calls.
