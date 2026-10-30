"""Keyframe gate (KG-01..KG-22, docs/KEYFRAME_GATE.md): every picture of an animated shot is checked before the next step
uses it, every check is logged with its cause, and the log says what to fix: a prompt rule or a LoRA. stdlib only.

ვანო (2026-10-24 18:53 Tbilisi): the system draws a picture, checks its logic, the world's physics and whether a video can
be made from it, draws again when it fails, and only a passing master goes on to the scene LoRA; every session records what
came out right and wrong and whose fault it was (prompt, style LoRA, scene LoRA), so only the weak part is fixed.

A shot here is ``{"id", "kind": keyframe|nextpose|cut, "people": [{"tag", "where"?, "height"?, "on"?, "actor"?}],
"relations"?: [str], "lead_room"?: {"side"}, "limbs"?: bool}``, the film_shots fields (PR #24, KP-31..34). The questions go to a vision model (Qwen2.5-VL on
the pod, free) as one numbered list; its numbered answers come back to ``verdict``.

    python -m explainer_engine.qa.keyframe_gate questions <shot.json>     # the numbered questions for one shot
    python -m explainer_engine.qa.keyframe_gate table <cards.json>       # Claude's review table, filled before showing
    python -m explainer_engine.qa.keyframe_gate summary <qa_log.jsonl>    # error counts by cause and the fix for each
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

from explainer_engine.qa.blind_check import STYLE_SUSPENDED  # one home for the D-80 flag

KINDS = ("keyframe", "nextpose", "cut")
MAX_TRIES = 3          # KG-14: three seeds, then the prompt is fixed, never an endless redraw
RETRAIN_AT = 15        # KG-15: cases of one error type on one LoRA before a retraining is proposed (house, 2026-10-24)
# KG-20: the 7B missed a second mammoth, three buses and a twin; the 72B (AWQ, ~41 GB) fits the 80 GB card once the image
# model is unloaded, and every question is asked on its own (`single_prompt`): one long numbered list let answers drift
VLM_MODEL = "Qwen/Qwen2.5-VL-72B-Instruct-AWQ"

# KG-16: which base model each of our LoRAs was trained on; a LoRA is loaded only into its own base
LORA_BASE = {
    "xworld": "Qwen/Qwen-Image-2.1",    # D-80: the new look (R&M) and the scene sequence, one LoRA
}
BASE = "Qwen/Qwen-Image-2.1"  # D-80: the one image stack
RETIRED_LORAS = ("wldnk_",)  # D-80: every LoRA trained before 2026-10-26 (wldnk_style, _scene, _qi21, _wan22)
RETIRED = {"Qwen/Qwen-Image-2512", "Qwen/Qwen-Image-Edit-2511"}


# the film_shots screen places (scripting/film_shots.WHERE, PR #24) as a question can say them
WHERE = {"left": "left side", "center": "center", "right": "right side", "left_back": "left side, in the background",
         "center_back": "center, in the background", "right_back": "right side, in the background",
         "left_front": "left side, in the foreground", "right_front": "right side, in the foreground"}


# KG-12 asks for whole arms only where the body is in the frame: a close shot cuts the arms by design (test v2: a CU failed)
CLOSE = {"MS", "MCU", "CU", "ECU"}

HEIGHT = {"quarter": "a quarter", "third": "a third", "half": "half", "two_thirds": "two thirds", "most": "most"}


def _q(code: str, text: str, expect: str | int, hard: bool = True) -> dict:
    return {"code": code, "q": text, "expect": expect, "hard": hard}


def questions(shot: dict) -> list[dict]:
    """The checks of one picture, built from its shot card; every question has an expected answer."""
    if shot.get("kind") not in KINDS:
        raise ValueError(f"kind must be one of {KINDS}")
    people = shot.get("people", [])
    out = [_q("KG-01", "How many people and animals are in the picture? Answer with a number.", len(people))]
    for p in people:
        tag = p["tag"]
        out.append(_q("KG-02", f"Is there {tag} in the picture?", "yes"))
        # KG-01 per figure: the total missed a second mammoth (counted 5 of 6); one figure drawn twice is the commonest error
        out.append(_q("KG-01", f"How many times does {tag} appear in the picture? Answer with a number.", 1))
        if p.get("where"):
            out.append(_q("KG-03", f"Is {tag} on the {WHERE.get(p['where'], p['where'])} of the picture?", "yes"))
        if p.get("height"):
            out.append(_q("KG-04", f"Does {tag} take up at least {HEIGHT.get(p['height'], p['height'])} of the picture's height?", "yes", hard=False))
        if p.get("on"):
            out.append(_q("KG-05", f"Is {tag} resting on {p['on']}, not floating in the air?", "yes"))
        for mark in p.get("marks", []):   # KG-19: the sheet's marks (asset test: the old man lost his round glasses)
            out.append(_q("KG-19", f"Does {tag} have {mark}?", "yes"))
    for rel in shot.get("relations", []):
        out.append(_q("KG-06", f"Is this true in the picture: {rel}?", "yes"))
    # KG-18: a twin is the commonest error (the pink-haired girl drawn twice in all 10 bus pictures, 2026-10-24)
    if len(people) > 1:
        out.append(_q("KG-18", "Are two of the people or animals look-alikes, with the same hair colour or the same clothes?",
                      "no"))
    for thing in shot.get("things", []):   # KG-01 for objects: a bus is one bus (asset test: three buses)
        out.append(_q("KG-01", f"How many {thing['plural']} are in the picture? Answer with a number.", thing.get("count", 1)))
    for x in shot.get("absent", []):       # KG-21: the world's absent things (asset test: a road and a car in the ice age)
        out.append(_q("KG-21", f"Is there {x} anywhere in the picture?", "no"))
    out += [
        _q("KG-07", "Does any person, animal or object float in the air without a visible reason?", "no"),
        _q("KG-08", "Does any person have a wrong number of arms, legs or fingers, or an object stuck inside the face or "
                    "eyes?", "no"),
        _q("KG-09", "Is any animal or object ambiguous, so that it could be a carving, a painting or a real thing?", "no"),
        _q("KG-10", "Is there any written text, letters or a sign with words?", "no", hard=False),
        _q("KG-17", "Are there measurement lines, arrows, rulers, percentages or numbers drawn over the picture?", "no"),
    ]
    actor = next((p for p in people if p.get("actor")), None)
    room = (shot.get("lead_room") or {}).get("side") or shot.get("free_space")      # film_shots `lead_room` (KP-34)
    if actor and room and room != "none":
        side = {"above": "space above", "below": "space below"}.get(room, f"space on the {room}")
        out.append(_q("KG-11", f"Is there empty {side} of {actor['tag']} to move into?", "yes"))
    if actor and shot.get("limbs", True) and shot["kind"] == "keyframe" and shot.get("size") not in CLOSE:
        out.append(_q("KG-12", f"Are both arms and hands of {actor['tag']} fully inside the picture?", "yes"))
    if shot["kind"] in ("nextpose", "cut"):
        out.append(_q("KG-13", "Compared with the first image, is the drawing style (line, colour, texture) the same?",
                      "yes"))
    return out


def vlm_prompt(qs: list[dict]) -> str:
    """One prompt for the vision model: numbered questions, numbered short answers."""
    lines = [f"{i}. {q['q']}" for i, q in enumerate(qs, 1)]
    return ("Look at the picture carefully and answer every question. Reply with one line per question in the form "
            "'<number>. yes', '<number>. no' or '<number>. <a number>'.\n" + "\n".join(lines))


def single_prompt(q: dict) -> str:
    """KG-20: one question per call, answered with one word or one number."""
    kind = "a number" if isinstance(q["expect"], int) else "yes or no"
    return f"Look at the whole picture carefully, corner to corner. {q['q']} Answer with {kind} only."


KG22_SUSPENDED = ("DINOv2 reference set is the retired wldnk eras sheet (D-80); recalibrate on xworld_v2 references on the P12b pod")


def kg22_row() -> dict:
    """The style row of Claude's table. While the style is suspended (D-80) it is a REVIEW, never a yes/no about the retired eras
    sheet, whatever any score says."""
    if STYLE_SUSPENDED:
        return {"code": "KG-22", "status": "REVIEW", "text": KG22_SUSPENDED}
    return {"code": "KG-22", "status": "ASK",
            "text": "Same line, texture, colour depth and detail as the approved eras sheet?"}


def kg22_row_text() -> str:
    r = kg22_row()
    return (f"| KG-22 | REVIEW: {r['text']} | REVIEW | |" if r["status"] == "REVIEW" else f"| KG-22 | {r['text']} | yes | |")


def review_table(card: dict, image: str) -> str:
    """KG-22: Claude's own read of a picture before the creator sees it: every gate question as a row to fill with what
    the picture shows, plus the style row against the approved eras sheet. A picture is shown only with its filled table."""
    rows = [f"| {q['code']} | {q['q']} | {q['expect']} | |" for q in questions(card)]
    rows.append(kg22_row_text())
    return (f"### {card['id']} · `{image}`\n\n| ID | Check | Expected | Seen |\n|---|---|---|---|\n" + "\n".join(rows) + "\n")


def parse_answers(text: str, n: int) -> list[str | None]:
    found: dict[int, str] = {}
    for m in re.finditer(r"^\s*(\d+)[.):]\s*(.+?)\s*$", text, re.M):
        found[int(m.group(1))] = m.group(2)
    out: list[str | None] = []
    for i in range(1, n + 1):
        raw = (found.get(i) or "").lower()
        num = re.search(r"\b(\d+)\b", raw)
        if re.match(r"yes\b", raw):
            out.append("yes")
        elif re.match(r"no\b", raw):
            out.append("no")
        elif num:
            out.append(num.group(1))
        else:
            out.append(None)
    return out


def verdict(qs: list[dict], answers: list[str | None]) -> dict:
    """PASS / FAIL / REVIEW for one picture. A hard check that misses FAILs; a soft one or an unreadable answer REVIEWs."""
    fails, reviews = [], []
    for q, a in zip(qs, answers):
        if a is None:
            reviews.append({"code": q["code"], "q": q["q"], "got": None})
            continue
        if str(a) != str(q["expect"]):
            (fails if q["hard"] else reviews).append({"code": q["code"], "q": q["q"], "got": a})
    status = "FAIL" if fails else "REVIEW" if reviews else "PASS"
    return {"status": status, "fails": fails, "reviews": reviews}


def blame(code: str, *, with_lora: bool, without_lora: bool, other_seed: bool) -> str:
    """KG-15 cause of one error type, from three pictures of the same prompt: the LoRA run, the base model without the
    LoRA, and another seed with the LoRA (KP-14: look at the base before blaming a LoRA)."""
    if not with_lora:
        return "none"
    if without_lora:
        return "prompt"      # the base model makes it too: the prompt (or the base) must change
    return "lora" if other_seed else "chance"


def record(shot: dict, *, model: str, loras: dict, seed: int, prompt: str, result: dict, image: str,
           cause: dict | None = None) -> dict:
    """One line of qa_log.jsonl."""
    return {"shot": shot.get("id"), "kind": shot.get("kind"), "model": model, "loras": loras, "seed": seed,
            "prompt": prompt, "image": image, "status": result["status"],
            "errors": sorted({f["code"] for f in result["fails"]}), "cause": cause or {}}


def append_log(path: str | Path, rec: dict) -> None:
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def read_log(path: str | Path) -> list[dict]:
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def next_step(tries: list[dict]) -> str:
    """KG-14 after each try of one shot: use it, draw again, or stop and fix the prompt."""
    if tries and tries[-1]["status"] == "PASS":
        return "use"
    if len(tries) >= MAX_TRIES:
        return "fix_prompt"
    return "redraw"


def summary(records: list[dict], retrain_at: int = RETRAIN_AT) -> dict:
    """Error counts by cause, and what each asks for: a prompt rule, a retraining candidate, or nothing yet."""
    by_cause: Counter = Counter()
    for r in records:
        for code in r["errors"]:
            cause = r.get("cause", {}).get(code, "unknown")
            lora = ",".join(sorted(r.get("loras", {}))) or "base"
            by_cause[(code, cause, lora)] += 1
    actions = []
    for (code, cause, lora), n in sorted(by_cause.items()):
        if cause == "prompt":
            actions.append({"code": code, "n": n, "do": "prompt rule + lint test (free, first)"})
        elif cause == "lora" and n >= retrain_at:
            actions.append({"code": code, "n": n, "do": f"retraining candidate for {lora}: add passing pictures of this "
                                                         "case, re-run the old test sheet; ask the creator (paid)"})
        elif cause == "lora":
            actions.append({"code": code, "n": n, "do": f"collect: {n}/{retrain_at} before a retraining of {lora}"})
        elif cause == "unknown":
            actions.append({"code": code, "n": n, "do": "run the cause test (base without LoRA + another seed, 2-3 pictures)"})
    total = len(records)
    passed = sum(r["status"] == "PASS" for r in records)
    return {"pictures": total, "passed": passed,
            "counts": [{"code": c, "cause": k, "lora": l, "n": n} for (c, k, l), n in sorted(by_cause.items())],
            "actions": actions}


def check_stack(model: str, loras: dict) -> None:
    """KG-16: refuse a retired base (D-80) and a LoRA on a base it was not trained on (the style LoRA inside Edit-2511
    broke style and faces)."""
    if model in RETIRED:
        raise ValueError(f"{model} is retired (D-80): keyframes come from {BASE}, plain or in edit mode with references")
    for name in loras:
        if name.startswith(RETIRED_LORAS):
            raise ValueError(f"{name} is banned (D-80): every LoRA trained before 2026-10-26 is retired")
        base = next((b for prefix, b in LORA_BASE.items() if name.startswith(prefix)), None)
        if base is None:
            raise ValueError(f"unknown LoRA {name!r}: add its base model to LORA_BASE")
        if base != model:
            raise ValueError(f"{name} was trained on {base}, not {model}: keyframes come from {BASE} with a LoRA "
                             f"trained on it (D-80)")


def main(argv: list[str]) -> int:
    cmd, path = argv[0], argv[1]
    if cmd == "questions":
        print(vlm_prompt(questions(json.loads(Path(path).read_text(encoding="utf-8")))))
        return 0
    if cmd == "table":
        cards = json.loads(Path(path).read_text(encoding="utf-8"))
        print("\n".join(review_table(c, c.get("image", "")) for c in (cards if isinstance(cards, list) else [cards])))
        return 0
    if cmd == "summary":
        print(json.dumps(summary(read_log(path)), indent=1, ensure_ascii=False))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
