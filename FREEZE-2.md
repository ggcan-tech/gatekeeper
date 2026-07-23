# FREEZE MANIFEST #2 — Exam #2A (Ultimate Evidence Program)

Frozen: 2026-07-23 12:16 +03, BEFORE any exam arm ran on the exam set (data/exam2.jsonl).
Examinee models: gpt-5.4-2026-03-05 (full window) + claude-fable-5 (sub-window > the pinned Fable cutoff; pin recorded at sitting in data/fable_pin.json).

Exam n = 834. Estimation exam — no win/lose verdict on Track A.

## Pre-freeze gate results (frozen with this manifest)

- Leakage audit: **PASS — blinded arm does not beat majority+3** (blinded 75.3% vs majority 75.42%, margin -0.12 pts, one-sided p=0.9274; fail iff p<.05 that blinded > majority+3).
- Ensemble arm (g) val gate: **arm_g PRIMARY (ensemble >= best single arm on held-out pre-cutoff val)** (held-out pre-cutoff val n=479: ensemble 87.47% vs best single L4 87.27%, Δ=0.2 pts).

## Reproducibility pins

- Persona loop: SEED=42, VALIDATION_SLICE=0.25; pool personas MAX_VAL=60 (prereg C4). Per-judge subsample caps were inert (no judge exceeded the 120 cap after filtering).
- All 15 judge personas + 2 court-pool personas built on the SAME final grounding snapshot (grounding2.jsonl), post attribution-filter (prereg C3).

## SHA-256 fingerprints (any post-hoc change to these voids the exam)

```
cd79fa6dee248ff4c5df65a9502609c1875b375e828dc637949df3af6db4d303  PREREGISTRATION-2.md
4538d79cdefaf25378106f2e03e9c0598df2b1f8daf379b7bbfa0acb71f7d5b7  config.yaml
956d774321070bf9759c405e9c68e0321781ef94aa79df94c124b56a6f3f2823  data/exam2.jsonl
79ecd3a46beb0e5de07497ac3744f364557315cb0f374bc18efe7d520c7f2333  data/grounding2.jsonl
912095d8f4f580a05b079c939190eae2fd24c7378336942724f78584e4beccd2  data/persona2_broderick.md
70d352bac4f993fb06f43bc48fc16617e24bb8d91696a3edbd04915ca49576df  data/persona2_carter.md
fdd59b3acaabe54bd6251ff9c6926aeed1b1b5216c8b3a14137bd4c2336c4979  data/persona2_cogan.md
a7d99bc7c44ab3031270032d6a964e0e7be9d64df8fb75648c2ef72f53ab85eb  data/persona2_daniels.md
298919eea2c9495447f4c57e07ed9c3a528c85f4f339a7982b09c17828ec5177  data/persona2_donnelly.md
7f1428a692788d447780edf511fba8db0c4aba7d2299479c8e301c4f79701d42  data/persona2_engelmayer.md
ad1a728c8a174a815545cf7373e01f40fee377581cee8a8049b6217fb24f0bd3  data/persona2_garnett.md
b6dc11d9d07dada08376fc51e008efdcf536c87fefe107ffbe9d23edf531e9fd  data/persona2_ho.md
d9ce5791c64d53b707df841d44d047f0770364a78f7582debba3f92bbaeaee3f  data/persona2_koeltl.md
e46daa17a9c058f8060f47aaab3747c9234e77af2ca05298a4413de805620eeb  data/persona2_morrison.md
9550e017e41efee9cabf503aae2ff191bf4c024a764aa121d90b9b4fa73a3c8d  data/persona2_rochon.md
211bca6193553eb30a08c582431691dc8eef7fdf1cee029ce99dc959c24192f5  data/persona2_stein.md
092ec85ccc8382d0a66b24d16b848c18f4e58e2c27819e6767c667707e397c9b  data/persona2_torres.md
7915d342f99847bebd4bc66dcd1933a5507dc687bd4a7e70ef0471e7570eecd8  data/persona2_vargas.md
569cfa1c3bcf884d098e369a3fbd9f5148afc0132d42621f80ddf61726e283c3  data/persona2_woods.md
0f0940d48aac2d6fefd13a49ceeba878a6802da0ae0ab02e4783a69b660e359d  data/persona2_sdny_pool.md
ba568b4213ca34261ad553477164b4d0b6fcf30a4049a1d8f42c9dbc57b59bea  data/persona2_edny_pool.md
11802d7a644ab6a14ef3cf521f65548e09984a286e4289af96d2dd002e5f76eb  data/persona2_fictional.md
00f1c8e125d57f8b7bb2ea70ad3344e2e6ffff98c3aaff5daf83ba1bf8b6cd03  data/doctrine_primers.json
f9417696f6d25156c4fd73d0af0425f5cacf094db796b79cc1fe8b6ae9988491  data/derangement_map.json
905cd25fd8292a5b57e977aae7980d177090a5b4dcac7d6db9d7bf358be0681b  data/bios2.json
94b1ec2510b897a69247c4d35e3bd84fc8e91849cb37ea65f25f443e27d01927  data/arm_extras.json
ae3869c47d268cd10c7e9e337d4a55b41b31ecf0f400590d4cc5d07109d0a59f  data/audit2_pass1.json
727d54778aa0d1b6adf28b7f985f01be14181c09429184734a47217dc44404f6  data/audit2_pass2.json
38ce06d948f98725ba9bf42913b1ff20414722ea56199524f438db08760cceba  data/ensemble_gate2.json
4446858f8d4a163771bac6a9c2332bba457875f8949137289eba7d93ab2bb8b0  data/leakage_audit2.json
ccf976f680219f4ec97125dcb9531756a48d3fd6f0f77fe9010e83f01cbc1287  pipeline/arms2.py
993703816452600f5bee6750eb4960bf71d870abc2b2c2171a39684d7559fb29  pipeline/label2.py
5069097cee92417ab4efbaf66e49d3df63c33447f2ae3a8050ce78a12ca011ca  pipeline/score2.py
32d452b0a338dfcad418ba350b7552ce4f21655cb6b0cfea7f6cf54121b17078  pipeline/persona_loop.py
502ec955b476f5180b0e4f13941927fa61542090fb5b6b1774d6e10a82928c5f  pipeline/ensemble_gate2.py
a1f82ad7706acc308ed4733a1531bb79e75a61c8922dd24a987071613ee75b03  pipeline/leakage_audit2.py
```

Persona / grounding / bios / doctrine / derangement documents may be withheld as product IP; the hashes above bind them. arms2.py imports the frozen exam-1 arms.py (itself hashed in FREEZE.md) and never edits it.
