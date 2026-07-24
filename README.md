# Gatekeeper

**We argue your motion 50 times before you file it once.**

Gatekeeper sells the Pre-Filing Bench Report: send a draft motion, and within
24-72 hours get back how a bench calibrated to your court will attack it,
which arguments survive, and a disclosed-confidence outcome read — built by
Monte-Carlo mooting the draft against a rulings-grounded simulation of the
bench. Product page: [ggcan-tech.github.io/gatekeeper](https://ggcan-tech.github.io/gatekeeper)
· Sample report: [data/reports/sample-motion.md](data/reports/sample-motion.md)

This repository is the company's **public lab**. Every accuracy claim we make
is pre-registered here before scoring, sealed by published hashes, and sat
exactly once. We publish losses.

## Exam #1 — the kill experiment (July 2026, verdict: LOSS, published)

Question: does a replica grounded in a named judge's rulings beat a generic
model on rulings nothing could have memorized? n=291 post-cutoff SDNY rulings
(entry dates strictly after the exam model's training cutoff), 3 judges,
model pinned at gpt-5.4-2026-03-05, labels double-audited blind (98.1%,
98.6%), leakage audit passed.

| arm | accuracy |
|---|---|
| (a) majority-class | 67.0 |
| (b) metadata-only | 72.2 |
| (c) name-only — memorization detector | 71.5 |
| (d) retrieval replica | 78.0 |
| (e) RSI-persona replica | **78.7** |

Both replica arms beat both controls (McNemar p ≤ .0135; persona arm
p ≤ .0022). The rulings-grounding effect is real: **+5.8 to +7.2 points**.
It missed our own frozen product-grade bar (+10), so per protocol the
"digital twin of Judge X" claim is **dead, in writing** —
[PIVOT.md](PIVOT.md) was signed within 24 hours. What survives is what we
sell: a court-calibrated bench with a measured, disclosed judge-specific
edge — never a twin.

Two findings that shape the product: judge identity barely moves
motion-to-dismiss outcomes (~8-point spread across judges) but is decisive
on preliminary-injunction/TRO (39% vs 71% grant rates) — so reports disclose
judge-relevance per motion type. And ~76% of summary-judgment motions are
decided on the papers: the brief *is* the argument, which is why the product
rehearses the actual draft.

## Exam #2A — results (published 2026-07-24, on the pre-registered date)

[PREREGISTRATION-2.md](PREREGISTRATION-2.md) Track A: an ESTIMATION exam — no
win/lose verdict, every reported quantity committed before scoring. n=834
post-cutoff rulings from 15 SDNY/EDNY judges never touched by any development
loop, selected by a mechanical rule; labels double blind-audited (96.5%,
95.9%); frozen by hash ([FREEZE-2.md](FREEZE-2.md)) before the sitting; sat
exactly once (gpt-5.4-2026-03-05 full window; claude-fable-5 on its own
n=425 post-cutoff sub-window with its own controls). Full tables:
[data/scorecard2.json](data/scorecard2.json).

**The hierarchy curve (GPT-5.4, pooled; every replica arm reported as TWO
numbers — absolute, and edge over the judge-name-only control):**

| arm | accuracy | edge vs name-only [95% CI] |
|---|---|---|
| (a) majority-class | 75.4 | — |
| (b) metadata-only | 74.5 | — |
| (c) judge-name-only — memorization detector | 75.8 | 0 (def.) |
| L0 generic | 75.4 | −0.4 [−2.6, +1.9] |
| L1 court-name-only | 76.7 | +1.0 [−1.1, +3.0] |
| **L2 court-calibrated bench** | **87.5** | **+11.8 [+8.9, +14.6]** |
| L3 judge-retrieval | 84.4 | +8.6 [+6.0, +11.3] |
| L4 judge-persona | 82.1 | +6.4 [+3.7, +9.0] |
| (g) ensemble {L2,L3,L4} | 86.1 | +10.3 [+7.7, +12.9] |

**The five findings, plainly:**

1. **The court-calibrated bench is the best predictor.** L2 wins pooled
   (87.5%, +11.8) and in every adequately powered motion type (MTD 88.9,
   SJ 89.2, PI/TRO 83.8, compel 86.0). This is the arm the product ships.
2. **The named-judge persona is dead, now with a placebo to prove it.**
   L4 *underperforms* the court bench by −5.4 points [−7.7, −3.1], and a
   deranged persona (the WRONG same-court judge's persona, arm L4X) scores
   within +1.1 [−1.7, +3.8] of the right judge's. The persona's content
   effect is real (+6.5 over a fictional-judge control) but it is
   court/genre signal, not judge signal. Exam #1 killed the twin claim at
   n=291; this kills it at n=834 with controls.
3. **Frontier substitution, measured and disclosed.** claude-fable-5 scores
   86.8% from the judge's NAME alone (its name-only control), and its best
   arm (L2, 88.0%) adds only +1.2 [−1.0, +3.4] — a CI that covers zero. On
   the smartest examinee, our system's edge is ~0–3 points. This is the
   risk we named in [specs/PRODUCT-MODEL.md](specs/PRODUCT-MODEL.md) before
   the exam: the company sells the validated report and the calibration
   ledger, not a secret model.
4. **Doctrine primers are mostly already inside the model.** D0 (doctrine,
   no identity) adds +3.0 [+0.5, +5.5] over generic for GPT; on top of a
   judge persona doctrine adds nothing (L4D−L4 = −0.4 [−2.0, +1.3]).
5. **Judge identity varies the corpus, yet pooling still wins.** Between-judge
   grant-rate spreads are large (MTD 29 pts, SJ 45, PI/TRO 41, compel 29 —
   small per-judge n, wide CIs), but knowing the courthouse's line (L2)
   still beats imitating the individual judge (L4). Where the judge you
   drew matters most (PI/TRO), we disclose it per motion type in every
   report.

Post-freeze errata (both before any result was published, both in
[FREEZE-2.md](FREEZE-2.md)): E1 — a Vargas/L4X derangement-map inconsistency,
fixed by honoring the frozen map. E2 — arm (g) was gated primary pre-freeze
but its column was missing from the first scorecard render; it is derived
mechanically from the recorded answers by the frozen vote rule
([pipeline/derive_ensemble2.py](pipeline/derive_ensemble2.py)) and reported
above — it does *not* beat the single best arm, and we report it anyway,
because its registration was frozen.

**Track B (the honest retake)** is unchanged: the original +10 named-judge
bar, re-tested only on rulings that did not exist at registration (Aug–Sep
2026 window), 18-judge bench, verdict 2026-10-05 (mechanical extension rule
if n<250). Given finding 2, Track B is now the twin claim's last window.

Power analysis first, results second: [docs/trust-numbers.md](docs/trust-numbers.md)
pre-specifies the n and CI each claim needs — including the finding that
exam #1's n=291 could not distinguish a +7 edge from a +10 edge (±4.4),
which is the entire reason Track A existed.

## The rules (frozen)

1. Pre-register before scoring; freeze by published SHA-256
   ([FREEZE.md](FREEZE.md)); one sitting per window; no retakes, ever —
   failed claims re-test only on future rulings.
2. Exam sets contain only post-training-cutoff outcomes. Random holdouts are
   banned: frontier models have read the public court record. Arm (c) exists
   to measure exactly that.
3. Every result reports TWO numbers — absolute accuracy and edge over the
   name-only control — because conflating them is how this category minted
   fake 90% claims.
4. Customer-facing claims carry honesty tiers: [VALIDATED] sealed exam ·
   [MEASURED] methodology public · [SIMULATED] no accuracy claim.

**Standing offer:** we will run any competitor's accuracy claim through this
protocol — post-cutoff window, pre-registered, published either way.

## Map

| | |
|---|---|
| [PREREGISTRATION.md](PREREGISTRATION.md) / [FREEZE.md](FREEZE.md) | exam #1 protocol + hashes |
| [data/scorecard.json](data/scorecard.json) | exam #1 results, McNemar tests |
| [PREREGISTRATION-2.md](PREREGISTRATION-2.md) / [FREEZE-2.md](FREEZE-2.md) | exam #2A protocol + hashes + errata |
| [data/scorecard2.json](data/scorecard2.json) | exam #2A results — all pre-registered estimands, CIs |
| [PIVOT.md](PIVOT.md) | the signed 24-hour pivot decision |
| [SYSTEM.md](SYSTEM.md) | production blueprint: actors, guardrails G1-G6 |
| [specs/PRODUCT-MODEL.md](specs/PRODUCT-MODEL.md) | business model + lab verdict + stop rule |
| [docs/litigation-101.md](docs/litigation-101.md) | founder field guide |
| [pipeline/](pipeline/) | ingest → label → audit → arms → score, census + power |
