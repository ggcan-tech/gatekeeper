# HANDOFF — co-founder session transfer (written 2026-07-21 ~16:30 Istanbul)

Everything a successor needs that is NOT already in the repo's other files or
in persistent memory. Repo is truth; this file is the connective tissue.
Read order: README.md → this file → PREREGISTRATION-2.md → PIVOT.md →
specs/PRODUCT-MODEL.md → SYSTEM.md → specs/market-geometry.md →
docs/litigation-101.md → docs/trust-numbers.md → pipeline/ → data/.

## 0. THE CLOCK (do not lose a day like the last session almost did)

- Today Tue Jul 21. Exam #2A sits WEDNESDAY Jul 22 midday. Results public
  FRIDAY Jul 24. YC application deadline MONDAY Jul 27, 20:00 PT (binding).
- PREREGISTRATION-2 is SIGNED by Can (in the file, pushed) but NOT YET
  FROZEN. Freeze = FREEZE-2.md with SHA-256 hashes, published BEFORE any arm
  runs. Also flip the "Status: DRAFT" line at top of PREREGISTRATION-2.md to
  SIGNED/FROZEN language in the same commit.

## 1. IMMEDIATE CRITICAL PATH (the sitting is NOT ready — build list)

What exists: exam2.jsonl (n=834, certified), grounding2.jsonl (batch-1
judges), personas arriving, signed protocol. What DOES NOT EXIST YET:

1. **pipeline/arms2.py — THE SITTING RUNNER. Not written.** Must implement,
   importing exam-1's arms.py (freeze-hashed: import, NEVER edit):
   - Arms per PREREGISTRATION-2: (a) majority per motion type from
     pre-cutoff pooled; (b) metadata-only; (c) name-only; L0 generic;
     L1 court-name-only; L2 court-pooled persona; L3 judge-retrieval
     (mirror arms.py retrieval over per-judge grounding2 rows);
     L4 judge-persona (data/persona2_{judge}.md); optional (g) ensemble
     majority-vote of {L2,L3,L4} ONLY if tonight's val test passed.
   - Examinee models: gpt-5.4-2026-03-05 via arms.py's client; claude-fable-5
     via Anthropic SDK (client.messages.create; structured outputs or strict
     one-char parsing; thinking always-on — give max_tokens headroom ~2048
     and parse the final Y/N; handle stop_reason=="refusal" as abstain=wrong;
     effort low). Fable scores ONLY items dated > 2026-01-31 (n=425) with its
     OWN (b),(c) controls run on that sub-window. VERIFY Fable cutoff against
     the official model docs at freeze; prereg says provisional 2026-01-31.
   - Cache every (model,arm,item)→answer to disk incrementally (jsonl), so a
     crash resumes. ~9 arms × 834 GPT + ~9 × 425 Fable ≈ 11.3K calls.
2. **L2 court-pooled personas — not built.** Run persona_loop with a pooled
   grounding file per court (SDNY pool = all SDNY judges' grounding2 rows;
   EDNY pool likewise; PERSONA_OUT_SUFFIX naming e.g. persona2_sdny_pool.md
   via a judge field hack: write pooled rows with judge="SDNY_POOL"). Do
   after batch-2 grounding lands tonight.
3. **Ensemble validation (arm g gate):** on pre-cutoff val slices, compare
   majority{L2,L3,L4} vs best single arm. Passes → freeze arm (g); fails →
   drop, log either way in FREEZE-2.
4. **Leakage audit** (pipeline/leakage_audit.py, exam-1 method) on exam2 —
   run pre-freeze; blinded arm must not beat majority by >3pts.
5. **FREEZE-2.md:** hashes of PREREGISTRATION-2.md, data/exam2.jsonl,
   data/grounding2.jsonl (final), all 14 persona2_*.md for new judges +
   2 pool personas, pipeline/arms2.py, pipeline/label2.py, audit artifacts;
   subsample seed for any capped judge (cap now inert); publish → commit →
   push → only THEN sit.
