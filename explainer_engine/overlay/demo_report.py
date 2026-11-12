"""Measure the rendered demo, run the validator and write the reports (validator PASS/FAIL/NOT_RUN per OV per shot, timing, sound, OV-34,
loudness, the list of house numbers used, cost 0). Any FAIL means the demo is not sent.
"""
from __future__ import annotations

import json
from pathlib import Path

from explainer_engine.core.store import write_text_atomic
from explainer_engine.overlay import demo_build as B
from explainer_engine.overlay import demo_measure as M
from explainer_engine.overlay import demo_script as D
from explainer_engine.overlay import rules as R

LIB = Path(__file__).resolve().parents[2] / "assets" / "audio" / "library"
SHORT = {R.PASS: "PASS", R.FAIL: "**FAIL**", R.NOT_RUN: "NOT_RUN", R.NA: "n/a"}


def collect(w: B.Work) -> dict:
    st = B.style()
    ink = st["tokens"]["ink"]
    specs = [B.load_spec(w, s["no"]) for s in D.SHOTS]
    boxes, texts, timing, meas, htmls, pix = {}, {}, {}, {}, {}, {}
    for sp in specs:
        no = sp["shot_no"]
        m = w.p("meas", f"boxes_{no:02d}.json")
        if m.exists():
            d = json.loads(m.read_text())
            boxes[no] = {b["id"]: b["box"] for b in d["boxes"]}
            texts[no] = {b["id"]: b["texts"] for b in d["boxes"]}
            timing[no] = d["timing"]
        h = w.p("proj", f"s{no:02d}", "index.html")
        if h.exists():
            htmls[no] = h.read_text()
        meas[no] = {}
        comp = w.p("comp", f"comp_{no:02d}.mp4")
        if sp["items"] and comp.exists() and no in texts:
            meas[no]["contrast"] = M.contrast(comp, sp, texts[no], ink)
        bg = w.p("bg", f"bg_{no:02d}.mp4")
        if sp["mode"] == "full" and bg.exists():
            meas[no]["bg_std"] = M.bg_std(bg, sp["frames"])
        if sp["mode"] == "full" and comp.exists():
            run, dmin = M.frozen_run(comp)
            meas[no]["max_frozen_run"], meas[no]["min_frame_diff"] = run, dmin
        ov = w.p("ov", f"ov_{no:02d}.webm")
        if sp["items"] and ov.exists():
            a = M.alpha_frames(ov)
            if any(p["surface"] == "glass" for p in sp["panels"]):
                meas[no]["glass_alpha"] = M.glass_alpha(ov, sp, a)
            if no in boxes:
                pix[no] = M.pixel_first_change(ov, sp, boxes[no], a)
    return {"specs": specs, "boxes": boxes, "texts": texts, "timing": timing, "meas": meas, "htmls": htmls, "pix": pix}


def run(w: B.Work) -> dict:
    c = collect(w)
    mix = json.loads(w.p("sound", "mix_report.json").read_text()) if w.p("sound", "mix_report.json").exists() else None
    order = json.loads(w.p("final", "render_order.json").read_text()) if w.p("final", "render_order.json").exists() else None
    narr = {l["no"]: l for l in B.narration()}
    rep = R.validate(c["specs"], D.SHOTS, lines=narr, boxes=c["boxes"], meas=c["meas"], htmls=c["htmls"], mix=mix, order=order, lib_present=any(LIB.glob("**/*.wav")))
    rep["fails"] = R.failures(rep)
    rep["timing"] = timing_rows(c)
    rep["measurements"] = {str(k): {kk: vv for kk, vv in v.items()} for k, v in c["meas"].items()}
    rep["cost_usd"] = 0
    write_text_atomic(w.p("final", "validator_report.json"), json.dumps(rep, indent=1, ensure_ascii=False))
    write_text_atomic(w.p("final", "DEMO_REPORT.md"), markdown(c, rep, mix))
    return rep


def timing_rows(c: dict) -> list[dict]:
    rows = []
    for sp in c["specs"]:
        no = sp["shot_no"]
        words = {}
        for x in sp["words"]:
            words.setdefault(x["word"], []).append(x["start_frame"])
        tm = {t["id"]: t for t in c["timing"].get(no, [])}
        for it in sp["items"]:
            if it["kind"] in R.STATIC or not it.get("word"):
                continue
            tok = it["word"].split()[0].lower()
            wf = min(words.get(tok, [None]), key=lambda f: abs((f or 0) - it["start"]))
            t = tm.get(it["id"], {})
            px = c["pix"].get(no, {}).get(it["id"])
            rows.append({"shot": no, "item": it["id"], "kind": it["kind"], "word": it["word"], "word_frame": wf, "plan_frame": it["start"],
                         "first_change_frame": t.get("first_change"), "pixel_first_change": px,
                         "deviation": None if t.get("first_change") is None else t["first_change"] - wf})
    return rows


