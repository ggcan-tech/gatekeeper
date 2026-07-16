#!/usr/bin/env python3
"""Case-Digest Optimizer v0 — "the loop that learns what to read".

Generalizes the persona loop (pipeline/persona_loop.py) one level up: instead of
learning a per-judge decision profile, it learns an EXTRACTION INSTRUCTION SET
(per motion type) that digests a case document into the features a bench actually
responds to. The learned artifact (data/extractor_{motion_type}.md) is product IP:
it must transfer to unseen customer drafts, so the loop revises WHAT TO EXTRACT
(instructions), never per-case summaries.

The loop, per iteration t:
  1. DIGEST   apply E_t to each item's case text -> data/digests/{mt}/iter{t}/{id}.txt
  2. LEAKAGE  blinded arm (no judge, no grounding) predicts outcomes from digests
              alone; if it beats majority by >3 pts (one-sided binomial vs
              majority+3, p<.05) the digests leak -> revise E with an anti-leakage
              rule and DO NOT SCORE this iteration (frozen, unskippable gate).
  3. SCORE    frozen predictor = persona-v1 + retrieval (exact arms.py composition)
              + the digest appended to build_inputs; accuracy on the held-out eval
              slice. Eval outcomes are NEVER shown to E.
  4. REVISE   show E_t the TRAIN-slice mistakes (digest | predicted | actual)
              -> E_{t+1}. Plateau stop after 3 rounds without improvement.

Baselines (dev-track, printed in history):
  B0  no digest (persona+retrieval only) — the current v1 regime.
  B1  static E_0 digest (iteration 1, no optimization) — proves the LOOP adds
      value, not just "more text".

HARD RULE (G2 exam wall): pre-cutoff items only; refuses any item dated after
exam.model_cutoff in config.yaml (asserted at load). This is lab tooling —
[MEASURED] tier at best; no accuracy claims live here.

Usage: python3 pipeline/digest_optimizer.py --motion-type motion_to_dismiss --max-iter 8
Output: data/extractor_{motion_type}.md (best E), data/digest_history.jsonl,
        data/digests/{motion_type}/iter{t}/{id}.txt
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import os
import random
import re
import sys
import time
import urllib.error

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import arms  # frozen model access + input construction (the exact production seams)

VALIDATION_SLICE = 0.25          # of the motion-type pool, held out for scoring (persona_loop discipline)
SEED = 42                        # deterministic eval split — rerun reproduces it
PLATEAU_STOP = 3                 # stop after N iterations without an eval improvement
MAX_TRAIN = 120                  # cost cap: <=120 train items digested/predicted per iteration
DIGEST_OUT_CHARS = 900           # cap per digest (PRD)
DIGEST_INPUT_CHARS = 8000        # cap case-text fed to the digester (cost control)
LEAK_MARGIN_PTS = 3              # blinded arm may not beat majority by more than this
CONFIG_PATH = "config.yaml"

# ---- Seed extraction instruction set (E_0). Revised by the loop, never hand-tuned. ----
SEED_EXTRACTOR = (
    "From a case document, extract, as terse labeled bullets:\n"
    "- Parties and posture (who moves, against whom, procedural stage).\n"
    "- Claims and counts at issue.\n"
    "- The legal standard invoked (e.g., Rule 12(b)(6), Twombly/Iqbal).\n"
    "- The movant's core theory (why relief should be granted).\n"
    "- Disputed facts material to the motion.\n"
    "- Procedural history relevant to the motion.\n"
    "NEVER extract outcome language: no disposition, holding, or any phrase from "
    "which the ruling could be inferred."
)

ANTI_LEAK_RULE = (
    "\n\nCRITICAL ANTI-LEAKAGE RULE: the source document may narrate the court's "
    "ruling and its reasoning toward that ruling. Extract ONLY pre-decision posture "
    "(facts, claims, standards, and arguments as presented BEFORE the court rules). "
    "Never include the disposition, the court's conclusions or holding, deference/"
    "dismissal signals, or any phrase from which the outcome could be inferred."
)

DIGEST_SYS_TEMPLATE = (
    "You are a litigation analyst building a STRUCTURED DIGEST of a {mt} case "
    "document for outcome prediction. Follow the extraction instruction set exactly.\n\n"
    "EXTRACTION INSTRUCTIONS:\n{E}\n\n"
    "Output ONLY the digest as terse labeled bullet points, <=160 words. Do not "
    "state, hint at, or imply how the motion was or should be decided."
)

REVISE_SYS = (
    "Below is your current EXTRACTION INSTRUCTION SET for digesting {mt} case "
    "documents, followed by prediction MISTAKES a downstream predictor made using "
    "digests you produced from held-out training cases. Revise the INSTRUCTIONS "
    "(what to extract, emphasize, or omit) to fix the SYSTEMATIC errors — never the "
    "case content itself. The instructions must generalize to unseen customer drafts "
    "of this motion type. Keep the anti-leakage rule intact. Max 320 words. Write "
    "only the revised instruction set."
)

REVISE_LEAK_SYS = (
    "Your extraction instruction set for {mt} case documents produced digests that "
    "LEAKED the case outcome — a blinded model recovered the ruling from the digest "
    "alone. Revise the instructions so digests capture pre-decision posture WITHOUT "
    "any outcome signal. Max 320 words. Write only the revised instruction set."
)


# --------------------------------------------------------------------------- data

def load_model_cutoff(path: str = CONFIG_PATH) -> str:
    """Parse exam.model_cutoff from config.yaml (stdlib only — no yaml dep)."""
    with open(path, encoding="utf-8") as f:
        for line in f:
            m = re.match(r"\s*model_cutoff:\s*[\"']?(\d{4}-\d{2}-\d{2})", line)
            if m:
                return m.group(1)
    sys.exit(f"REFUSING TO RUN: no exam.model_cutoff found in {path} (G2 exam wall).")


def load_texts() -> dict:
    """id -> full opinion text (rich case doc). Empty when not fetched; the loop
    then falls back to the grounding docket description (same seam as persona_loop)."""
    path = "data/opinion_texts.jsonl"
    if not os.path.exists(path):
        return {}
    out = {}
    for line in open(path, encoding="utf-8"):
        r = json.loads(line)
        out[r["id"]] = r["text"]
    return out


def case_text(item: dict, texts: dict) -> str:
    """The raw case document fed to the digester. Full opinion when available,
    else the docket description. Raw (uncensored) — the digester's instructions +
    the leakage gate are what keep the outcome out, not pre-filtering."""
    body = texts.get(item["id"]) or item["description"]
    return body[:DIGEST_INPUT_CHARS]


# --------------------------------------------------------------------------- digest

def digest_dir(mt: str, it: int) -> str:
    return os.path.join("data", "digests", mt, f"iter{it}")


def _ehash(E: str) -> str:
    return hashlib.sha1(E.encode("utf-8")).hexdigest()[:12]


def build_digests(items: list, mt: str, it: int, E: str, texts: dict) -> dict:
    """Digest each item under E_t; cache to data/digests/{mt}/iter{t}/{id}.txt.
    An .ehash sidecar guards reuse: a cached iter dir is only trusted if it was
    built from the same E (revisions produce a new E -> a rebuild)."""
    d = digest_dir(mt, it)
    os.makedirs(d, exist_ok=True)
    stamp = os.path.join(d, ".ehash")
    prev = open(stamp, encoding="utf-8").read().strip() if os.path.exists(stamp) else ""
    fresh = _ehash(E)
    reuse = prev == fresh
    if not reuse:
        # E changed: any cached digests in this dir are stale — drop them before
        # stamping, so the stamp always means "every .txt here was built under E".
        for fn in os.listdir(d):
            if fn.endswith(".txt"):
                os.remove(os.path.join(d, fn))
    # Stamp first: a crash mid-build resumes per-file under the same E.
    with open(stamp, "w", encoding="utf-8") as f:
        f.write(fresh)
    sys_prompt = DIGEST_SYS_TEMPLATE.format(mt=mt, E=E)
    digests = {}
    for i, item in enumerate(items):
        fp = os.path.join(d, f"{item['id']}.txt")
        if os.path.exists(fp):
            digests[item["id"]] = open(fp, encoding="utf-8").read()
            continue
        text = call_model_long(sys_prompt, case_text(item, texts))[:DIGEST_OUT_CHARS]
        with open(fp, "w", encoding="utf-8") as f:
            f.write(text)
        digests[item["id"]] = text
        if i % 25 == 0:
            print(f"  [iter {it}] digested {i}/{len(items)}", file=sys.stderr)
    return digests


# ----------------------------------------------------------------------- prediction

def scored_predict(persona: str, judge: str, retrieved: str, item: dict, digest: str) -> str:
    """Frozen predictor: the EXACT arms.py rsi_persona + retrieval composition, with
    the case digest appended to build_inputs. This is what the digest must improve."""
    system = (arms.SYSTEM_BASE + f"\nYou are predicting Judge {judge}, SDNY.\n"
              f"Decision profile of this judge, learned from their rulings:\n{persona}\n"
              f"This judge's actual recent rulings on this motion type:\n{retrieved}")
    user = arms.build_inputs(item)
    if digest:
        user += f"\n\nStructured digest of THIS case document:\n{digest}"
    return call_model(system, user)


def score(items: list, personas: dict, grounding: list, digests: dict | None) -> tuple[float, list]:
    """Accuracy of the frozen predictor over `items`. digests=None -> B0 (no digest).
    Returns (accuracy, mistakes) where mistakes = [(item, pred), ...]."""
    correct, mistakes = 0, []
    for it in items:
        # Self-exclusion: eval/train items live inside grounding; retrieving the
        # item itself would put its own outcome= line in the prompt (label leak).
        retrieved = arms.retrieve([g for g in grounding if g["id"] != it["id"]], it)
        dg = digests.get(it["id"], "") if digests else ""
        pred = scored_predict(personas[it["judge"]], it["judge"], retrieved, it, dg)
        if pred == it["label"]:
            correct += 1
        else:
            mistakes.append((it, pred))
    return correct / max(len(items), 1), mistakes


# ------------------------------------------------------------------------- leakage

def leakage_gate(items: list, digests: dict, majority: dict) -> dict:
    """Blinded arm: predict outcomes from the digest ALONE (no judge identity, no
    grounding). Mirrors leakage_audit.py's one-sided exact test of
    H0: blinded_acc <= majority_acc + 3 pts. Fails (leaks) iff p < .05."""
    n = len(items)
    blinded_hits = majority_hits = b_disc = c_disc = 0
    for item in items:
        user = (f"Court: SDNY. Motion type: {item['motion_type']}.\n"
                f"Structured digest of this case document:\n{digests[item['id']]}\n"
                f"Predict: Y or N.")
        blind = call_model(arms.SYSTEM_BASE, user)
        maj = majority.get(item["motion_type"], "N")
        br, mr = blind == item["label"], maj == item["label"]
        blinded_hits += br
        majority_hits += mr
        if br and not mr:
            b_disc += 1
        elif mr and not br:
            c_disc += 1
    blind_acc = blinded_hits / n * 100 if n else 0.0
    maj_acc = majority_hits / n * 100 if n else 0.0
    handicap = round(LEAK_MARGIN_PTS / 100 * n)
    b, c = b_disc, c_disc + handicap
    total = b + c
    p = (sum(math.comb(total, k) for k in range(b, total + 1)) / (2 ** total)) if total else 1.0
    return {"n": n, "blinded_acc": round(blind_acc, 1), "majority_acc": round(maj_acc, 1),
            "margin_points": round(blind_acc - maj_acc, 1),
            "p_vs_majority_plus_3": round(p, 4), "leaked": p < 0.05}


# ------------------------------------------------------------- model seams (mockable)

RETRYABLE = (429, 500, 502, 503, 529)


def _with_retry(fn, system: str, user: str) -> str:
    """A full run is ~2K sequential API calls; ride out transient failures."""
    delay = 2.0
    for attempt in range(6):
        try:
            return fn(system, user)
        except urllib.error.HTTPError as e:
            if e.code not in RETRYABLE or attempt == 5:
                raise
        except OSError:  # URLError, timeouts, connection resets
            if attempt == 5:
                raise
        print(f"  transient API error — retry in {delay:.0f}s", file=sys.stderr)
        time.sleep(delay)
        delay = min(delay * 2, 60)
    raise AssertionError("unreachable")


def call_model(system: str, user: str) -> str:
    return _with_retry(arms.call_model, system, user)


def call_model_long(system: str, user: str) -> str:
    return _with_retry(arms.call_model_long, system, user)


# ---------------------------------------------------------------------------- loop

def format_mistakes(mistakes: list, digests: dict) -> str:
    lines = []
    for item, pred in mistakes[:25]:
        dg = digests.get(item["id"], "").replace("\n", " ")[:220]
        lines.append(f"- {item['id']} {item['judge']} {item['motion_type']}: "
                     f"predicted {pred}, actual {item['label']}\n  digest: {dg}")
    return "\n".join(lines)


def run(mt: str, max_iter: int, limit: int | None) -> None:
    cutoff = load_model_cutoff()
    grounding = [json.loads(l) for l in open("data/grounding.jsonl", encoding="utf-8")]
    pool = [g for g in grounding if g["motion_type"] == mt]
    if not pool:
        sys.exit(f"REFUSING TO RUN: no grounding items for motion_type={mt}.")

    # G2 exam wall — pre-cutoff only, asserted at load.
    late = [g for g in pool if (g.get("date") or "9999") > cutoff]
    if late:
        sys.exit(f"REFUSING TO RUN (G2 exam wall): {len(late)} {mt} item(s) dated after "
                 f"model_cutoff {cutoff}, e.g. id={late[0]['id']} date={late[0].get('date')}.")

    texts = load_texts()
    src = "opinion_texts" if texts else "docket descriptions (opinion_texts.jsonl absent)"

    # Deterministic split (SEED) over the whole pool — pooled across judges.
    rng = random.Random(SEED)
    rng.shuffle(pool)
    if limit:
        pool = pool[:limit]
    n_val = max(10, round(len(pool) * VALIDATION_SLICE))
    n_val = min(n_val, len(pool) - 1) if len(pool) > 1 else len(pool)
    eval_items = pool[:n_val]
    train_items = pool[n_val:n_val + MAX_TRAIN]
    print(f"[{mt}] pool={len(pool)} eval={len(eval_items)} train={len(train_items)} "
          f"| case text: {src} | cutoff {cutoff}")

    personas = arms.load_personas({g["judge"] for g in pool})
    counts: dict = {}
    for g in grounding:
        counts.setdefault(g["motion_type"], {"Y": 0, "N": 0})[g["label"]] += 1
    majority = {m: ("Y" if c["Y"] >= c["N"] else "N") for m, c in counts.items()}

    # B0 — no digest (persona + retrieval only): the current v1 regime.
    b0_acc, _ = score(eval_items, personas, grounding, None)
    print(f"[{mt}] B0 (no digest) eval acc {b0_acc*100:.1f}%")

    history = open("data/digest_history.jsonl", "a", encoding="utf-8")

    def log(row: dict) -> None:
        history.write(json.dumps(row) + "\n")
        history.flush()

    E = SEED_EXTRACTOR + ANTI_LEAK_RULE
    best_acc, best_E, since_best = -1.0, E, 0
    b1_acc = None

    for it in range(1, max_iter + 1):
        digests = build_digests(eval_items + train_items, mt, it, E, texts)
        eval_digests = {i["id"]: digests[i["id"]] for i in eval_items}

        gate = leakage_gate(eval_items, eval_digests, majority)
        if gate["leaked"]:
            print(f"[{mt}] iter {it}: LEAK (blinded {gate['blinded_acc']}% vs "
                  f"majority {gate['majority_acc']}%, margin {gate['margin_points']}, "
                  f"p={gate['p_vs_majority_plus_3']}) — revising E, NOT scoring")
            log({"motion_type": mt, "iter": it, "leaked": True, "scored": False,
                 "leakage_margin": gate["margin_points"], "leakage_p": gate["p_vs_majority_plus_3"],
                 "blinded_acc": gate["blinded_acc"], "majority_acc": gate["majority_acc"],
                 "n_eval": gate["n"]})
            revised = call_model_long(REVISE_LEAK_SYS.format(mt=mt), E)
            E = revised if ANTI_LEAK_RULE.strip()[:40] in revised else revised + ANTI_LEAK_RULE
            continue

        acc, _ = score(eval_items, personas, grounding, digests)
        _, train_mistakes = score(train_items, personas, grounding, digests)
        if b1_acc is None:
            # B1 = first iteration that clears the gate: E_0, or its anti-leak
            # revision if E_0 leaked — the closest valid static (pre-mistake-loop)
            # baseline the protocol allows.
            b1_acc = acc
        print(f"[{mt}] iter {it}: eval acc {acc*100:.1f}% "
              f"(leak margin {gate['margin_points']}, {len(train_mistakes)} train mistakes)")
        log({"motion_type": mt, "iter": it, "leaked": False, "scored": True,
             "acc": round(acc, 4), "leakage_margin": gate["margin_points"],
             "n_eval": len(eval_items), "n_train": len(train_items),
             "train_mistakes": len(train_mistakes)})

        if acc > best_acc:
            best_acc, best_E, since_best = acc, E, 0
        else:
            since_best += 1
            if since_best >= PLATEAU_STOP:
                print(f"[{mt}] plateau — stopping")
                break
        if it == max_iter or not train_mistakes:
            break

        E = call_model_long(
            REVISE_SYS.format(mt=mt),
            f"CURRENT INSTRUCTIONS:\n{E}\n\nMISTAKES:\n{format_mistakes(train_mistakes, digests)}")
        if ANTI_LEAK_RULE.strip()[:40] not in E:
            E += ANTI_LEAK_RULE

    # Summary row: the dev-track comparison the winner must beat.
    b0_pts, b1_pts, e_pts = b0_acc * 100, (b1_acc or 0) * 100, best_acc * 100
    beats_b0 = b1_acc is not None and (e_pts - b0_pts) >= 5
    beats_b1 = b1_acc is not None and (e_pts - b1_pts) >= 2
    summary = {"motion_type": mt, "summary": True,
               "B0_no_digest": round(b0_pts, 1),
               "B1_seed_digest": round(b1_pts, 1) if b1_acc is not None else None,
               "best_E": round(e_pts, 1) if best_acc >= 0 else None,
               "dev_win": bool(beats_b0 and beats_b1),
               "beats_B0_by_5": bool(beats_b0), "beats_B1_by_2": bool(beats_b1),
               "n_eval": len(eval_items)}
    log(summary)
    history.close()

    out_path = f"data/extractor_{mt}.md"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(f"# Extraction instruction set — {mt} (lab/digest-optimizer, [MEASURED])\n\n")
        f.write(f"<!-- best-E eval acc {e_pts:.1f}% | B0 {b0_pts:.1f}% | "
                f"B1 {b1_pts:.1f}% | dev_win={beats_b0 and beats_b1} -->\n\n")
        f.write(best_E.strip() + "\n")

    print(f"\n[{mt}] BEST E eval acc {e_pts:.1f}% -> {out_path}")
    print(f"[{mt}] B0 {b0_pts:.1f}% | B1 {b1_pts:.1f}% | best-E {e_pts:.1f}% | "
          f"dev_win={beats_b0 and beats_b1} (>=+5 vs B0 AND >=+2 vs B1)")


def main() -> None:
    ap = argparse.ArgumentParser(description="Case-Digest Optimizer v0 (lab tooling, [MEASURED]).")
    ap.add_argument("--motion-type", required=True, help="e.g. motion_to_dismiss")
    ap.add_argument("--max-iter", type=int, default=8)
    ap.add_argument("--limit", type=int, default=None,
                    help="cap the motion-type pool to N items (cheap runs; deterministic)")
    args = ap.parse_args()
    run(args.motion_type, args.max_iter, args.limit)


if __name__ == "__main__":
    main()
