#!/usr/bin/env python3
"""Exam #2A sitting runner — PREREGISTRATION-2.md Track A.

Arms (each differs ONLY in persona/grounding input; estimation exam, no verdict):
  (a) majority   — majority class per motion type, PRE-cutoff pooled grounding2
  (b) metadata   — judge biography/appointment data (data/bios2.json), NO rulings
  (c) name_only  — judge name + court only (memorization detector)
  L0  generic    — no court, no judge, no identity; motion facts only
  L1  court_name — "You are a judge of the {SDNY|EDNY}", no data
  L2  court_pool — persona from POOLED court rulings (persona2_{sdny,edny}_pool.md)
  L3  retrieval  — exam-1 arm (d): retrieval over the named judge's grounding2 rows
  L4  persona    — exam-1 arm (e): RSI persona (persona2_{judge}.md); Vargas: SKIP
  (g) ensemble   — majority{L2,L3,L4}; computed at pivot ONLY if frozen pre-sitting
                   (data/armg_frozen.json present = the val gate passed and was logged)

Examinee models (dual-model attribution, own controls each):
  gpt   gpt-5.4-2026-03-05 via frozen arms.py client — full window, n=834
  fable claude-fable-5 via Anthropic REST — items dated > FABLE_CUTOFF only,
        controls (b),(c) re-run on that sub-window; refusal => "X" (abstain=wrong)

DISCIPLINE, ENFORCED IN CODE:
  - Refuses to run on data/exam2.jsonl unless FREEZE-2.md exists (freeze before scoring).
  - SMOKE=1 runs the full plumbing on 4 PRE-cutoff grounding rows instead (never exam).
  - imports exam-1's freeze-hashed arms.py; NEVER edits it.
  - never run concurrently with any other OpenAI consumer (429 storm).

Resume: every (model,arm,id) answer is appended to data/answers2.jsonl immediately;
re-running skips completed calls. ~8.8K model calls total.

Usage:  cd gatekeeper && python3 -u pipeline/arms2.py          # the sitting
        SMOKE=1 python3 -u pipeline/arms2.py                   # plumbing test
Output: data/answers2.jsonl (cache) -> data/predictions2.jsonl (pivoted, for score2.py)
"""
from __future__ import annotations
import json
import os
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import arms  # frozen exam-1 module: GPT client, input hygiene. READ ONLY.

SMOKE = os.environ.get("SMOKE") == "1"
MODEL_FILTER = os.environ.get("MODEL_FILTER", "")  # "gpt"|"fable" -> run one model only;
# the two providers may run CONCURRENTLY (separate processes, separate cache files);
# after both finish, run once with no filter for the merged pivot (all calls cached).
FABLE_MODEL = os.environ.get("FABLE_MODEL_ID", "claude-fable-5")
FABLE_CUTOFF = os.environ.get("FABLE_CUTOFF", "2026-01-31")  # verify at freeze (prereg)
FABLE_MAX_TOKENS = 2048          # thinking always-on: headroom, parse final Y/N
if SMOKE:
    CACHE_PATH = "data/answers2_smoke.jsonl"
elif MODEL_FILTER:
    CACHE_PATH = f"data/answers2_{MODEL_FILTER}.jsonl"
else:
    CACHE_PATH = "data/answers2.jsonl"
OUT_PATH = "data/predictions2_smoke.jsonl" if SMOKE else "data/predictions2.jsonl"
MODEL_ARMS = ["metadata", "name_only", "L0", "L1", "L2", "L3", "L4"]
# Amendment arms (L4X derangement / L4F fictional): scored ONLY if registered —
# data/arm_extras.json is created at freeze time iff the signed amendment covers them,
# and is hashed in FREEZE-2 alongside derangement_map.json / persona2_fictional.md.
if os.path.exists("data/arm_extras.json"):
    _extras = json.load(open("data/arm_extras.json", encoding="utf-8"))
    MODEL_ARMS += [a for a in ("L4X", "L4F", "D0", "L4D") if _extras.get(a)]


def _load_json(path: str):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _load_jsonl(path: str) -> list[dict]:
    return [json.loads(l) for l in open(path, encoding="utf-8")]


COURT = {r["judge"]: ("EDNY" if r["court"] == "nyed" else "SDNY")
         for r in _load_json("data/judges2.json")["selected"]}
def _no_persona_judges() -> set:
    """L4-eligibility is MECHANICAL: a judge gets L4/L4X/L4D iff a frozen persona
    file exists for them at freeze time. Hardcoding was wrong — the initial
    'Vargas has zero grounding' disclosure predated the completion of her pull
    (logged as a pre-freeze correction in PREREGISTRATION-2.md)."""
    out = set()
    for j in COURT:
        if not os.path.exists(f"data/persona2_{j.lower()}.md"):
            out.add(j)
    return out


