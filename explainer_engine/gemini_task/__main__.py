"""CLI of the Gemini Task route. Every command is free and local; the PC session pastes, attaches and downloads.

    python -m explainer_engine.gemini_task pack   episodes/ep_toba            # 1: rules pack -> planning/gemini_task/drive/
    python -m explainer_engine.gemini_task t0     episodes/ep_toba            # 7: the T0 message
    python -m explainer_engine.gemini_task t0-record episodes/ep_toba --answer a.txt --drop dl/ --by "<thread>"
    python -m explainer_engine.gemini_task open   episodes/ep_toba            # P0
    python -m explainer_engine.gemini_task check  episodes/ep_toba short_story|script|video_script   # 2: P1-P3
    python -m explainer_engine.gemini_task review-intake episodes/ep_toba <stage> --answer a.txt
    python -m explainer_engine.gemini_task reply  episodes/ep_toba <stage> --decisions d.json      # P4
    python -m explainer_engine.gemini_task reply-intake episodes/ep_toba <stage> --answer a.txt
    python -m explainer_engine.gemini_task decide episodes/ep_toba <stage> F3 A|B --by <creator message id>
    python -m explainer_engine.gemini_task queue  episodes/ep_toba            # 3 + 6: shot_queue.json (timed when audio/timing.json exists)
    python -m explainer_engine.gemini_task save-queue episodes/ep_toba [--answer a.txt]           # P5
    python -m explainer_engine.gemini_task batch  episodes/ep_toba 1          # 4: P6/P7/P8
    python -m explainer_engine.gemini_task intake episodes/ep_toba 1 --answer a.txt --drop dl/
    python -m explainer_engine.gemini_task verdict episodes/ep_toba <id> ok|redo [--reason ...] [--correction "..."]
    python -m explainer_engine.gemini_task approve episodes/ep_toba <ref id> --by <creator message id>
    python -m explainer_engine.gemini_task approve-anchor <A..G> <repo file> --by <creator message id>
    python -m explainer_engine.gemini_task resume episodes/ep_toba 1          # P9
    python -m explainer_engine.gemini_task redo   episodes/ep_toba R1|R2|scene   # 5: P10
    python -m explainer_engine.gemini_task redo-intake episodes/ep_toba 1 --answer a.txt --drop dl/
    python -m explainer_engine.gemini_task status episodes/ep_toba
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from explainer_engine.core.errors import ContractError


def _read(p: Path | None) -> str:
    return Path(p).read_text(encoding="utf-8") if p else ""


def main(argv=None) -> int:
    from explainer_engine.gemini_task import batch as BT
    from explainer_engine.gemini_task import gate as GT
    from explainer_engine.gemini_task import pack as PK
    from explainer_engine.gemini_task import queue as QU
    from explainer_engine.gemini_task import review as RV
    ap = argparse.ArgumentParser(prog="python -m explainer_engine.gemini_task", description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    def add(name, *args):
        p = sub.add_parser(name)
        p.add_argument("episode", type=Path)
        for a in args:
            p.add_argument(*a[0], **a[1])
        return p
    ans = (["--answer"], {"type": Path, "required": True})
    drop = (["--drop"], {"type": Path, "required": True})
    by = (["--by"], {"required": True})
    stage = (["stage"], {"choices": tuple(RV.STAGES)})
    add("pack")
    add("t0")
    add("t0-record", ans, drop, by, (["--code-drawn"], {"type": int, "default": 0}), (["--elapsed"], {"type": float}))
    add("open")
    add("check", stage)
    add("review-intake", stage, ans)
    add("reply", stage, (["--decisions"], {"type": Path, "required": True}))
    add("reply-intake", stage, ans)
    add("decide", stage, (["finding"], {}), (["choice"], {"choices": ("A", "B")}), by)
    add("queue", (["--size"], {"type": int}))
    add("save-queue", (["--answer"], {"type": Path}))
    add("batch", (["no"], {"type": int}))
    add("intake", (["no"], {"type": int}), ans, drop)
    add("verdict", (["id"], {}), (["result"], {"choices": ("ok", "redo")}), (["--reason"], {"default": ""}),
        (["--correction"], {}))
    add("approve", (["ref"], {}), by)
    pa = sub.add_parser("approve-anchor")
    pa.add_argument("type")
    pa.add_argument("file")
    pa.add_argument("--by", required=True)
    add("resume", (["no"], {"type": int}))
    add("redo", (["phase"], {"choices": ("R1", "R2", "scene")}))
    add("redo-intake", (["no"], {"type": int}), ans, drop)
    add("status")
    a = ap.parse_args(argv)
    try:
        c = a.cmd
        if c == "pack":
            res = PK.export(a.episode)
        elif c == "t0":
            res = GT.render_t0(a.episode)
        elif c == "t0-record":
            res = GT.record_t0(a.episode, _read(a.answer), BT.drop_files(a.drop), a.by, a.code_drawn, a.elapsed)
            res = {k: v for k, v in res.items() if k != "pictures"} | {"pictures": [(p["id"], p["ok"]) for p in res["pictures"]]}
        elif c == "open":
            res = RV.render_open(a.episode)
        elif c == "check":
            res = RV.render_check(a.episode, a.stage)
        elif c == "review-intake":
            res = RV.intake_review(a.episode, a.stage, _read(a.answer))
        elif c == "reply":
            res = RV.reply(a.episode, a.stage, json.loads(_read(a.decisions)))
        elif c == "reply-intake":
            res = RV.intake_reply(a.episode, a.stage, _read(a.answer))
        elif c == "decide":
            res = RV.decide(a.episode, a.stage, a.finding, a.choice, a.by)
        elif c == "queue":
            doc = QU.build(a.episode, a.size)
            p = QU.write(a.episode, doc)
            res = {"queue": str(p), **doc["counts"], "timed": doc["timed"], "mode": doc["mode"], "t0": doc["t0_status"],
                   "mix": doc["mix"]["shares"], "review": len(doc["review"])}
        elif c == "save-queue":
            res = BT.intake_save_queue(a.episode, _read(a.answer)) if a.answer else BT.render_save_queue(a.episode)
        elif c == "batch":
            res = BT.render(a.episode, a.no)
        elif c == "intake":
            res = BT.intake(a.episode, a.no, _read(a.answer), BT.drop_files(a.drop))
        elif c == "verdict":
            res = BT.verdict(a.episode, a.id, a.result == "ok", a.reason, a.correction)
        elif c == "approve":
            res = BT.approve(a.episode, a.ref, a.by)
        elif c == "approve-anchor":
            res = BT.approve_anchor(a.type, a.file, a.by)
        elif c == "resume":
            res = BT.resume(a.episode, a.no)
        elif c == "redo":
            res = BT.redo(a.episode, a.phase)
        elif c == "redo-intake":
            res = BT.intake_redo(a.episode, a.no, _read(a.answer), BT.drop_files(a.drop))
        else:
            res = BT.status(a.episode)
    except ContractError as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False, indent=1))
        return 2
    print(json.dumps(res, ensure_ascii=False, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