6. **score2.py + the report:** pre-registered ESTIMANDS ONLY (no win/lose):
   hierarchy curve L0→L4 pooled + per motion type w/ 95% CIs; judge-relevance
   index (between-judge spread per motion type); dual-model attribution
   (floor c−a, lift best−c, per model); L4−L2 named-vs-court delta pooled +
   per motion type + stratified by grounding size (Vargas=0 stratum,
   Koeltl 34 / Rochon 33 thin); self-consistency v2 (near-cell pairs);
   absolute accuracies. Two-numbers rule everywhere.
7. **Publish Friday:** scorecard2.json + README results block + website
   (docs/index.html) update + a plain-language findings section.
8. **PI/TRO booster stratum** (pre-registered, SUPPLEMENTARY, reported
   separately): court-wide PI pulls NOT yet fetched (censused 2,561 SDNY +
   615 EDNY docs). Can run after the main sitting; do not pool.

## 2. LIVE PROCESSES (daemons survive session death; MY WATCHERS DID NOT)

- `ingest2.py` (nohup daemon): grounding pull, was 41/54 tasks; quota-paced
  (Tier-4 ≈2,400/day on the NEW CourtListener account); finishes tonight.
  Log: data/ingest2.log. Judge list: data/judges2.json.
- `persona_loop.py` (nohup daemon): batch-1 (7 judges) running; ~2 done
  (cogan, donnelly) + engelmayer mid-flight at time of writing. Launch
  batch-2 after pull completes: rebuild data/grounding2.jsonl from
  labeled2.jsonl (date<=2025-08-31) for ALL judges, then
  `GROUNDING_PATH=data/grounding2.jsonl PERSONA_OUT_SUFFIX=2 nohup python3
  -u pipeline/persona_loop.py >> data/persona2.log 2>&1 &`. The loop skips
  nothing — filter the grounding file to not-yet-done judges to avoid
  re-running finished ones.
- **Re-arm watchers immediately** (session-scoped, all dead): pull-54/54,
  persona-completion. Pattern: `until <check>; do sleep 300; done; echo X`
  with run_in_background.
- caffeinate daemon tied to puller pid keeps the Mac awake; lid must stay
  OPEN during long runs (clamshell kills everything).

## 3. KEYS / ACCOUNTS / MONEY (the quota saga condensed)

- **CourtListener:** token.txt (gitignored) = NEW second account, Tier 4
  ($75/mo, ~2,400/day). Facts learned the hard way: quota is per-ACCOUNT not
  per-token; throttled (429) probes COUNT into the rolling 24h window and
  push the reopen time later; Retry-After header is authoritative; membership
  tier→API sync lags ~a day and broke entirely on the first account
  (Tier-2 grace-period rows confuse the resolver → fell to free 250/day).
  First account: $75 stuck, support ticket sent Fri + refund/merge follow-up
  Mon — CHASE the reply. Never scrape their site; they're our long-term data
  ally (bulk files exist but have NO docket-entries export).
- **OpenAI:** openai_key.txt (gitignored). Credits topped ~$100 Tue. 429 with
  code insufficient_quota == OUT OF CREDITS, not rate limit — probe the error
  body before diagnosing. ROTATE the key after the lab settles (standing).
- **Anthropic key: STILL NOT PROVIDED.** Blocker for the Fable arm. Ask Can
  first thing. Fable-5: $10/$50 per MTok; no dated snapshot (pin = alias +
  response.model + sitting date, already in prereg); sampling params
  rejected; thinking always-on (disclosed in prereg as non-determinism).
- **CL exam-1 artifacts are freeze-hashed** (FREEZE.md): labeled.jsonl,
  exam.jsonl, grounding.jsonl, persona_{liman,furman,subramanian}.md,
  score.py, arms.py — READ ONLY forever. NOTE: persona2_{liman,furman,
  subramanian}.md are exam-1's post-freeze full-text-lever personas — same
  suffix as exam-2's new personas; don't confuse the two families.
- Spend to date this program: ~$150 CL memberships + ~$100 OpenAI + Fable
  sitting est. $200-350. All under the $1K line. PACER briefs (Track B
  lever) = the only pending >$1K decision (~$1.8-2.7K full; RECAP-free scan
  first).

## 4. WHAT CAN OWES (chase kindly, firmly — pivot doc gives you the mandate)

