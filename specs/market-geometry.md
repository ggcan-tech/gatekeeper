# Market Geometry Audit — state vs federal, competitors, data existence
**Decision memo for Gatekeeper** (pre-filing Bench Report, $2.5–7.5K/motion, public pre-registered validation at github.com/ggcan-tech/gatekeeper). July 21, 2026.

---

## 1. Verdict: federal-first, with NY Commercial Division annexed early

Judge vote: **2 federal-first, 1 hybrid. Zero votes for state-first.** The hybrid vote collapses into the same operational answer: keep the SDNY/EDNY wedge, add NY ComDiv as venue expansion (not a pivot), and buy the one cheap state option that expires (CA tentative rulings).

The decisive facts, stated plainly:

- **The scoreboard needs federal data.** Gatekeeper's entire differentiator is a pre-registered public accuracy ledger. That requires many uniformly classified, cleanly labeled motion outcomes per judge. Uniform FRCP + one PACER pipeline gives clean grant/partial/deny labels; Pre/Dicta's backtest on 50,000+ motions to dismiss proves the labeled corpus is assemblable at ledger scale (https://www.lawnext.com/startup-alley-pre-dicta). No state equivalent exists. State outcomes are messier to grade — partial grants, oral rulings, minute orders, ephemeral tentatives — so the scoreboard degrades exactly where state coverage expands.
- **Willingness to pay is proven only federally.** Pre/Dicta sells federal per-case prediction at $1,800/case (~$90K/yr at 50 cases) to Quinn Emanuel, insurers, and funders (https://www.globenewswire.com/news-release/2024/05/16/2883441/0/en/Pre-Dicta-Partners-with-Quinn-Emanuel-to-Provide-Lawyers-with-AI-Powered-Litigation-Prediction-Tools.html). No state buyer has ever paid per-case for prediction at any price. State price anchors are Trellis at $69.95–199.95/mo (https://trellis.law/plans) and Gavelytics, which died June 30, 2022 with $5.7M raised (https://www.lawnext.com/2022/06/litigation-analytics-company-gavelytics-is-shutting-down-tomorrow.html).
- **Revealed preference of the best-informed player.** Pre/Dicta owns the Gavelytics multi-state corpus — near-zero marginal cost to enter state prediction — and still chose federal appellate expansion in Aug 2025 over any new state (https://www.lawnext.com/2025/08/legal-analytics-platform-pre-dicta-expands-its-judicial-modeling-adding-appellate-forecasting-enhanced-biographical-analysis-and-comparative-predictions.html).
- **State demand evidence is for records access, not paid prediction.** The flagship "underserved" quote asks for state court *records and analytics coverage* inside subscriptions the firm already pays for (https://www.reddit.com/r/legaltech/comments/1jzuood/what_are_your_thoughts_on_trellis_law/). Nobody in the practitioner corpus asked for a state motion-outcome product.
- **The federal lane is contested but the validated-prediction cell is empty.** The only accuracy numbers in the market — Pre/Dicta's 85%, Courtroom's >90% — are unaudited vendor backtests. Nobody sells independently validated predictions, federal or state. Gatekeeper does not need an empty jurisdiction; it needs the empty validation cell, and it can occupy that from SDNY.
- **The best "state" venue is not a new market.** NY ComDiv buyers are the same NYC firms and clients as the existing SDNY/EDNY book, and NYSCEF gives free guest-accessible PDFs of every e-filed decision and order (https://iapps.courts.state.ny.us/nyscef/CaseSearch). That is a cross-sell at ~$0 data cost, which is why it belongs in chapter 2 rather than justifying a state-first wedge.

## 2. Competitor table

| Name | Courts | Artifact | Motion/case types | Buyer | Validation claim | Implication for us |
|---|---|---|---|---|---|---|
| **Pre/Dicta** | Federal district + CA state; appellate since Aug 2025 | Instant probability from case number (judge bio + party/firm, not case facts) | 10 modules: MTD, MSJ, class cert, transfer, compel, JOP, TRO, PI, Daubert, remand | Quinn Emanuel, insurers (reserves), funders, mediators | 85% on 50K+ MTDs — self-reported, no audit (https://www.lawnext.com/startup-alley-pre-dicta) | Direct competitor and price anchor ($1,800/case). Its unaudited number is the thing our pre-registration attacks. It does not read the case; we do. |
| **Bench IQ** | Federal only; state "planned" | AI reports explaining a judge's reasoning (from transcripts/oral rulings) | Not motion-typed | 4 of top-5 AmLaw firms; $5.3M seed Battery/Inovia (https://www.lawnext.com/2025/08/bench-iq-ai-startup-led-by-former-ross-cofounder-to-understand-judges-decision-patterns-raises-5-3m-seed.html) | Deliberately none: "shape outcomes, not predict" | Occupies the reasoning-explanation lane. Its refusal to claim accuracy leaves the falsifiable-prediction lane to us. |
| **Courtroom.ai** | Venue-agnostic simulation | LLM judge/jury personas for argument testing | Products liability, patent, mass torts, MDL | AmLaw 100, Fortune 1000; pre-seed Neo/Precursor (https://www.businesswire.com/news/home/20260611125975/en/Courtroom-Emerges-From-Stealth-to-Bring-the-Jury-Room-Into-the-War-Room) | ">90%" — white paper on request only, unverifiable | Validates the category; second unaudited number to contrast against. |
| **Lex Machina** | All 94 districts, 13 circuits, PTAB; 1,200+ state courts added Nov 2025 | Descriptive dashboards + annual reports | 22 federal practice areas | Firms, enterprise custom pricing (https://www.lexisnexis.com/en-us/products/lex-machina.page) | None — counts, not predictions | Not a prediction competitor. Practitioner verdict: "only good for federal analytics." |
| **Westlaw Precision Litigation Analytics** | ~8M federal + 150M state dockets | Judge/firm dashboards in Westlaw tiers | 28 motion types (https://legal.thomsonreuters.com/en/insights/articles/westlaw-edge-litigation-analytics) | All firm sizes, bundled | None | Bundled descriptive layer; users report data-quality confusion. |
| **Lexis+ Context** | Federal + state trial judges; appellate all 50 states | Grant/partial/deny rates + citation-language analytics | 100 motion types (https://supportcenter.lexisnexis.com/app/answers/answer_view/a_id/1100336/~/using-judge-profiles-in-context-judge-analytics) | Bundled into Lexis+ | None | Its motion taxonomy is a useful reference standard; no predictions. |
| **Trellis** | 45 states, 3,000+ courts; documents far narrower (https://support.trellis.law/coverage-1) | State docket data + judge analytics + Trellis AI | Grant/denial rates by motion type incl. MSJ, discovery | Insurers, corporates, funders; $69.95–199.95/mo | None | The state incumbent, with documented reliability complaints and churn to "go directly to the court." Its moat (CA tentatives archive) is the one asset we should start replicating prospectively. |
| **Docket Alarm** | PACER + ~40 state systems, 950M+ docs | Build-your-own analytics workbench, $99/user/mo | Custom | DIY firms | None | Cheap federal data supply for our pipeline, not a rival product. |
| **Gavelytics (dead 2022)** | 10 state courts | State judge analytics subscription | Various | Big firms, insurers | None | The state-first post-mortem: coverage cost outran revenue while incumbents bundled. Per-motion pricing avoids its subscription trap, but its death still caps state enthusiasm. |
| **Viewpoints AI** | Jury simulation only | Verdict/damages simulation | Trial-stage | AmLaw 100, top-10 insurers | Published live head-to-head vs mock jury (https://viewpoints.ai/jury-sim) | Not a competitor, but the strongest validation methodology in the space — a template for our study design. |

## 3. Motion-type coverage recommendation

Start narrow. Two motion types, then two more:

1. **Motion to dismiss (12(b)(6)) — first.** Cleanest labels, highest volume, and the type where the incumbent's 85% claim lives (https://www.lawnext.com/startup-alley-pre-dicta). Beating or honestly bounding a pre-registered MTD number is the fastest way to make the unaudited claims look bad.
2. **Summary judgment — second.** The other dispositive motion; decides case value for funders and insurers; well-labeled in SDNY/EDNY written opinions.
3. **Class certification — third.** SDNY securities concentration makes it high-stakes (2nd+9th Circuits = 61% of securities filings, record $17.3M median settlement — https://www.cornerstone.com/insights/press-releases/median-securities-settlement-amount-record-high/), and it is a funder-diligence trigger.
4. **Daubert — fourth.** High leverage in the same commercial/securities book.

Do not chase Pre/Dicta's full 10-module spread (TRO, remand, transfer, compel, JOP). Those are either low-stakes relative to a $2.5–7.5K report or hard to score cleanly, and breadth dilutes the ledger. Use Lexis Context's 100-type taxonomy and Westlaw's 28 types as naming references so our categories are legible to buyers, but validate on four.

## 4. State-data map: what is feasible today

Free or near-free, judge-level rulings corpora assemblable now:

| Venue | Access | Cost | Note |
|---|---|---|---|
| **NY Supreme Ct incl. ComDiv** | NYSCEF guest search: full dockets + PDFs of every e-filed decision/order, statewide (https://iapps.courts.state.ny.us/nyscef/CaseSearch) | $0 | Best free venue in the country; highest-value commercial docket outside Delaware |
| **Delaware Chancery** | All opinions/orders free (https://courts.delaware.gov/opinions/index.aspx?ag=court+of+chancery) | $0 | Maximum prestige, but ~7 jurists = too thin-N for a per-judge accuracy ledger. Marketing flag, not scoreboard. |
| **NC Business Court** | Every opinion since 1996 free | $0 | Complete archive, small N |
| **Minnesota (MCRO)** | Free statewide document downloads, all 87 counties, ~2015+ | $0 | Best free bulk corpus; low commercial stakes |
| **Oklahoma (OSCN)** | Free dockets + scanned order images in OK/Tulsa counties | $0 | |
| **New Jersey eCourts** | Free case jackets incl. signed orders, registration only | $0 | |
| **Indiana (mycase)** | Free, partial order availability | $0 | |
| **Texas (re:SearchTX)** | Non-party docs 10¢/page, $6/doc cap | Low single-digit $k for 20–30K orders | Cheapest paid volume pull |
| **California** | Tentative rulings free in ~25 counties but ephemeral; filed orders at scale cost six figures (LA: $1/page first 5 + $0.40/page) | Free prospectively, unbuyable retroactively | Value accrues only to whoever scrapes daily — Trellis's original moat |
| **Cook County, GA, PA, MA, VA, MD** | Documents offline or per-county paywalled | Effectively closed | WI CCAP docket text is the best fallback for inference only |

**Single best chapter-2 state venue: NY Commercial Division.** Same city, same firms, same clients as the current SDNY/EDNY book. Manhattan $500K floor, tightened Jan 2025 to concentrate high-value commercial cases (https://www.schlamstone.com/blogs/commercial/2025-02-05-commercial-division-rules-amended-to-require-suits-seeking-equitable-or-declaratory-relief-to-meet-monetary-threshold). ComDiv justices write and post decisions — dense per-judge text for replicas. And the scoreboard mechanic improves: any skeptical partner can free-click verify outcomes on NYSCEF, versus PACER's paywall. Zero prediction competitors there today.

## 5. Three moves this implies — without touching this week's frozen YC/exam plan

1. **Start the California tentative-rulings archiver now.** A daily scraper over the ~25 posting counties, dumped to storage. It is the only state asset that compounds purely with elapsed time and cannot be backfilled (https://support.trellis.law/coverage-1 for why this is Trellis's moat). It changes nothing about the wedge, the pitch, or this week's plan. Hours of work, then it runs.
2. **Begin silent NYSCEF ingestion of ComDiv decisions and orders.** Zero-marginal-cost background collection (https://iapps.courts.state.ny.us/nyscef/CaseSearch) so the ComDiv annex is data-ready the moment the federal ledger has enough entries to show. No positioning change, no product change now.
3. **Sharpen the pre-registration to name the gap it fills.** The repo's validation protocol should state explicitly that the category's only accuracy numbers (Pre/Dicta's 85%, Courtroom's >90%) are vendor backtests with no third-party audit, and commit publicly to MTD + MSJ scoring rules, taxonomy, and forward test windows before results exist. Viewpoints AI's published live head-to-head (https://viewpoints.ai/jury-sim) is the methodological bar to meet or beat. This is a writing task against the existing repo, not a strategy change.

**One-line summary:** the wedge stays federal because the scoreboard and the proven wallet are federal; NY ComDiv is the annex, not the pivot; Delaware is a flag, not a ledger; and the only urgent state action is a cheap scraper whose value is a function of start date.