NO_PERSONA_JUDGES = _no_persona_judges()   # judges with no frozen persona -> L0-L3 only


def _anthropic_key() -> str:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        return key
    for p in ("anthropic_key.txt", os.path.join("..", "anthropic_key.txt")):
        try:
            t = open(p, encoding="utf-8").read().strip()
            if t:
                return t
        except OSError:
            continue
    sys.exit("REFUSING TO RUN: no Anthropic key (env ANTHROPIC_API_KEY or "
             "anthropic_key.txt). The Fable arm is pre-registered; get the key from Can.")


def call_fable(system: str, user: str) -> str:
    """One exam answer from claude-fable-5. Y/N, or X on refusal/unparseable."""
    body = {
        "model": FABLE_MODEL,
        "max_tokens": FABLE_MAX_TOKENS,
        "system": system,
        "messages": [{"role": "user", "content": user}],
        "effort": "low",
    }
    for attempt in range(6):
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=json.dumps(body).encode(),
            headers={"x-api-key": _anthropic_key(),
                     "anthropic-version": "2023-06-01",
                     "content-type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                data = json.load(r)
            break
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")[:400]
            if e.code == 400 and "effort" in detail and "effort" in body:
                body.pop("effort")            # graceful degrade, mirror arms.py pattern
                continue
            if e.code in (429, 500, 502, 503, 529):
                if "credit" in detail or "billing" in detail:
                    sys.exit(f"ANTHROPIC OUT OF CREDITS (not a rate limit): {detail}")
                wait = float(e.headers.get("retry-after") or min(60, 2 ** attempt * 5))
                print(f"  fable {e.code}, retry in {wait:.0f}s", file=sys.stderr)
                time.sleep(wait)
                continue
            raise
        except (urllib.error.URLError, TimeoutError):
            time.sleep(min(60, 2 ** attempt * 5))
            continue
    else:
        return "X"
    # pin disclosure: record the response-model string the first time we see it
    _pin_response_model(data.get("model", ""))
    if data.get("stop_reason") == "refusal":
        return "X"                            # abstain scores as wrong (prereg)
    text = ""
    for block in data.get("content", []):
        if block.get("type") == "text":
            text = block.get("text", "")      # last text block wins
    text = text.strip().upper()
    for ch in text:
        if ch in ("Y", "N"):
            return ch
    return "X"


_PIN_DONE = False


def _pin_response_model(model_str: str) -> None:
    """Fable has no dated snapshot: pin = alias + response.model + sitting date."""
    global _PIN_DONE
    if _PIN_DONE or not model_str or SMOKE:
        return
    _PIN_DONE = True
    with open("data/fable_pin.json", "w", encoding="utf-8") as f:
        json.dump({"alias": FABLE_MODEL, "response_model": model_str,
                   "sitting_date": time.strftime("%Y-%m-%d"),
                   "fable_cutoff_used": FABLE_CUTOFF}, f, indent=1)


def base_input(item: dict, include_court: bool) -> str:
    court_part = f"Court: {COURT.get(item['judge'], 'SDNY')}. " if include_court else ""
    return (f"{court_part}Motion type: {item['motion_type']}. "
            f"Docket entry (pre-ruling text): "
            f"{arms.strip_outcome_language(item['description'])}\n"
            f"Predict: Y or N.")


def retrieve2(grounding: list[dict], item: dict, k: int = 8) -> str:
    """L3 — mirrors frozen arms.retrieve over grounding2."""
    pool = [g for g in grounding
            if g["judge"] == item["judge"] and g["motion_type"] == item["motion_type"]]
    pool.sort(key=lambda g: g.get("date") or "", reverse=True)
    lines = [f"- {g['date']} {g['motion_type']}: outcome={g['label']} | "
             f"{arms.strip_outcome_language(g['description'])[:200]}" for g in pool[:k]]
    return "\n".join(lines) if lines else "(no prior rulings of this type)"


def build_arm_prompt(arm: str, item: dict, ctx: dict) -> tuple[str, str]:
    """-> (system, user) for a model arm."""
    judge = item["judge"]
    court = COURT.get(judge, "SDNY")
    S = arms.SYSTEM_BASE
    if arm == "L0":
        return S, base_input(item, include_court=False)
    user = base_input(item, include_court=True)
    if arm == "metadata":
        return S + f"\nJudge profile: {ctx['bios'][judge]}", user
    if arm == "name_only":
        return S + f"\nYou are predicting Judge {judge}, {court}.", user
    if arm == "L1":
        return S + f"\nYou are a judge of the {court}.", user
    if arm == "L2":
        pool = ctx["pool_personas"][court]
        return (S + f"\nYou are a judge of the {court}.\nDecision profile of this "
                f"court's bench, learned from its rulings:\n{pool}"), user
    if arm == "L3":
        return (S + f"\nYou are predicting Judge {judge}, {court}.\nThis judge's "
                f"actual recent rulings on this motion type:\n"
                f"{retrieve2(ctx['grounding'], item)}"), user
    if arm == "L4":
        return (S + f"\nYou are predicting Judge {judge}, {court}.\nDecision profile "
                f"of this judge, learned from their rulings:\n"
                f"{ctx['personas'][judge]}"), user
    if arm == "L4X":  # derangement placebo: another same-court judge's real persona
        other = ctx["derangement"][judge]
        return (S + f"\nYou are predicting Judge {judge}, {court}.\nDecision profile "
                f"of this judge, learned from their rulings:\n"
                f"{ctx['personas'][other]}"), user
    if arm == "L4F":  # fictional-persona control: persona-shaped text, no data behind it
        return (S + f"\nYou are predicting Judge {judge}, {court}.\nDecision profile "
                f"of this judge, learned from their rulings:\n"
                f"{ctx['fictional']}"), user
    if arm == "D0":   # doctrine-only: structured general legal knowledge, no identity
        return (S + f"\nControlling legal standard for this motion type:\n"
                f"{ctx['doctrine'][item['motion_type']]}"), \
            base_input(item, include_court=False)
    if arm == "L4D":  # persona + doctrine: the founder's knowledge-armed persona arm
        return (S + f"\nYou are predicting Judge {judge}, {court}.\nControlling legal "
                f"standard for this motion type:\n{ctx['doctrine'][item['motion_type']]}\n"
                f"Decision profile of this judge, learned from their rulings:\n"
                f"{ctx['personas'][judge]}"), user
    raise ValueError(arm)


def load_context(exam: list[dict]) -> dict:
    grounding = _load_jsonl("data/grounding2.jsonl")
    bios = _load_json("data/bios2.json")
    judges = sorted({e["judge"] for e in exam})
    missing = [j for j in judges if j not in bios]
    if missing:
        sys.exit(f"REFUSING TO RUN: bios2.json missing judges {missing}")
    derangement, fictional, doctrine = {}, "", {}
    if "L4X" in MODEL_ARMS:
        derangement = _load_json("data/derangement_map.json")["map"]
    if "L4F" in MODEL_ARMS:
        fictional = open("data/persona2_fictional.md", encoding="utf-8").read()
    if "D0" in MODEL_ARMS or "L4D" in MODEL_ARMS:
        doctrine = _load_json("data/doctrine_primers.json")
    personas, pool_personas = {}, {}
    if SMOKE:
        judges = sorted(set(judges) | {derangement[j] for j in judges if j in derangement})
    if not SMOKE:
        for j in judges:
            if j in NO_PERSONA_JUDGES:
                continue
            personas[j] = open(f"data/persona2_{j.lower()}.md", encoding="utf-8").read()
        for court, fname in (("SDNY", "data/persona2_sdny_pool.md"),
                             ("EDNY", "data/persona2_edny_pool.md")):
            if not os.path.exists(fname):
                sys.exit(f"REFUSING TO RUN: {fname} missing — L2 pooled persona not built.")
            pool_personas[court] = open(fname, encoding="utf-8").read()
    else:  # smoke: tolerate whatever exists, stub the rest
        for j in judges:
            p = f"data/persona2_{j.lower()}.md"
            personas[j] = open(p, encoding="utf-8").read() if os.path.exists(p) \
                else "(stub persona for smoke test)"
        for court in ("SDNY", "EDNY"):
            p = f"data/persona2_{court.lower()}_pool.md"
            pool_personas[court] = open(p, encoding="utf-8").read() \
                if os.path.exists(p) else "(stub pooled persona for smoke test)"
    return {"grounding": grounding, "bios": bios, "personas": personas,
            "pool_personas": pool_personas, "derangement": derangement,
            "fictional": fictional, "doctrine": doctrine}


def majority_by_motion(grounding: list[dict]) -> dict:
    counts: dict[str, dict[str, int]] = {}
    for g in grounding:
        counts.setdefault(g["motion_type"], {"Y": 0, "N": 0})[g["label"]] += 1
    return {mt: ("Y" if c["Y"] >= c["N"] else "N") for mt, c in counts.items()}


def load_cache() -> dict:
    done = {}
    paths = [CACHE_PATH] if SMOKE else [
        "data/answers2.jsonl", "data/answers2_gpt.jsonl", "data/answers2_fable.jsonl"]
    for p in paths:
        if os.path.exists(p):
            for l in open(p, encoding="utf-8"):
                r = json.loads(l)
                done[(r["model"], r["arm"], r["id"])] = r["answer"]
    return done


def main() -> None:
    if not SMOKE and not os.path.exists("FREEZE-2.md"):
        sys.exit("REFUSING TO RUN: FREEZE-2.md not published. Freeze before scoring "
                 "is the signed rule. Run SMOKE=1 for a plumbing test on pre-cutoff data.")
    if SMOKE:
        exam = _load_jsonl("data/grounding2.jsonl")[:4]
        print(f"SMOKE MODE: {len(exam)} PRE-cutoff grounding rows, cache {CACHE_PATH}")
    else:
        exam = _load_jsonl("data/exam2.jsonl")
    ctx = load_context(exam)
    fable_items = [e for e in exam if (e.get("date") or "") > FABLE_CUTOFF]
    plans = [("gpt", exam), ("fable", fable_items)]
    if MODEL_FILTER:
        plans = [(m, its) for m, its in plans if m == MODEL_FILTER]
    done = load_cache()
    todo = sum(1 for model, items in plans for it in items for a in MODEL_ARMS
               if not (a in ("L4", "L4X", "L4D") and it["judge"] in NO_PERSONA_JUDGES)
               and (model, a, it["id"]) not in done)
    print(f"exam n={len(exam)}  fable sub-window n={len(fable_items)}  "
          f"cached={len(done)}  remaining calls={todo}")

    cache = open(CACHE_PATH, "a", encoding="utf-8")
    calls = 0
    t0 = time.time()
    for model, items in plans:
        for i, item in enumerate(items):
            for arm_name in MODEL_ARMS:
                if arm_name in ("L4", "L4X", "L4D") and item["judge"] in NO_PERSONA_JUDGES:
                    continue
                # Erratum E1 (post-freeze, pre-results): the frozen derangement map
                # excludes Vargas ("Vargas excluded", stale from the pre-C2 no-persona
                # assumption); C2 later gave her a persona so she is NOT in
                # NO_PERSONA_JUDGES. Honor the frozen map: skip L4X for any judge it
                # excludes rather than KeyError. Touches no exam item, no other arm.
                if arm_name == "L4X" and item["judge"] not in ctx["derangement"]:
                    continue
                key = (model, arm_name, item["id"])
                if key in done:
                    continue
                system, user = build_arm_prompt(arm_name, item, ctx)
                ans = arms.call_model(system, user) if model == "gpt" \
                    else call_fable(system, user)
                cache.write(json.dumps({"model": model, "arm": arm_name,
                                        "id": item["id"], "answer": ans}) + "\n")
                cache.flush()
                done[key] = ans
                calls += 1
                time.sleep(0.25 if model == "gpt" else 0.4)
            if i % 10 == 0:
                rate = calls / max(time.time() - t0, 1)
                print(f"[{model}] item {i}/{len(items)}  calls this run={calls}  "
                      f"{rate:.1f}/s", file=sys.stderr)
    cache.close()

    if MODEL_FILTER:
        print(f"[{MODEL_FILTER}] model-filtered run complete — run once with no "
              "MODEL_FILTER for the merged pivot (all calls cached).")
        return

    # pivot cache -> predictions2.jsonl
    maj = majority_by_motion(ctx["grounding"])
    armg = os.path.exists("data/armg_frozen.json") and not SMOKE
    with open(OUT_PATH, "w", encoding="utf-8") as out:
        for item in exam:
            row = {"id": item["id"], "label": item["label"], "judge": item["judge"],
                   "court": COURT.get(item["judge"], "SDNY"),
                   "motion_type": item["motion_type"], "date": item.get("date"),
                   "fable_window": (item.get("date") or "") > FABLE_CUTOFF}
            for model, items in plans:
                if item not in items:
                    continue
                row[f"{model}_majority"] = maj.get(item["motion_type"], "N")
                for arm_name in MODEL_ARMS:
                    if arm_name in ("L4", "L4X", "L4D") and item["judge"] in NO_PERSONA_JUDGES:
                        row[f"{model}_{arm_name}"] = "SKIP"
                        continue
                    if arm_name == "L4X" and item["judge"] not in ctx["derangement"]:
                        row[f"{model}_{arm_name}"] = "SKIP"  # erratum E1 (see call loop)
                        continue
                    row[f"{model}_{arm_name}"] = done.get((model, arm_name, item["id"]), "MISSING")
                if armg:
                    votes = [row.get(f"{model}_{a}") for a in ("L2", "L3", "L4")]
                    if "SKIP" in votes or "MISSING" in votes:
                        row[f"{model}_ensemble"] = "SKIP"
                    else:
                        row[f"{model}_ensemble"] = "Y" if votes.count("Y") >= 2 else "N"
            out.write(json.dumps(row) + "\n")
    missing = sum(1 for l in open(OUT_PATH, encoding="utf-8") if '"MISSING"' in l)
    print(f"done: {len(exam)} items -> {OUT_PATH}  (rows with MISSING: {missing})")


if __name__ == "__main__":
    main()
