# PRD: Case-Digest Optimizer v0 (lab/digest-optimizer) — "the loop that learns what to read"

Founder's mechanism (Can, 2026-07-16), pointed at the measured bottleneck.
Read SYSTEM.md (guardrails), PIVOT.md (lab rules), pipeline/persona_loop.py
(the pattern this generalizes). Conventions: Python 3.9+, stdlib only,
`from __future__ import annotations`, model access via pipeline/arms.py seams.

## Why (one paragraph of context the builder must internalize)

Three measurements agree: judge-side signal is saturated (full-text personas
≈ summary personas), within-cell self-consistency ≈65% (case facts dominate),
exam margins +6-7 (real but modest with THIN case inputs — 200-char docket
summaries). The untested lever is case-side input richness. This component
learns HOW to digest a case document into the features a bench actually
responds to. The learned artifact is an EXTRACTION INSTRUCTION SET (per
motion type), not per-case summaries — it must transfer to customer drafts.

## Data (v0 — no new purchases)

data/opinion_texts.jsonl (370 pre-cutoff items, avg 20K chars). The opinion's
own narrative contains the case posture we need — AND its outcome, which is
the leakage hazard this design must kill (see Leakage).

## Architecture

pipeline/digest_optimizer.py — CLI:
  python3 pipeline/digest_optimizer.py --motion-type motion_to_dismiss --max-iter 8

Loop (persona-loop pattern, one level up):
1. E_0 = seed extraction instructions ("From a case document, extract: parties
   and posture; claims and counts; the legal standard invoked; the movant's
   core theory; disputed facts; procedural history. NEVER outcome language.").
2. DIGEST: apply E_t via call_model_long to each item's text → digest cache
   data/digests/{motion_type}/iter{t}/{id}.txt (cap 900 chars each).
3. LEAKAGE GATE (every iteration, frozen): blinded arm (no judge identity, no
   grounding) predicts outcomes from digests alone on the eval slice; if it
   beats the majority baseline by >3 pts (one-sided binomial vs majority+3,
   p<.05 — the leakage_audit.py pattern), the digests leak → E_t is revised
   with an explicit anti-leakage instruction and the iteration DOES NOT SCORE.
4. SCORE: frozen predictor = persona-v1 file + retrieval (exact arms.py
   composition) + the digest appended to build_inputs; accuracy on the
   held-out eval slice (same VALIDATION_SLICE/SEED discipline as persona_loop
   — eval items' digests are built but their outcomes never shown to E).
5. REVISE: show E_t the mistakes (digest + prediction + actual) → E_{t+1}
   revises WHAT TO EXTRACT (instructions, not case content). Plateau stop 3.
6. OUTPUT: data/extractor_{motion_type}.md (best E), data/digest_history.jsonl
   (iter, acc, leakage_margin, n).

## Baselines the winner must beat (dev-track, printed in history)

- B0: no digest (v1 inputs exactly) — the current 88.6/100/82.1 regime.
- B1: static E_0 digest (no optimization) — proves the LOOP adds value, not
  just "more text".
Win (dev): best E beats B0 by >=5 pts pooled across judges on the eval slice
AND beats B1 by >=2 pts. Miss = record honestly; the lever report says so.

## Guardrails

- G2 exam wall: pre-cutoff items only; the script refuses any item dated
  after exam.model_cutoff in config.yaml (assert at load).
- Leakage gate is per-iteration and unskippable (step 3).
- The extraction instructions are product IP: data/extractor_*.md and
  data/digests/ go into .gitignore (add the entries).
- No claims language anywhere; this is lab tooling ([MEASURED] tier at best).

## Non-goals (v0)

No PACER brief purchases, no per-judge extractors, no exam scoring, no
integration into arena.py (that's a follow-up PRD once dev-win is shown).

## Acceptance

- End-to-end run on motion_to_dismiss with --max-iter 3 completes: digest
  cache written, leakage gate exercised (its numbers in history), history has
  B0/B1/E accuracies, extractor file written.
- Deterministic sampling (SEED 42); rerun reproduces the same eval split.
- Cost: full 8-iter run on one motion type <= $40 (cap digest calls: eval
  slice + <=120 train items per iteration; token caps in call sites).
- Only pipeline/digest_optimizer.py + .gitignore entries added.
