# Pre-Registration: The Gatekeeper Kill Experiment

Status: DRAFT — becomes FROZEN when this file's SHA-256 is published publicly
(GitHub repo + hash posted) BEFORE any exam scoring. After freezing, no clause
may change; a violated clause voids the exam.

## Claim under test (P2)

An AI replica of a specific federal judge, grounded via retrieval over the
judge's pre-cutoff public rulings, predicts the judge's post-cutoff motion
outcomes better than (a) majority-class guessing, (b) a biography/metadata-only
model, and (c) the same model given only the judge's name — the memorization
detector. If it cannot, the named-judge replica product is dead, in writing.

## Why post-cutoff only

Frontier models are pretrained on the public court record (CourtListener is in
The Pile's FreeLaw component). Any exam on pre-cutoff rulings grades the model
on its own training data. The exam set therefore contains ONLY outcomes whose
decision/docket-entry date is strictly after the pinned model's published
training cutoff. Filing date is irrelevant; inputs use pre-ruling material only.

## Arms (one frozen model runs all five)

- (a) majority-class per motion type, computed on the PRE-cutoff pooled corpus
- (b) metadata-only: judge biography/appointment data, NO rulings
- (c) name-only: "You are Judge {name}, SDNY", NO rulings — memorization detector
- (d) replica-retrieval: same model + retrieval over pre-cutoff grounding corpus
- (e) replica-persona (RSI loop, the founding hypothesis): a per-judge persona
  document produced by an iterative optimization loop — draft persona → predict
  a held-out validation slice of PRE-cutoff rulings → score → revise persona →
  repeat. The loop runs EXCLUSIVELY on pre-cutoff data; the winning persona is
  frozen (hashed) before the exam and sits the exam exactly once.

## Win rule (frozen)

A replica arm passes iff it (1) exceeds arm (a) accuracy as a floor, AND
(2) beats arm (b) and arm (c) EACH by >= 10 accuracy points with one-sided
exact McNemar p < .025 per comparison (alpha Bonferroni-corrected from .05
because two replica arms are tested), on the pooled post-cutoff exam set.
The COMPANY claim ("a rulings-grounded replica of the named judge beats
generic and biographical baselines") passes iff at least one replica arm
passes. Which arm passes determines the product engine. Pooled n >= 200
required; below 200 = UNDERPOWERED = fail for launch and public claims
(point estimates recorded; no re-rolling; no backward window extension).

## Development iteration and retakes (frozen)

Unlimited iteration is permitted BEFORE the exam, on pre-cutoff data only
(including dry-runs on a validation slice). The exam is sat ONCE per exam
window. A failed claim may be re-tested only via a NEW public pre-registration
scored on a FUTURE post-cutoff window (rulings not yet decided at re-registration
time). No retakes on the same window, ever.

## Labels, scope, audits

Label schema, motion inclusion list, hand-verification (a blind random 20%
sample OF THE EXAM SET, minimum 40 items, >=95% agreement — the exam labels
are the load-bearing ones; grounding labels get a 20-item spot check;
rater protocol, disclosed honestly: the blind rater is Claude (Anthropic) —
a different model family from the extraction model (OpenAI gpt-5.4-mini) —
rating raw docket text with no access to pipeline labels at rating time.
Disclosed overlap: the same Claude authored the pipeline's extraction rules,
and saw 3 labeled examples during development; this is a weaker independence
claim than a human legal expert, which the founder (a non-lawyer, non-native
English reader) could not credibly provide. Mitigations: X ("cannot tell")
answers are excluded from agreement and reported; all 66 sampled items and
both label sets are published in this repo for anyone to re-check; and a
practicing US litigator will re-audit a subsample as a published addendum), leakage audit (opinion-derived inputs only; blinded arm must
not beat majority by >3 pts, one-sided test at .05; one rebuild; fallback =
docket-derived-only exam, which counts as audit-passed) — all per config.yaml,
which is hashed together with this file.

## Verdicts

- WIN: scorecard page goes public with per-motion-type accuracy + this protocol.
- LOSS / TIE / UNDERPOWERED: named-judge replica dead for claims; written pivot
  decision (court-calibrated bench vs eval-harness licensing vs stop) within 48h.
- Verdict date: 2026-07-22 (slip cap 2026-07-24, recorded).

## Pre-freeze amendment log (all changes below occurred BEFORE any arm ran)

- 2026-07-15: first blind label audit (66 items) passed at 98.1% agreement but
  surfaced corpus contamination (party filings, magistrate-signed orders,
  administrative grants, cross-listed duplicates). Filters added; labels
  re-extracted; post-filter exam n fell to 180, below the frozen 200 floor.
  Resolution: the floor stays; a third SDNY judge (Arun Subramanian) was added
  to the corpus instead. A fresh blind audit runs on the final 3-judge corpus.
- 2026-07-15/16: arm (e) replica-persona added (the founding RSI hypothesis);
  alpha Bonferroni-corrected to .025 across the two replica arms; dev-iteration
  and no-retake rules codified. Persona loops trained on pre-cutoff data only;
  frozen personas: Furman val 100.0%, Liman 88.6%, Subramanian 82.1%
  (pre-cutoff validation — potentially memorization-inflated; exam decides).
- 2026-07-16: second blind audit on the final 3-judge corpus (78 items):
  98.6% agreement (69/70 rated Y/N), X-rate 10% (down from 18% — filters
  effective). Labels double-certified. Residual non-ruling noise (~9% of the
  exam sample: scheduling/housekeeping entries) is symmetric across all arms
  and disclosed rather than hand-pruned (hand-pruning post-audit would be
  selection bias). Final corpus: 695 labels; exam n=291 (Liman 122,
  Subramanian 112, Furman 57); grounding n=404.

## Model pin

Exam model: gpt-5.4 (dated snapshot gpt-5.4-2026-03-05), published knowledge
cutoff: 2025-08-31 (source: developers.openai.com/api/docs/models/gpt-5.4).
Pinned on: 2026-07-15. Decoding: reasoning_effort=none, deterministic settings,
max completion tokens 16. Same model, same params, all model arms (b), (c), (d).
Rejected alternative, for the record: gpt-5.6-sol (cutoff 2026-02-16) — its
5-month exam window falls below the n>=200 floor; the newest model is the most
contaminated examinee, which is this experiment's entire point.