def markdown(c: dict, rep: dict, mix: dict | None) -> str:
    out = ["# Overlay demo: report (DEMO data, never uploaded; cost 0)", ""]
    ids = list(R.SHOT_RULES)
    nos = [s["no"] for s in D.SHOTS]
    out += ["## 1. Validator: PASS / FAIL / NOT_RUN per rule and shot (n/a = nothing to judge in that shot)", "",
            "| rule | " + " | ".join(str(n) for n in nos) + " |", "|---|" + "---|" * len(nos)]
    for k in ids:
        out.append(f"| {k} | " + " | ".join(SHORT[rep["shots"][n][k]["status"]] for n in nos) + " |")
    out += ["", "Episode-level rules:", "", "| rule | status | detail |", "|---|---|---|"]
    out += [f"| {k} | {SHORT[v['status']]} | {v['detail']} |" for k, v in rep["episode"].items()]
    out += ["", f"FAIL count: {len(rep['fails'])}" + (": " + "; ".join(rep["fails"]) if rep["fails"] else " (the demo may be sent)"), "", "### Details (the rule's own words)", ""]
    for n in nos:
        for k in ids:
            v = rep["shots"][n][k]
            if v["status"] != R.NA:
                out.append(f"- shot {n} {k} {SHORT[v['status']]}: {v['detail']}")
    out += ["", "## 2. Timing: every element on its word (planned frame = word start; first change = first frame its own nodes differ; the pixel check reads the rendered alpha)", "",
            "| shot | item | kind | word | word frame | first change | deviation | rendered pixels |", "|---|---|---|---|---|---|---|---|"]
    for t in rep["timing"]:
        out.append(f"| {t['shot']} | {t['item']} | {t['kind']} | {t['word']} | {t['word_frame']} | {t['first_change_frame']} | {t['deviation']} | {t['pixel_first_change']} |")
    devs = [t["deviation"] for t in rep["timing"] if t["deviation"] is not None]
    out += ["", f"Elements: {len(devs)}; earliest deviation {min(devs)} frames, latest {max(devs)}; early (< 0): {sum(1 for d in devs if d < 0)}; over 1 frame: {sum(1 for d in devs if abs(d) > 1)}."]
    out += ["", "## 3. Sound events (one per motion; the demo's sounds are procedural numpy, demo only)", "", "| shot | item | class | frame | frames long |", "|---|---|---|---|---|"]
    for sp in c["specs"]:
        for e in sp["sound"]:
            out.append(f"| {sp['shot_no']} | {e['item']} | {e['cls']} | {e['t']} | {e['dur']} |")
    if mix:
        out += ["", "## 4. Loudness (ffmpeg ebur128, LUFS)", "", f"- groups (bed + overlay sounds + clip, without narration): {mix['groups']}",
                f"- the scene's real sounds (wind + fire): integrated {mix['ambience']['integrated']}, median momentary {mix['ambience']['momentary_median']}",
                f"- overlay sounds: loudest momentary {mix['sfx']['momentary_max']}; below the scene's real sounds by {mix['sfx_under_scene_lu']} LU",
                f"- narration (scratch Kokoro): integrated {mix['narration']['integrated']}",
                f"- the quietest 100 ms of the bed: {mix['ambience_min_100ms_dbfs']} dBFS"]
    out += ["", "## 5. OV-34: faces and the main object, every frame of the push", ""]
    for sp in c["specs"]:
        if sp["mode"] == "accent":
            res = rep["shots"][sp["shot_no"]]["OV-34"]
            out.append(f"- shot {sp['shot_no']} ({sp['photo']}): {res['detail']}")
    out += ["", "## 6. The house numbers (the rules file's \"წ\") that this demo used", "", "| number | value |", "|---|---|"]
    out += [f"| {k} | {v} |" for k, v in R.HOUSE.items()]
    out += ["", "Data: every number on screen is DEMO data (no claim map); the demo is never uploaded. Cost: 0 (no ElevenLabs, LTX, Gemini API, pod or Modal)."]
    return "\n".join(out) + "\n"
