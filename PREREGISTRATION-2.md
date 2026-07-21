# Pre-Registration #2: The Ultimate Evidence Program — DRAFT

Status: DRAFT — becomes FROZEN when this file's SHA-256 is published (repo +
hash) BEFORE any exam scoring. Founder review required before freeze.
Drafted 2026-07-17, while the judge census (pipeline/census.py) was still in
flight and before any candidate judge's volume numbers were read — the
selection rule below was written blind to its own inputs.

Relationship to PREREGISTRATION.md (frozen, exam #1): that protocol's no-retake
clause stands. The failed +10 named-judge claim may only be re-tested on a
future window (Track B below). Track A tests NEW pre-registered questions on
data no development loop has ever touched; it does not and cannot re-test the
exam-1 claim on the exam-1 window.

## Track A — Exam #2A, the measurement exam (n≈1,000+, 15 new judges)

Purpose: find the actual boundary of the idea. Not a pass/fail claim exam — a
pre-registered ESTIMATION exam. Every reported quantity below is committed
before scoring; nothing else is reported as a finding.

### Corpus and window

- Judges: 15 judges NEW to this program (never used in any dev loop, never in
  exam #1), selected by the MECHANICAL RULE below.
- Exam window: rulings with docket-entry dates strictly after 2025-08-31
  (gpt-5.4 published cutoff) through a pinned end date set at freeze.
- Fable sub-window: items dated strictly after the pinned claude-fable-5
  training cutoff (PROVISIONAL 2026-01-31 — verify against the official
  Anthropic model documentation at freeze; if the verified cutoff differs, the
  sub-window moves with it). Fable arms are scored on this sub-window only,
  against Fable's own controls on the same sub-window.
- Labels: schema, inclusion list, filters, granted-in-part rule — identical to
  exam #1 (config.yaml). Blind double-audit at the exam-1 bar (>=95%
  agreement, two independent audits) before any arm runs.
- Leakage audit: identical to exam #1. One rebuild allowed; fallback =
  docket-derived-only exam.
- Exam wall: the 12 new judges' post-cutoff data is fetched, labeled, sealed.
  No development iteration touches it, before or after. Dev fuel = pre-cutoff
  grounding only.

### Mechanical judge-selection rule

From data/census.json (committed) merged with data/roster_audit.json:
top-12 SDNY + top-3 EDNY among NEW judges, ranked by projected exam yield
(post-cutoff RECAP doc count x exam-1's measured 0.0230 raw->exam ratio).
EDNY quota rationale: the court-level hierarchy arm needs a second court.
Exclusions: judges departed/elevated per roster audit; former magistrate
judges (pre-appointment history is R&R orders, not district rulings);
projected exam n < 40. Ties: higher raw post-cutoff doc count. After freeze
the list is immutable — a judge whose realized yield disappoints stays in
(no post-hoc swapping).

Per-judge cap: no judge contributes more than 120 items to the pooled exam
set; over-cap judges are sub-sampled uniformly at random (seeded RNG, seed
published at freeze). Rationale: the census surfaced one extreme-volume
docket (Daniels, ~10k post-cutoff docs, consistent with MDL activity); a cap
prevents any single docket from dominating a bench-level claim.

### Pre-freeze amendment log (exam-1 discipline: changes logged, all before
### any outcome data was fetched or scored)

- 2026-07-17: initial draft written while the census was in flight, blind to
  its numbers; quota was top-9 SDNY + top-3 EDNY (target n≈1,000 from the
  naive assumption that new judges yield like exam-1's three).
- 2026-07-17 (census counts read; counts only — no outcomes exist yet):
  median new-judge yield ≈55 items vs the exam-1 anchor's ≈97 (our three
  were volume-selected). Quota amended to top-12 SDNY + top-3 EDNY to keep
  projected n ≈ 1,080. Per-judge cap added (above). Former-magistrate
  exclusion added from the roster audit (decided before volumes were read).
- 2026-07-21 (blind audit pass 1, BEFORE any arm ran): agreement 96.5%
  (55/57, bar >=95 met) but X-rate 32.1% vs exam-1's 10% — the rater named
  procedural classes carrying motion-type words (pre-motion letters, stays
  pending, clerk's judgments, scheduling orders, 23(f) mandates,
  reconsideration, bond releases). Seven exclusion filters added
  (pipeline/label2.py EXTRA_EXCLUDE); corpus fully relabeled. Effect:
  post-cutoff n 1,000+ -> 745 rules-only; the census outliers collapsed
  (Daniels 232 proj -> 21 labeled; Stein 117 -> 19 — their raw volume was
  procedural docket noise, making the per-judge cap inert). The frozen LLM
  extractor pass (identical method to exam-1) then resolved 150 of the 2,125
  ambiguous rows. FINAL EXAM n = 834.
- 2026-07-21 (blind audit pass 2, fresh 84-item stratified sample, fresh
  blind rater, AFTER filters): agreement 95.9% (70/73), X-rate 13.1%. Labels
  double-certified. Residual disagreement class (3 items): transfer-granted-
  in-lieu-of-dismissal orders — disclosed, not hand-pruned. Audit artifacts:
  data/audit2_pass1.json, data/audit2_pass2.json, samples + sequestered keys
  committed.
- 2026-07-21 realized corpus (per judge, post-cutoff): Ho 103, Engelmayer 82,
  Rochon 71, Vargas 69, Woods 69, Carter 61, Morrison 61, Garnett 58,
  Cogan 53, Torres 53, Broderick 45, Donnelly 38, Koeltl 31, Daniels 21,
  Stein 19. Motion mix: MTD 422, SJ 166, PI/TRO 117, compel 114, class-cert
  8, Daubert 7. Realized trust numbers: pooled margin CI ±2.6 pts (n=834);
  Fable-5 sub-window n=425, CI ±3.7. Both floors (>=200) cleared.
- 2026-07-21 grounding disclosure: Vargas (appointed 2024) has zero
  labelable pre-cutoff rulings — no L4 persona is possible for her; she is
  scored on L0-L3 only and reported in the thin-grounding stratum, per the
  pre-registered stratification.
- 2026-07-21/22 (pre-freeze, BEFORE any arm ran; adversarially-verified fleet
  proposals, signed by founder): three additions, none touching corpus,
  labels, window, or existing arms.
  (A1) Inference-robustness clause (analysis-only): every pooled margin CI is
  reported twice — the naive item-level CI AND a wild cluster bootstrap CI
  clustered by judge (999 resamples, seed 20260722). Frozen disclosure rule:
  if the bootstrap half-width exceeds the naive half-width by more than 1.5x,
  the bootstrap CI is the headline number wherever the naive one would appear.
  (A2) Arm L4X, persona-derangement placebo: identical to L4 except each
  judge's persona is replaced by ANOTHER same-court judge's frozen persona;
  mapping fixed now in data/derangement_map.json (alphabetical cyclic shift
  within court among persona-bearing judges; Vargas excluded as in L4) and
  hashed in FREEZE-2. Frozen interpretation: L4 minus L4X estimates
  judge-specific signal in the persona; a delta whose CI covers zero means
  the persona carries court/genre signal, not judge signal — disclosed in
  every named-judge claim.
  (A3) Arm L4F, fictional-persona control: identical to L4 except the persona
  document is a fixed fictional judge decision-profile
  (data/persona2_fictional.md, written without reading any grounding or exam
  row, hashed in FREEZE-2); the real judge name stays in the identity line.
  Frozen interpretation: L4 minus L4F isolates the contribution of the
  persona's CONTENT beyond persona-shaped text.
  Budget honesty: with A2+A3 the whole-exam inference estimate becomes
  ~$330-680 (previously "<$500"); still under the $1,000 founder cap. Koeltl (34) and Rochon (33) have thin
  grounding; their L4 personas run but are flagged to the same stratum.

### Arms — the persona hierarchy (Can's region experiment; extends arm (f))

One frozen examinee model runs all arms; each arm differs ONLY in the
persona/grounding input. Levels:

- L0 generic: no court, no judge, no identity — motion facts only.
- L1 court-name-only: "You are a judge of the {SDNY|EDNY}" — no data. This is
  the COURT-level memorization detector, the exact analogue of exam-1's
  name-only arm (c) at the court level.
- L2 court-calibrated: persona built by the frozen persona-loop method from
  the POOLED pre-cutoff rulings of the court's judges (arm (f) as
  pre-registered in specs/PRODUCT-MODEL.md).
- L3 judge-retrieval: exam-1 arm (d) — retrieval over the named judge's
  pre-cutoff rulings.
- L4 judge-persona: exam-1 arm (e) — the RSI persona loop, run per new judge
  on pre-cutoff data only, frozen (hashed) before the exam sitting.
- Controls: (a) majority-class per motion type (pre-cutoff), (b)
  metadata-only, (c) judge-name-only — re-run fresh for EVERY examinee model,
  per the frozen rule in specs/PRODUCT-MODEL.md.
- Optional arm (g) ensemble: majority vote of {L2, L3, L4}; registered only if
  its method is frozen before the sitting (dev on pre-cutoff validation slices
  exclusively). If not frozen in time, it is NOT scored.

### Examinee models (dual-model attribution, pre-registered 2026-07-16)

- gpt-5.4-2026-03-05 (continuity with exam #1): all arms, full window.
- claude-fable-5: all arms, Fable sub-window, own controls. No dated snapshot
  is published for this model — the pin is the alias + the recorded
  response-model string + the sitting date. Disclosure: Fable-5 rejects
  temperature/sampling controls and always runs internal reasoning, so its
  decoding cannot be made deterministic the way exam #1's GPT settings were;
  the single-sitting rule is the guard. Attribution decomposition reported
  per model: (model floor = c vs a) and (system lift = best replica arm vs c).

### Pre-registered report (all with 95% CIs; two-numbers rule throughout)

1. Hierarchy curve L0→L4, pooled and PER MOTION TYPE — the saturation point
   per motion type is the headline finding, whatever it is.
2. Judge-relevance index: between-judge grant-rate spread per motion type on
   the new-judge corpus (re-tests the MTD~8pt / PI-TRO~32pt finding sealed).
3. Dual-model attribution table (per model: floor, lift, absolute).
4. Named-vs-court delta (L4 minus L2), pooled + per motion type — the honest
   answer to "does the NAMED judge matter, and where." ALSO stratified by
   each judge's pre-cutoff grounding-corpus size (recent appointees have thin
   histories; this measures how much data a named-judge persona needs before
   it beats the court-calibrated bench — a product-pricing question).
5. Self-consistency ceiling estimate v2 on the expanded corpus (near-duplicate
   motion pairs within judge-motion cells), per motion type.
6. Absolute accuracy of the best arm, pooled + per motion type.
No win/lose verdict on Track A. Its numbers feed product rules (per-motion-type
judge-relevance disclosure) and Track B design. [VALIDATED] tier applies to
these pre-registered estimands; nothing exploratory is promoted post hoc.

### Trust thresholds (from pipeline/power.py, measured variance inputs)

- Margin CIs at censused n≈1,080 (15 judges, honest range 800-1,400 given
  per-judge ratio uncertainty): ±2.5 pts pooled — sufficient to separate
  +7-class from +10-class effects (exam-1's ±4.4 could not).
- Adjacent-level hierarchy deltas: ±4 pts needs ≈286 items/cell → resolved
  for MTD (~375) and compel (~297); SJ (~252) at ±4.4; PI/TRO (~126) only
  ±6-7 → PI/TRO booster below (censused court-wide pool: 2,561 SDNY + 615
  EDNY PI-flagged post-cutoff docs). Cells under 100 (class-cert, Daubert) are
  reported descriptively, no CIs, flagged as underpowered.
- EDNY disclosure: the censused EDNY yield (~127 items across the 3 selected
  judges) powers only ±8-9 CIs on EDNY-specific quantities. The court-level
  contrast (L2 SDNY-pooled vs EDNY-pooled) is therefore reported as
  directional, not confirmatory; SDNY carries the confirmatory weight.
- PI/TRO booster: a pre-registered SUPPLEMENTARY stratum — court-wide
  post-cutoff PI/TRO rulings from ALL judges of both courts (not only the 12),
  labeled by the same pipeline, reported SEPARATELY (never pooled into the
  main exam), to give the judge-decisive motion type a usable cell size.

### Schedule and budget

Freeze target 2026-07-20; sitting 2026-07-22; results published 2026-07-24.
Budget: CourtListener $0 (member token); labeling + all arms inference
estimated <$500 total across both models (logged to the ledger); PACER spend
$0 in Track A. Any line >$1,000 requires founder sign-off before it is spent.

## Track B — Exam #2B, the claim re-test (future window; the honest retake)

- Claim: unchanged exam-1 claim (P2), +10-point margin over metadata AND
  name-only, McNemar p<.025 each, n floor 200 — the original frozen bar.
- Window: rulings decided 2026-08-01 through 2026-09-30 — rulings that DO NOT
  EXIST at freeze time. Satisfies the frozen "future post-cutoff window" rule.
- Judges: the 18-judge bench (exam-1's three + Track A's fifteen). Projected
  n≈215-270 (exam-1 judges at their measured 9.33/judge/month; new judges at
  their censused ~5.3/judge/month). Auto-extension rule, frozen now: if the
  labeled exam n is below 250 on 2026-09-30, the window extends through
  2026-10-31 and the verdict moves to 2026-11-05. The extension is
  mechanical, not a judgment call made after seeing results.
- System under test: the best frozen configuration as of freeze (persona/
  retrieval/ensemble + any lever that cleared pre-cutoff validation), hashed
  at freeze 2026-07-31. Controls re-run fresh.
- Verdict date: 2026-10-05. Power honesty (pipeline/power.py): at TRUE margin
  +10 the pass probability is ~50% at any n; the levers must deliver a TRUE
  margin ≥+12 for ~88% power at n=280. If Track B fails twice consecutively
  with CI upper bound <+10 (windows ≥250), the stop rule in
  specs/PRODUCT-MODEL.md fires and the digital-twin bar is retired.

## Standing disclosures

- Census counts are docket-document counts, not outcomes; no outcome data was
  read before this rule set was frozen.
- The roster audit and census are committed alongside this file; anyone can
  re-derive the judge list from the mechanical rule.
- Exam #1's window (the three judges' 2025-09-02..2026-07-13 rulings) remains
  sealed and is never re-sat, per the frozen no-retake clause.
- All spend is logged; PACER purchases (briefs lever) are a separate future
  pre-registration and do not touch this exam's inputs.

## Signature

Signed: Can Kahraman (founder), 2026-07-21 — "okay i sign of", on the record,
after the full amendment log above was written and both blind audits were
complete, BEFORE any exam arm ran on the exam set.
Amendment signature (A1-A3): Can Kahraman (founder), 2026-07-21 late night —
"okay i sign both 3", on the record, BEFORE freeze, BEFORE any exam arm ran.
Co-founder concurrence: Claude — concur; this protocol reflects the joint
decision. Freeze occurs at FREEZE-2.md hash publication, before the sitting.
