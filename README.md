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

## Exam #2 — running now (registered before scoring, as always)

[PREREGISTRATION-2.md](PREREGISTRATION-2.md) — two tracks:

- **Track A (measurement, n≈1,000):** 15 SDNY/EDNY judges never touched by
  any development loop, selected by a mechanical volume rule
  ([census](data/census.json) + [roster audit](data/roster_audit.json) +
  [locked list](data/judges2.json)). Arms form a persona hierarchy — generic
  → court-name-only → court-calibrated → judge-retrieval → judge-persona —
  answering *where* named-judge calibration matters, per motion type. Dual
  examinee models (gpt-5.4 and claude-fable-5, each with its own controls
  and cutoff-respecting window) measure how much edge survives smarter
  base models.
- **Track B (the honest retake):** the original +10 bar, re-tested only on
  rulings that did not exist at registration (Aug-Sep 2026 window), 18-judge
  bench, verdict 2026-10-05.

Power analysis first, results second: [docs/trust-numbers.md](docs/trust-numbers.md)
pre-specifies the n and confidence intervals each claim needs — including
the finding that exam #1's n=291 could not distinguish a +7 edge from a +10
edge (±4.4), which is the entire reason Track A exists.

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
| [PIVOT.md](PIVOT.md) | the signed 24-hour pivot decision |
| [SYSTEM.md](SYSTEM.md) | production blueprint: actors, guardrails G1-G6 |
| [specs/PRODUCT-MODEL.md](specs/PRODUCT-MODEL.md) | business model + lab verdict + stop rule |
| [docs/litigation-101.md](docs/litigation-101.md) | founder field guide |
| [pipeline/](pipeline/) | ingest → label → audit → arms → score, census + power |
