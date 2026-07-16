#!/usr/bin/env python3
"""Generate the blind hand-verification sample (frozen: 20% of exam set,
min 40, plus 20 grounding spot-checks; >=95% agreement required).

Blindness: the checker sees docket text only. Machine labels go to the
answer key, compared only after the human answers are in.

Usage: python3 pipeline/hand_verify.py
Output: data/hand_check_items.json (blind), data/hand_check_key.json (labels)
"""
from __future__ import annotations
import json
import random

CUTOFF = "2025-08-31"
SEED = 42  # fixed + documented for reproducibility


def main() -> None:
    rows = [json.loads(l) for l in open("data/labeled.jsonl", encoding="utf-8")]
    exam = [r for r in rows if (r.get("date") or "") > CUTOFF]
    grounding = [r for r in rows if (r.get("date") or "") <= CUTOFF]
    rng = random.Random(SEED)
    n_exam = max(40, round(0.20 * len(exam)))
    sample = rng.sample(exam, n_exam) + rng.sample(grounding, min(20, len(grounding)))
    rng.shuffle(sample)

    items, key = [], []
    for i, r in enumerate(sample, 1):
        items.append({"n": i, "date": r.get("date"), "judge": r["judge"],
                      "text": r["description"]})
        key.append({"n": i, "id": r["id"], "label": r["label"],
                    "source": r.get("label_source", "rules"),
                    "set": "exam" if (r.get("date") or "") > CUTOFF else "grounding"})
    json.dump(items, open("data/hand_check_items.json", "w"), indent=1)
    json.dump(key, open("data/hand_check_key.json", "w"), indent=1)
    print(f"sample: {len(items)} items ({n_exam} exam + {len(sample)-n_exam} grounding)")


if __name__ == "__main__":
    main()
