# SYSTEM.md — Production System Blueprint ("the shape")

The one engine, its actors, its judge-of-judges, and its rails. This is the
spec Archon's coding agents build from — each component below becomes an
`archon workflow run archon-feature-development --branch feat/<component>`
run in its own worktree, from a PRD in specs/.

## The flow (customer path)

draft motion in → INTAKE → ACTOR FACTORY → ARENA (Monte Carlo moot)
→ SELECTOR → REPORT → customer; real-world outcome later → FEEDBACK LOOP.

## Components

### 1. Intake
Customer's draft (docx/pdf/text) → structured motion: type, court, judge,
claims, requested relief, key arguments. Zero-retention path (guardrail G4).

### 2. Actor Factory
Builds three actors per engagement:
- **Bench replica** — persona from the assigned judge's public rulings via the
  RSI persona loop (pipeline/persona_loop.py, lab-validated method). Where the
  judge's data is thin: court-calibrated bench (pooled district persona),
  labeled as such.
- **Opponent replica** — argues the other side. Trained ADVERSARIALLY: its
  objective is to beat the customer's draft, RSI'd against the bench replica's
  reactions (loop: attack → bench scores → sharpen attack). It is a synthetic
  stress-tester, never claimed to be a real person (guardrail G1).
- **Advocate** — presents the customer's position, steelmanned.

### 3. Arena (Monte Carlo moot)
N simulated exchanges (default 50) with controlled variation: argument order,
emphasis, concessions, counter-framings. Every run logged: transcript,
bench reactions, outcome call.

### 4. Selector — "the system that looks at the simulation and decides best"
Scores every Arena run: which attacks landed, which survived, outcome
distribution. Anchoring rule (guardrail G2): the Selector's outcome scoring is
anchored to the VALIDATED prediction layer (the exam-tested predictor). Its
qualitative rubric (argument-strength scoring) is lab-material — it improves
only through lab A/Bs, never by vibes in production.

### 5. Report generator
Distills Arena+Selector into the Bench Report: attack map (what kills this
draft), survival table (which arguments held across N runs), fix list,
outcome distribution with three-tier labels (G1). Concierge first: founder
reviews every report before delivery until further notice.

### 6. Feedback loop (the compounding asset)
Customer files; judge rules; the real outcome enters the calibration ledger:
predicted vs actual, per motion type, per court. Published quarterly. This is
the moat — the only sim-vs-reality ledger in the category.

## Guardrails (non-negotiable, enforced in code not policy)

- **G1 Three-tier claim labels** on every customer-facing number:
  [VALIDATED] = from a sealed public exam · [MEASURED] = practice-track,
  methodology public, not sealed · [SIMULATED] = Arena output, no accuracy
  claim. A report can never present tier-3 as tier-1.
- **G2 Exam wall**: production code and RSI loops never read any sealed exam
  window, past or pending. Enforced by date-partitioned data access.
- **G3 Confidence gate**: below-threshold predictions ship as "insufficient
  basis — routed to human analysis," never as a guess. (The survey-twin rule:
  the system refuses to bluff.)
- **G4 Confidentiality**: customer drafts are never used for training, zero
  retention on request, no cross-customer leakage (ABA Op. 512 posture).
- **G5 Not legal advice**: reports are preparation intelligence; no filing
  recommendations; disclaimer generated into every report.
- **G6 Persona dignity**: named-judge personas built from public professional
  record only; correction/de-listing channel; "prediction and rehearsal tool
  built from public rulings," never "digital twin of Judge X."

## RSI, precisely — what improves, against what, when

| Loop | Optimizes | Ground truth | Where it runs |
|------|-----------|--------------|---------------|
| Persona loop | bench replica | judge's pre-cutoff rulings | lab |
| Opponent loop | attack quality | bench replica's reactions | lab + per-engagement |
| Selector rubric | scoring quality | lab A/Bs vs validated predictor | lab only |
| Calibration | confidence labels | REAL filed outcomes (feedback loop) | production ledger |

"Success → go to customer" means: a loop's improvement graduates from lab to
shop only with a lab A/B result attached, and customer-facing claims only
through a sealed exam (PIVOT.md lab rules).

## Build order (Archon runs, shop-first)

1. `feat/arena` — Arena v0 + Opponent v0 (needed for first concierge pilot)
2. `feat/selector` — Selector v0 anchored to validated predictor
3. `feat/report` — Bench Report v0 (markdown → pdf), G1/G3/G5 labels built in
4. `feat/intake` — document parsing (manual until pilots demand it)
5. `feat/ledger` — calibration ledger + feedback ingestion
Each: PRD in specs/, built by archon-feature-development in a worktree,
reviewed before merge. Lab levers (full-text personas, ensembles) continue in
lab-exp2 in parallel.
