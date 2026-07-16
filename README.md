# Gatekeeper — Kill Experiment

Can litigation teams rehearse against an AI replica of their assigned judge?
Before selling anything, this repo answers the prior question: **is a
rulings-grounded replica of a named judge measurably better than a generic
judge model — on rulings the model cannot have memorized?**

Protocol: [PREREGISTRATION.md](PREREGISTRATION.md) (frozen + hashed before scoring).
Parameters: [config.yaml](config.yaml). Verdict due: **2026-07-22**.

## Pipeline

```
1. python3 pipeline/ingest.py            # CourtListener RECAP pull (both judges)
   python3 pipeline/ingest.py --description order   # second pass for label volume
2. python3 pipeline/label.py             # deterministic outcome labels + review pool
   (LLM extractor + 20% hand-verify pass close the review pool)
3. python3 pipeline/split.py <cutoff>    # grounding vs exam by model cutoff date
4. python3 pipeline/arms.py              # four arms (needs ANTHROPIC_API_KEY + pinned model)
5. python3 pipeline/score.py             # ONE run, verdict day only
```

## The wall

The exam set contains only outcomes decided AFTER the pinned model's training
cutoff. Random holdouts are banned — frontier models pretrained on the public
court record have already read them. Arm (c), name-only, exists to prove it.

## Status

- [x] Smoke test passed 2026-07-14: Liman 808 / Furman 716 docket documents
      confirmed live; labeler yields ~15% clean labels on sample.
- [ ] CourtListener Tier-2 token ($25) — full pull
- [ ] Exam model pinned (name + published cutoff) in config + PREREGISTRATION
- [ ] Full ingest (opinion + order passes) → labels → hand-verify audit
- [ ] Pre-registration frozen: SHA-256 published publicly BEFORE scoring
- [ ] Leakage audit → arms → score → verdict (Jul 22)
