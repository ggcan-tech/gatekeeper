#!/usr/bin/env python3
"""Run the four pre-registered arms over the exam set.

Arms (PREREGISTRATION.md — one frozen model, same decoding params, all arms):
  a) majority   — majority class per motion type, computed on GROUNDING set only
  b) metadata   — model + judge biography/appointment data, NO rulings
  c) name_only  — model + judge name only, NO rulings (memorization detector)
  d) replica    — model + retrieved pre-cutoff rulings of this judge

Model access via env ANTHROPIC_API_KEY (provider-agnostic seam in call_model).
Usage: python3 pipeline/arms.py            # requires data/exam.jsonl + grounding.jsonl
Output: data/predictions.jsonl (input to score.py)
"""
from __future__ import annotations
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

MODEL_ID = os.environ.get("EXAM_MODEL_ID", "gpt-5.4-2026-03-05")  # frozen pin (config.yaml)
REASONING_EFFORT = "none"                                          # frozen decoding param

SYSTEM_BASE = (
    "You predict the outcome of a contested motion before a US federal district "
    "judge. Answer with exactly one character: Y (relief substantially granted) "
    "or N (denied). No explanation."
)

BIO = {
    # metadata arm inputs — public biographical/appointment data only, no rulings.
    "Liman": "Judge Lewis J. Liman, SDNY. Appointed 2019 (Trump). Yale Law. "
             "Former Cleary Gottlieb partner, SDNY AUSA.",
    "Furman": "Judge Jesse M. Furman, SDNY. Appointed 2012 (Obama). Yale Law. "
              "Former SDNY AUSA, DOJ counsel.",
    "Subramanian": "Judge Arun Subramanian, SDNY. Appointed 2023 (Biden). "
                   "Columbia Law. Former Susman Godfrey partner.",
}


def _openai_key() -> str:
    key = os.environ.get("OPENAI_API_KEY")
    if key:
        return key
    here = os.path.dirname(os.path.abspath(__file__))
    for p in (os.path.join(here, "..", "openai_key.txt"), "openai_key.txt"):
        try:
            with open(p, encoding="utf-8") as f:
                t = f.read().strip()
            if t.startswith("sk-"):
                return t
        except OSError:
            continue
    sys.exit("REFUSING TO RUN: no OpenAI key (env OPENAI_API_KEY or openai_key.txt).")


def _post_chat(body: dict) -> dict:
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {_openai_key()}",
                 "content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.load(r)


def call_model(system: str, user: str) -> str:
    body = {
        "model": MODEL_ID,
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user}],
        "max_completion_tokens": 16,
        "reasoning_effort": REASONING_EFFORT,
    }
    try:
        data = _post_chat(body)
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:300]
        # graceful degrade if this snapshot rejects a param name
        if e.code == 400 and "reasoning_effort" in detail:
            body.pop("reasoning_effort", None)
            data = _post_chat(body)
        elif e.code == 400 and "max_completion_tokens" in detail:
            body["max_tokens"] = body.pop("max_completion_tokens")
            data = _post_chat(body)
        else:
            raise
    text = (data["choices"][0]["message"]["content"] or "").strip().upper()
    return "Y" if text.startswith("Y") else "N"


def call_model_long(system: str, user: str) -> str:
    """Free-text variant for persona drafting/revision (not exam predictions)."""
    body = {
        "model": MODEL_ID,
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user}],
        "max_completion_tokens": 1200,
        "reasoning_effort": "low",
    }
    try:
        data = _post_chat(body)
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:300]
        if e.code == 400 and "reasoning_effort" in detail:
            body.pop("reasoning_effort", None)
            data = _post_chat(body)
        else:
            raise
    return (data["choices"][0]["message"]["content"] or "").strip()


def strip_outcome_language(desc: str) -> str:
    """Input construction: remove grant/deny words so the item doesn't leak its answer."""
    return re.sub(r"\b(grant\w*|den(y|ies|ied|ying)|in part)\b", "[RULING]", desc, flags=re.I)


def build_inputs(item: dict) -> str:
    return (f"Court: SDNY. Motion type: {item['motion_type']}. "
            f"Docket entry (pre-ruling text): {strip_outcome_language(item['description'])}\n"
            f"Predict: Y or N.")


def retrieve(grounding: list[dict], item: dict, k: int = 8) -> str:
    """Replica arm retrieval v1: same-judge, same-motion-type recent rulings.
    Upgrade path: BM25/embeddings over full opinion texts."""
    pool = [g for g in grounding
            if g["judge"] == item["judge"] and g["motion_type"] == item["motion_type"]]
    pool.sort(key=lambda g: g.get("date") or "", reverse=True)
    lines = [f"- {g['date']} {g['motion_type']}: outcome={g['label']} | "
             f"{strip_outcome_language(g['description'])[:200]}" for g in pool[:k]]
    return "\n".join(lines) if lines else "(no prior rulings of this type)"


def load_personas(judges: set) -> dict:
    personas = {}
    for j in judges:
        p = f"data/persona_{j.lower()}.md"
        if not os.path.exists(p):
            sys.exit(f"REFUSING TO RUN: {p} missing — run pipeline/persona_loop.py "
                     "first (arm (e) requires frozen personas).")
        personas[j] = open(p, encoding="utf-8").read()
    return personas


def main() -> None:
    exam = [json.loads(l) for l in open("data/exam.jsonl", encoding="utf-8")]
    grounding = [json.loads(l) for l in open("data/grounding.jsonl", encoding="utf-8")]
    personas = load_personas({e["judge"] for e in exam})

    # arm (a): majority per motion type from GROUNDING only (frozen reference corpus)
    counts: dict[str, dict[str, int]] = {}
    for g in grounding:
        counts.setdefault(g["motion_type"], {"Y": 0, "N": 0})[g["label"]] += 1
    majority = {mt: ("Y" if c["Y"] >= c["N"] else "N") for mt, c in counts.items()}

    out = open("data/predictions.jsonl", "w", encoding="utf-8")
    for i, item in enumerate(exam):
        base_input = build_inputs(item)
        judge = item["judge"]
        row = {
            "id": item["id"], "label": item["label"], "judge": judge,
            "motion_type": item["motion_type"],
            "majority": majority.get(item["motion_type"], "N"),
            "metadata": call_model(
                SYSTEM_BASE + f"\nJudge profile: {BIO.get(judge, judge)}", base_input),
            "name_only": call_model(
                SYSTEM_BASE + f"\nYou are predicting Judge {judge}, SDNY.", base_input),
            "retrieval": call_model(
                SYSTEM_BASE + f"\nYou are predicting Judge {judge}, SDNY.\n"
                f"This judge's actual recent rulings on this motion type:\n"
                f"{retrieve(grounding, item)}", base_input),
            "rsi_persona": call_model(
                SYSTEM_BASE + f"\nYou are predicting Judge {judge}, SDNY.\n"
                f"Decision profile of this judge, learned from their rulings:\n"
                f"{personas[judge]}", base_input),
        }
        out.write(json.dumps(row) + "\n")
        if i % 10 == 0:
            print(f"{i}/{len(exam)}", file=sys.stderr)
        time.sleep(0.3)
    out.close()
    print(f"done: {len(exam)} items -> data/predictions.jsonl")


if __name__ == "__main__":
    main()