1. Anthropic API key (TODAY — gates tomorrow's sitting).
2. 3 founder-profile stories (most-weighted YC answers).
3. 60-second video (plan bullets exist in mission; needs 3 takes).
4. Live YC form check/transcription day-one.
5. Interview counts + written notes for interviews #1 (Turkish lawyer,
   "real demand" feel) and #2 (Turkish prosecutor — see §6 learnings).
6. Thursday bump emails to non-repliers (10 sent Monday).
7. Mock interview (10-min drill) before Aug — Arena-based prep planned.

## 5. OUTREACH MACHINE (running + promised)

- 10 hyper-personalized cold emails SENT Mon from his Gmail. Targets file:
  `/Users/cankahraman/ggggg/outreach-targets.md` — PRIVATE, outside repo,
  never commit. Wave-2 = 7 LinkedIn-path (Unikowsky via Substack = highest
  signal). Wave-3 = 10 more with public emails.
- PROMISED (build Wed): daily batch — research agent finds ~15 NEW verified
  targets (dedupe vs file; add NY Commercial Division litigators bucket per
  market-geometry), extracts a real hook each, drafts in Can's voice via
  Gmail MCP create_draft (NEVER send — drafts only, his finger on every
  trigger), appends to targets file. Throttle when his call calendar fills.
  Reply-rate framing: 10-30% over 3-7 days; hook = the published study.
- Email template that works: personalized hook line → pre-registered study
  one-liner + repo link → "interviewing litigators about how motions get
  pressure-tested before filing; 20 min; not selling anything."

## 6. CHAT-ONLY KNOWLEDGE (not written anywhere else — keep alive)

**Interview learnings (Turkish prosecutor):** lawyers pay for judge intel
everywhere (Turkey once had a platform selling judge opinions); he predicts
judge-identity matters MORE in US (rule-based civil law vs discretionary
common law) — matches our PI/TRO finding; drafting-AI disappointment is
universal ("tried it, unhappy") = our rehearsal wedge dodges burned ground;
his "monthly subscription" instinct = our Model B later, not step one
(Gavelytics died on subscriptions; per-event pricing scaled — EvenUp,
Casetext).

**Country test (why US; Turkey/UK verdicts):** a market needs (1) public
per-judge written rulings, (2) buyers paying $$$ per motion, (3) stable
long-tenure judges. US federal maxes all three. Turkey fails 1+2 (UYAP
closed; fees too low; judges rotate by decree; regulatory risk — France
banned judicial analytics) → Turkey = interview gym + diaspora referral
source ONLY. UK = half-passes (Find Case Law/BAILII open; London Commercial
Court high stakes; loser-pays makes calibration MORE valuable; but
oral-heavy, thin per-judge written interim rulings) → chapter 3 after NY
ComDiv. Delaware Chancery: 7 judges = thin stats → "marketing, not
statistics" (fleet verdict).

**World-models frame (YC-partner vocabulary, NEVER litigator-facing):**
brief = action, ruling = next state, arena = model-predictive control;
"perfect world model needs zero environment samples" ↔ filing = one sample
that costs everything → domain forces model-based rehearsal. BRIEFS LEVER =
Dreamer-style action-conditioning (everyone has states/CourtListener; only
we will have draft→outcome pairs; Pre/Dicta never reads the brief so can
never have action data) → calibration ledger = the moat restated. We chose a
domain with NO real-time constraint (24-72h reports) = ideal habitat for
heavy test-time planning. Ceiling (~65% self-consistency) = environment
entropy, not model failure — "we published the noise floor of law."

**Q&A bank Can drilled (reuse for the Founder Sheet):** Did we really fail?
— the claim failed (+7 < +10 frozen bar), the engine didn't (78.7,
p≤.0022); keeping our own kill bar IS the product; we lost a marketing
sentence, bought a reputation. Courtroom.ai "90%" = unverifiable
white-paper backtest; memorization inflation (our name-only 71.5 proves the
mechanism). What accuracy satisfies customers? — three bars: beat their gut
(lawyers ~60s-70s overconfident), visibly beat free ChatGPT (=name-only
71.5; our +7 is exactly this), be calibrated (ledger); plus attack-map
hit-rate matters more than the binary; 90s+ claims HURT credibility.
Why did nobody build this? — three unlocks ~18mo old: models that read
briefs + reason legally; RECAP maturity; published cutoffs make honest
post-cutoff validation possible; incumbents' economics (Lexis/Westlaw sell
to partners; moots are billable) blocked them; founder-market fit =
eval-culture + multi-agent harness. Fine-tuning? — judge-side SATURATED
(full-text lever ≈ noise); error lives on case-facts side; tuning = style
lever for arena realism at most. Research-agent arm? — Can's lever,
pre-registered +2-4, blocked on contamination protocol (snapshot cut,
docket canaries, boxed-vs-unboxed) — Track B/exam-3, never improvised.

