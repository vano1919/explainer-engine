"""CLI of the LoRA training control (docs/LORA_TRAINING.md). Exit 1 on a FAIL / a STOP_FAIL.

    python -m explainer_engine.training audit-style <folder>... [--repeats his=4,aux_k=1] [--creator his]
    python -m explainer_engine.training audit-edit <targets> <control>...
    python -m explainer_engine.training audit-video <clips.json>
    python -m explainer_engine.training check-config <cfg.yaml> --kind style|edit|video [--captions <folder>...]
           [--image ostris/aitoolkit:latest --boot-minutes 25]
    python -m explainer_engine.training cost --log <train.log> --price 0.59 --cap 1.8 [--spent 0.5] [--prompts 6
           --sec-per-sample 79 --save-every 250 --boot-minutes 0]
    python -m explainer_engine.training footage-index|footage-split|footage-measure|footage-balance|footage-pairs|footage-clips ...
           (see training/footage.py)
    python -m explainer_engine.training judge-style --samples <dir> --refs <dir> --config <cfg.yaml> [--train <dir>...]
           [--cache <dir>] [--out judge.json]
    python -m explainer_engine.training video-qa <clip.mp4> [--layout <layout.mp4>] [--regions <regions.json>]
           [--ref <rhythm.json>] [--sheet <sheet.jpg>] [--out <qa.json>]
    python -m explainer_engine.training footage-rhythm <work dir> --out <rhythm.json> [--per-show 40]
    python -m explainer_engine.training shot-identity <a.mp4> [<b.mp4>] [--heroes <heroes.json>] [--out <id.json>]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from . import audit, judge


def _opt(argv, name, default=None, many=False):
    if name not in argv:
        return default
    i = argv.index(name)
    vals = []
    for a in argv[i + 1:]:
        if a.startswith("--"):
            break
        vals.append(a)
    return vals if many else (vals[0] if vals else default)


def _pos(argv):
    out = []
    for a in argv:
        if a.startswith("--"):
            break
        out.append(a)
    return out


def _print(report):
    print(json.dumps(report, ensure_ascii=False, indent=1, default=str))


def _done(report):
    report["verdict"] = audit.verdict(report["findings"])
    _print(report)
    return 1 if report["verdict"] == "FAIL" else 0


def _load_yaml(path):
    import yaml
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def _captions(folders):
    return [i["caption"] for fo in folders for i in audit.scan(fo) if i["caption"]]


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print(__doc__)
        return 2
    cmd, rest = argv[0], argv[1:]
    if cmd == "audit-style":
        reps = dict(kv.split("=") for kv in (_opt(rest, "--repeats", "") or "").split(",") if "=" in kv)
        return _done(audit.audit_style(_pos(rest), repeats={k: float(v) for k, v in reps.items()},
                                       creator_folders=tuple(_opt(rest, "--creator", ["his"], many=True))))
    if cmd == "audit-edit":
        p = _pos(rest)
        return _done(audit.audit_edit(p[0], p[1:]))
    if cmd == "audit-video":
        return _done(audit.audit_video(_pos(rest)[0]))
    if cmd == "check-config":
        launch = None
        if _opt(rest, "--image"):
            launch = {"image": _opt(rest, "--image"), "boot_minutes": float(_opt(rest, "--boot-minutes", 0))}
        return _done(audit.check_config(_load_yaml(_pos(rest)[0]), _opt(rest, "--kind", "style"),
                                        captions=_captions(_opt(rest, "--captions", [], many=True)), launch=launch))
    if cmd == "cost":
        done, total, sps = judge.log_progress(Path(_opt(rest, "--log")).read_text(encoding="utf-8", errors="ignore"))
        save = int(_opt(rest, "--save-every", 250))
        ckpts_left = len(range((done // save + 1) * save, total + 1, save))
        proj = audit.project_cost(steps=total, done_steps=done, sec_per_step=sps, price_per_hour=float(_opt(rest, "--price")),
                                  n_ckpt_samples=ckpts_left, n_prompts=int(_opt(rest, "--prompts", 0)),
                                  sec_per_sample=float(_opt(rest, "--sec-per-sample", 0)),
                                  boot_minutes=float(_opt(rest, "--boot-minutes", 0)),
                                  spent_usd=float(_opt(rest, "--spent", 0)))
        rep = {"done": done, "total": total, "sec_per_step": sps, "projection": proj,
               "findings": audit.spend_findings(proj, float(_opt(rest, "--cap")))}
        return _done(rep)
    if cmd == "judge-style":
        from . import embed
        cfg = _load_yaml(_opt(rest, "--config"))
        view = audit.config_view(cfg)
        trig = view["trigger"] or audit.RULES["dataset"]["trigger"]
        cache = _opt(rest, "--cache")
        by_path = judge.parse_samples(Path(_opt(rest, "--samples")).rglob("*"))
        by_step = {st: dict(zip(sorted(ps), embed.images([ps[i] for i in sorted(ps)], cache))) for st, ps in by_path.items()}
        refs = embed.images(sorted(i["path"] for i in audit.scan(_opt(rest, "--refs"))), cache)
        train_dirs = _opt(rest, "--train", [], many=True)
        train = embed.images([i["path"] for d in train_dirs for i in audit.scan(d)], cache) if train_dirs else None
        prompts = view["prompts"]
        texts = dict(enumerate(embed.texts([audit.strip_trigger(p, trig) for p in prompts])))
        caps = _captions(train_dirs)
        seen = audit.heldout(prompts, caps, trig) if caps else [0.0] * len(prompts)
        held = {i: s <= audit.RULES["config"]["heldout_seen_words_max"] for i, s in enumerate(seen)}
        no_trig = {i for i, p in enumerate(prompts) if not p.lower().startswith(trig.lower())}
        rows = judge.score_run(by_step, refs, train=train, texts=texts, heldout=held, no_trigger=no_trig)
        dec = judge.decide(rows, int(view["steps"] or 0))
        rep = {"rows": rows, "decision": dec, "heldout": held}
        if _opt(rest, "--out"):
            Path(_opt(rest, "--out")).write_text(json.dumps(rep, indent=1, default=str), encoding="utf-8")
        _print(rep)
        return 1 if dec["action"] == "STOP_FAIL" else 0
    if cmd in ("video-qa", "footage-rhythm", "shot-identity"):
        from . import video_qa
        p = _pos(rest)
        if cmd == "shot-identity":
            heroes = json.loads(Path(_opt(rest, "--heroes")).read_text(encoding="utf-8")) if _opt(rest, "--heroes") else None
            m, findings = video_qa.identity_file(p[0], p[1] if len(p) > 1 else None, heroes)
            rep = {"clips": p, "metrics": m, "findings": findings}
            if _opt(rest, "--out"):
                Path(_opt(rest, "--out")).write_text(json.dumps(rep, indent=1), encoding="utf-8")
            return _done(rep)
        if cmd == "footage-rhythm":
            ref = video_qa.footage_rhythm(p[0], per_show=int(_opt(rest, "--per-show", 40)))
            Path(_opt(rest, "--out")).write_text(json.dumps(ref, indent=1), encoding="utf-8")
            _print(ref)
            return 0
        load = lambda o: json.loads(Path(_opt(rest, o)).read_text(encoding="utf-8")) if _opt(rest, o) else None  # noqa: E731
        regions = load("--regions")
        m, findings = video_qa.qa_file(p[0], regions=regions, ref=load("--ref"), layout=_opt(rest, "--layout"))
        if _opt(rest, "--sheet"):
            m["sheet"] = video_qa.review_sheet(p[0], _opt(rest, "--sheet"), regions)
        rep = {"clip": p[0], "metrics": m, "findings": findings}
        if _opt(rest, "--out"):
            Path(_opt(rest, "--out")).write_text(json.dumps(rep, indent=1), encoding="utf-8")
        return _done(rep)
    if cmd.startswith("footage-"):
        from . import footage
        p = _pos(rest)
        sub = cmd[len("footage-"):]
        if sub == "index":
            return _done(footage.index(p[0], _opt(rest, "--out", p[0])))
        if sub == "split":
            shots = footage.split(p[0], min_len_s=float(_opt(rest, "--min-len", 0)) or None)
            print(json.dumps({"shots": len(shots), "dups": sum(1 for s in shots if s["dup_of"])}))
            return 0
        if sub == "measure":
            shots = footage.measure(p[0])
            from collections import Counter
            print(json.dumps(dict(Counter(footage.classify(s) for s in shots))))
            return 0
        if sub == "balance":
            shots = json.loads((Path(p[0]) / "shots.json").read_text(encoding="utf-8"))
            return _done(footage.balance(shots, heldout=_opt(rest, "--heldout")))
        if sub == "pairs":
            made = footage.pairs(p[0], _opt(rest, "--out"), heldout=_opt(rest, "--heldout"))
            print(json.dumps({"pairs": len(made)}))
            return 0
        if sub == "clips":
            made = footage.clips(p[0], _opt(rest, "--out"), heldout=_opt(rest, "--heldout"),
                                 max_per_show=int(_opt(rest, "--max-per-show", 0)) or None)
            print(json.dumps({"clips": len(made)}))
            return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
