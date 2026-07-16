#!/usr/bin/env python3
"""Arm (e): the RSI persona loop — the founding hypothesis.

Per judge: draft a persona document from the judge's pre-cutoff rulings,
predict a held-out validation slice of PRE-cutoff rulings with the persona
alone, study the mistakes, revise the persona, repeat until plateau.
The best persona is frozen and sits the exam exactly once (via arms.py).

HARD RULE: this loop never touches post-cutoff (exam) data. Ever.

Usage: python3 pipeline/persona_loop.py            # needs data/grounding.jsonl
Output: data/persona_{judge}.md + data/persona_history.jsonl
"""
from __future__ import annotations
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import arms  # frozen model access + input construction

VALIDATION_SLICE = 0.25
MAX_ITER = 12
PLATEAU_STOP = 3
SEED = 42

DRAFT_PROMPT = """You are building a decision-profile ("persona") of a real US federal
district judge from their actual rulings. Study the rulings below and write a persona
document (max 700 words) describing HOW this judge decides contested motions:
tendencies per motion type (dismiss, summary judgment, compel, injunctions, class cert),
procedural strictness, what arguments move them, base rates you observe.
Be concrete and predictive, not flattering. Write only the persona document."""

REVISE_PROMPT = """Below is your current persona document for this judge, followed by
prediction MISTAKES it just made on real held-out rulings (it predicted wrong).
Revise the persona to fix the SYSTEMATIC errors you see (wrong base rates, missed
tendencies, over/under-confidence on a motion type). Keep what works. Max 700 words.
Write only the revised persona document."""


def predict_with_persona(persona: str, judge: str, item: dict) -> str:
    return arms.call_model(
        arms.SYSTEM_BASE + f"\nYou are predicting Judge {judge}, SDNY.\n"
        f"Decision profile of this judge, learned from their rulings:\n{persona}",
        arms.build_inputs(item))


def evaluate(persona: str, judge: str, items: list) -> tuple[float, list]:
    mistakes = []
    correct = 0
    for it in items:
        pred = predict_with_persona(persona, judge, it)
        if pred == it["label"]:
            correct += 1
        else:
            mistakes.append((it, pred))
    return correct / max(len(items), 1), mistakes


def rulings_digest(items: list, cap: int = 60) -> str:
    rng = random.Random(SEED)
    sample = rng.sample(items, min(cap, len(items)))
    return "\n".join(f"- {i['date']} {i['motion_type']}: outcome={i['label']} | "
                     f"{arms.strip_outcome_language(i['description'])[:180]}"
                     for i in sample)


def run_judge(judge: str, grounding: list, log) -> None:
    items = [g for g in grounding if g["judge"] == judge]
    rng = random.Random(SEED)
    rng.shuffle(items)
    n_val = max(10, round(len(items) * VALIDATION_SLICE))
    val, train = items[:n_val], items[n_val:]
    print(f"[{judge}] grounding={len(items)} train={len(train)} val={len(val)}")

    persona = arms.call_model_long(DRAFT_PROMPT, rulings_digest(train))
    best_acc, best_persona, since_best = -1.0, persona, 0
    for it in range(1, MAX_ITER + 1):
        acc, mistakes = evaluate(persona, judge, val)
        log.write(json.dumps({"judge": judge, "iter": it, "acc": round(acc, 4),
                              "mistakes": len(mistakes)}) + "\n")
        log.flush()
        print(f"[{judge}] iter {it}: val acc {acc*100:.1f}% ({len(mistakes)} mistakes)")
        if acc > best_acc:
            best_acc, best_persona, since_best = acc, persona, 0
        else:
            since_best += 1
            if since_best >= PLATEAU_STOP:
                print(f"[{judge}] plateau — stopping")
                break
        if it == MAX_ITER or not mistakes:
            break
        mistakes_txt = "\n".join(
            f"- {m[0]['date']} {m[0]['motion_type']}: predicted {m[1]}, actual "
            f"{m[0]['label']} | {arms.strip_outcome_language(m[0]['description'])[:160]}"
            for m in mistakes[:25])
        persona = arms.call_model_long(
            REVISE_PROMPT, f"CURRENT PERSONA:\n{persona}\n\nMISTAKES:\n{mistakes_txt}")

    with open(f"data/persona_{judge.lower()}.md", "w", encoding="utf-8") as f:
        f.write(best_persona)
    print(f"[{judge}] FROZEN persona at val acc {best_acc*100:.1f}% -> "
          f"data/persona_{judge.lower()}.md")


def main() -> None:
    grounding = [json.loads(l) for l in open("data/grounding.jsonl", encoding="utf-8")]
    judges = sorted({g["judge"] for g in grounding})
    with open("data/persona_history.jsonl", "a", encoding="utf-8") as log:
        for j in judges:
            run_judge(j, grounding, log)


if __name__ == "__main__":
    main()