**Market-geometry highlights (full memo specs/market-geometry.md):**
federal-first 2-1-0 (zero state-first); Pre/Dicta owns Gavelytics' state
corpus and STILL chose federal appellate (revealed preference); funders
spend $5-25K/case diligence (39 funders, ~$2.8B/yr) → C-track pricing
trivially justified; Bench IQ ($5.3M seed) explicitly refuses accuracy
claims → falsifiable-prediction lane ceded to us; wedge language:
"NYC high-stakes commercial dispositive motions, both courthouses";
NY ComDiv = chapter 2 (NYSCEF free PDFs, same buyers); **CA
tentative-rulings archiver = unbuilt day-one call option (they get DELETED
after hearings — value compounds with elapsed time; tiny daemon; build next
week)**; Viewpoints AI's live sim-vs-real-mock-jury head-to-head = the
validation template for a future Arena-vs-real-moot study; sitting judge on
2025 ABA podcast: lawyers' method is literally "Google the judge."

**Persona-writer A/B (open idea, not built):** engineered loop vs simple —
error-clustering by motion type, separate adversarial critic, per-motion-type
structured persona schema, nested holdout. Candidate for post-YC lab week.

**YC-partner-replica fun fact:** NEVER a public demo (unvalidated persona =
the cosplay we expose). Honest version: use our own Arena privately to
mock-interview Can in August; if asked, the line is "we rehearsed this
interview against our own engine — labeled simulation, here's the attack
map." Honesty tiers as punchline.

## 7. PITFALLS THAT COST US HOURS (do not repeat)

- Shell cwd RESETS between Bash calls unpredictably — `cd /Users/cankahraman/
  ggggg/gatekeeper &&` on EVERY command or absolute paths.
- `pkill -f <name>` kills your own watchers whose command strings contain
  the name — use distinct markers in watcher commands.
- label_llm2.py cache = IDs only (data/labeled2_llm.done): any labeled2
  rewrite ORPHANS LLM rows; rebuild the .done from rows with
  label_source=="llm" then rerun (pattern in history).
- Output pipes (`| tail`) buffer until exit; use `python3 -u` + direct log
  files.
- Foreground `sleep` is blocked by the harness; use run_in_background
  until-loops.
- OpenAI + persona loops + resolver = same key: NEVER run two OpenAI
  consumers concurrently (429 storm). Sequence them.
- exam-1's predictions.jsonl / exam window = burned forever; ensemble dev on
  pre-cutoff val slices ONLY.
- Archon: run from CAN'S terminal only (nested-Claude hangs); tiers via CLI
  flags, not config yaml.
- Never auto-send email; never scrape CourtListener; never edit
  freeze-hashed files; nothing exploratory promoted to a claim post hoc.

## 8. DECISION REGISTER POINTERS

PIVOT.md (shop owns calendar to Jul 27; interviews never wait for evidence
— Can's own documented pattern, hold the line kindly+firmly) ·
PREREGISTRATION.md + FREEZE.md (exam-1, closed) · PREREGISTRATION-2.md
(SIGNED; Track A estimands, Track B retake w/ auto-extension to Oct 31 if
n<250 on Sep 30) · specs/PRODUCT-MODEL.md (A→C→B, 30-day proof test, lever
sequence, stop rule, two-numbers, frontier-substitution hedge) · SYSTEM.md
(G1-G6 guardrails, RSI table, build order) · specs/market-geometry.md ·
docs/trust-numbers.md (±10 bar needs TRUE ~+12; n-vs-CI tables).
