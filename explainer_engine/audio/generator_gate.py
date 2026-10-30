"""The free-generator gate (P4, D8, BP-162, BP-163, SD-13): a take from a free (open-model) sound generator enters the library
or a mix only when that generator is admitted for that kind (music, sfx, room_tone), and it is admitted only with the creator's
recorded word after a measured test. Free, numpy only, deterministic; nothing here calls a generator or the network.

    measure   technical per take (duration, silence share, clipped share, DC offset, a loop's seam) and variety (across-prompt
              distance against the library's ElevenLabs reference set, near-duplicate seeds) -> ``generator_gate_report/1``
    sheet     a blind A/B listening sheet: each reference paired with a generator take of the same prompt, sides drawn from a seed;
              the sheet and the paired files never say which side is the generator (the key is a separate file)
    admit     writes ``assets/audio/generator_admission.json`` only with ``creator_ref`` + ``at`` and a report that passes
    admitted  what ``assets_reuse`` and the ElevenLabs hook read: the standing admission for a kind, or None

    python -m explainer_engine.audio.generator_gate measure --takes DIR --kind music --prompts prompts.json --reference DIR
        --generator NAME [--model M] --out report.json
    python -m explainer_engine.audio.generator_gate sheet report.json --out DIR --seed N
    python -m explainer_engine.audio.generator_gate admit report.json --generator NAME --kind music --sheet DIR/sheet.md
        --creator-ref <his message id> --at 2026-10-31T10:00:00Z [--prefer-rate 0.6] [--model M]
    python -m explainer_engine.audio.generator_gate status [--kind music]

Take files are ``<prompt id>__s<seed>.wav``; ``prompts.json`` maps a prompt id to ``{"seconds": requested length, "loop": bool,
"text": the prompt, "reference": a reference file name}`` (a reference file whose stem is the prompt id needs no name). The file
that holds the admissions is ``assets/audio/generator_admission.json``; ``$EXPLAINER_GENERATOR_ADMISSION`` (or the ``path``
argument) points the code elsewhere, so tests never touch the real one. Without that file ``admitted`` returns None: no
generator is admitted and the order stays library, then the ElevenLabs connector (the narrator is always the connector).

Every number is BP-163's (``SR.T``). The cosine of two MFCC statistics vectors (``voice_audition.mfcc_embedding``, the one home
of that embedding) measures timbre likeness: it is reported and compared, and the first real run calibrates it. Quality and
prompt fit are the creator's ear, never a number.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import re
import sys
from datetime import datetime
from itertools import combinations
from pathlib import Path

import numpy as np

from explainer_engine.audio import sfx_library, voice_audition
from explainer_engine.core.errors import ContractError
from explainer_engine.core.store import write_json_atomic, write_text_atomic
from explainer_engine.governance import records
from explainer_engine.standards import sourced_rules as SR

REPO = Path(__file__).resolve().parents[2]
ADMISSION = REPO / "assets" / "audio" / "generator_admission.json"
ENV = "EXPLAINER_GENERATOR_ADMISSION"
KINDS = ("music", "sfx", "room_tone")
REPORT_SCHEMA = "generator_gate_report/1"
KEY_SCHEMA = "generator_gate_sheet_key/1"
TAKE = re.compile(r"^(?P<prompt>.+)__s(?P<seed>\d+)\.wav$")


def _t(key: str):
    return SR.T("BP-163", key)


def sha256_of(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _load(path: Path) -> tuple[np.ndarray, int]:
    from explainer_engine.audio import register  # lazy: register imports this module
    return register.load_any(Path(path))


def kind_of_item(category: str, tags) -> str | None:
    """The admission kind of a library item: music; a ``room_tone`` tag; any other foley is sfx; a vocal has no generator kind."""
    if category == "music":
        return "music"
    if "room_tone" in (tags or []):
        return "room_tone"
    return "sfx" if category == "foley" else None


# -- measure -----------------------------------------------------------------------------------------------------------

def take_measures(samples: np.ndarray, rate: int, *, requested: float, loop: bool, item_id: str) -> dict:
    """The technical measures of one take and the rules it misses (BP-163). DC offset is reported, not judged."""
    x = np.asarray(samples, dtype=np.float64)
    seconds = len(x) / rate
    h = max(1, int(_t("window_ms") / 1000 * rate))
    n = len(x) // h
    if n:
        rms = np.sqrt(np.mean(x[: n * h].reshape(n, h) ** 2, axis=1))
        silence = float(np.mean(20 * np.log10(np.maximum(rms, 1e-9)) < _t("silence_floor_dbfs")))
    else:
        silence = 1.0
    clipped = float(np.mean(np.abs(x) >= _t("clip_level"))) if len(x) else 1.0
    seam = [f["detail"] for f in sfx_library.check_seams({"id": item_id, "kind": "loop"}, samples, rate)] if loop else []
    misses = []
    if requested <= 0 or abs(seconds - requested) > _t("duration_tol") * requested:
        misses.append("duration")
    if silence > _t("silence_share_max"):
        misses.append("silence_share")
    if clipped > _t("clip_share_max"):
        misses.append("clipped_share")
    if seam:
        misses.append("loop_seam")
    return {"seconds": round(seconds, 3), "requested_seconds": requested, "silence_share": round(silence, 4),
            "clipped_share": round(clipped, 6), "dc_offset": round(float(np.mean(x)) if len(x) else 0.0, 6),
            "peak_dbfs": round(sfx_library.db(float(np.max(np.abs(x)))), 2) if len(x) else None, "seam": seam, "misses": misses}


def _mean_distance(a: list[np.ndarray], b: list[np.ndarray] | None = None) -> float | None:
    """Mean (1 - cosine) over all pairs of one set, or over the pairs between two sets."""
    pairs = list(combinations(a, 2)) if b is None else [(x, y) for x in a for y in b]
    return float(np.mean([1.0 - voice_audition._cos(x, y) for x, y in pairs])) if pairs else None


def _reference_for(pid: str, spec: dict, reference: list[Path]) -> Path | None:
    for r in reference:
        if r.name == spec.get("reference") or r.stem == pid:
            return r
    return None


def measure(takes: Path, *, kind: str, prompts: dict, reference: list[Path], generator: str = "", model: str = "") -> dict:
    """The ``generator_gate_report/1`` of one generator for one kind: every take's technical measures, each prompt's verdict, the
    variety against the reference set and the verdicts the admission reads."""
    if kind not in KINDS:
        raise ContractError(f"unknown kind {kind!r}; known: {KINDS}")
    reference = [Path(r) for r in reference]
    rows, unmatched = [], []
    emb: dict[str, np.ndarray] = {}
    for path in sorted(Path(takes).glob("*.wav")):
        m = TAKE.match(path.name)
        if not m or m["prompt"] not in prompts:
            unmatched.append(path.name)
            continue
        pid, seed = m["prompt"], int(m["seed"])
        spec = prompts[pid]
        samples, rate = _load(path)
        row = {"prompt": pid, "seed": seed, "file": str(path), "sha256": sha256_of(path),
               **take_measures(samples, rate, requested=float(spec["seconds"]), loop=bool(spec.get("loop")), item_id=f"{pid}__v{seed}")}
        rows.append(row)
        if not row["misses"]:  # a technical miss takes the take out, of the variety as well
            emb[path.name] = voice_audition.mfcc_embedding(samples, rate)
    rows.sort(key=lambda r: (r["prompt"], r["seed"]))
    per_prompt: dict = {}
    for pid, spec in prompts.items():
        mine = [r for r in rows if r["prompt"] == pid]
        short = len(mine) < _t("takes_per_prompt")
        ref = _reference_for(pid, spec, reference)
        per_prompt[pid] = {"takes": len(mine), "takes_missing": short, "clean": bool(mine) and not short and all(not r["misses"] for r in mine),
                           "reference": str(ref) if ref else None, "text": spec.get("text", "")}
    counts: dict = {}
    for r in rows:
        for rule in r["misses"]:
            counts[rule] = counts.get(rule, 0) + 1
    clean = sum(1 for p in per_prompt.values() if p["clean"])
    share = clean / len(per_prompt) if per_prompt else 0.0
    # variety: the generator's admitted-in takes across prompts against the reference set across its own prompts
    by_prompt: dict = {}
    for r in rows:
        name = Path(r["file"]).name
        if name in emb:
            by_prompt.setdefault(r["prompt"], []).append((r["seed"], emb[name]))
    gen_dist = _mean_distance_across([[e for _, e in v] for v in by_prompt.values()])
    ref_emb = []
    for r in reference:
        samples, rate = _load(r)
        ref_emb.append(voice_audition.mfcc_embedding(samples, rate))
    ref_dist = _mean_distance(ref_emb)
    ratio = round(gen_dist / ref_dist, 4) if gen_dist is not None and ref_dist else None
    dups = []
    for pid, v in sorted(by_prompt.items()):
        for (sa, ea), (sb, eb) in combinations(sorted(v, key=lambda t: t[0]), 2):
            c = voice_audition._cos(ea, eb)
            if c > _t("duplicate_cos_max"):
                dups.append({"prompt": pid, "seeds": [sa, sb], "cosine": round(c, 4)})
    technical_ok = bool(per_prompt) and share >= _t("prompts_clean_min")
    variety_ok = ratio is not None and ratio >= _t("variety_ratio_min") and not dups
    return {"schema": REPORT_SCHEMA, "generator": generator, "model": model, "kind": kind, "rule": "BP-163",
            "takes": rows, "unmatched_files": unmatched, "prompts": per_prompt,
            "technical": {"prompts": len(per_prompt), "clean_prompts": clean, "clean_share": round(share, 4),
                          "misses_by_rule": counts, "pass": technical_ok},
            "variety": {"embedder": "numpy_mfcc13", "generator_mean_distance": None if gen_dist is None else round(gen_dist, 4),
                        "reference_mean_distance": None if ref_dist is None else round(ref_dist, 4), "reference_files": len(reference),
                        "ratio": ratio, "duplicates": dups, "pass": variety_ok},
            "pass": technical_ok and variety_ok}


def _mean_distance_across(groups: list[list[np.ndarray]]) -> float | None:
    """Mean (1 - cosine) over pairs of takes that belong to different prompts."""
    d = [1.0 - voice_audition._cos(x, y) for a, b in combinations(groups, 2) for x in a for y in b]
    return float(np.mean(d)) if d else None


def verdict(report: dict) -> list[str]:
    """What stops an admission, re-derived from the report's numbers and BP-163 (a hand-edited ``pass`` is not trusted)."""
    out = []
    if report.get("schema") != REPORT_SCHEMA:
        return [f"not a {REPORT_SCHEMA} document"]
    prompts = report.get("prompts") or {}
    clean = sum(1 for p in prompts.values() if p.get("clean"))
    if not prompts or clean / len(prompts) < _t("prompts_clean_min"):
        out.append(f"technical: {clean} of {len(prompts)} prompts are clean; BP-163 asks for at least {_t('prompts_clean_min'):g} of them")
    v = report.get("variety") or {}
    if v.get("ratio") is None or v["ratio"] < _t("variety_ratio_min"):
        out.append(f"variety: ratio {v.get('ratio')} against the reference set; BP-163 asks for at least {_t('variety_ratio_min'):g}")
    if v.get("duplicates"):
        out.append(f"variety: {len(v['duplicates'])} near-duplicate seed pair(s) above {_t('duplicate_cos_max'):g}")
    return out


# -- the blind sheet ---------------------------------------------------------------------------------------------------

def _level_pair(a: np.ndarray, b: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Both sides to their common RMS, so loudness never tells the generator from the reference (a louder side is preferred)."""
    ra = float(np.sqrt(np.mean(a.astype(np.float64) ** 2))) or 1e-9
    rb = float(np.sqrt(np.mean(b.astype(np.float64) ** 2))) or 1e-9
    target = (ra + rb) / 2
    a, b = a * (target / ra), b * (target / rb)
    peak = max(float(np.max(np.abs(a))), float(np.max(np.abs(b))), 1e-9)
    k = min(1.0, 0.89 / peak)
    return (a * k).astype(np.float32), (b * k).astype(np.float32)


def sheet(report: dict, out: Path, *, seed: int) -> Path:
    """The blind A/B sheet (markdown + ``pair_NN_A.wav`` / ``pair_NN_B.wav``): per prompt with a reference and a clean generator
    take, one of the take's seeds (drawn from ``seed``) against the reference, sides drawn from ``seed``. The sheet and the files
    never say which side is the generator; ``sheet_key.json`` does, and he opens it only after answering. Same seed, same bytes."""
    if report.get("schema") != REPORT_SCHEMA:
        raise ContractError(f"not a {REPORT_SCHEMA} document")
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    cands = []
    for pid in sorted(report["prompts"]):
        p = report["prompts"][pid]
        clean = [t for t in report["takes"] if t["prompt"] == pid and not t["misses"]]
        if p.get("reference") and clean:
            cands.append((pid, p, clean))
    rng.shuffle(cands)
    rows, key = [], []
    for n, (pid, p, clean) in enumerate(cands, 1):
        take = clean[rng.randrange(len(clean))]
        gen_is_a = rng.random() < 0.5
        gx, gr = _load(Path(take["file"]))
        rx, rr = _load(Path(p["reference"]))
        if rr != gr:  # one rate on both sides: a rate never gives the generator away
            ratio = rr / gr
            idx = np.arange(int(len(rx) / ratio)) * ratio
            rx = np.interp(idx, np.arange(len(rx)), rx).astype(np.float32)
        gx, rx = _level_pair(gx, rx)
        a, b = (gx, rx) if gen_is_a else (rx, gx)
        for side, x in (("A", a), ("B", b)):
            write_bytes = sfx_library.wav_bytes(x, gr)
            (out / f"pair_{n:02d}_{side}.wav").write_bytes(write_bytes)
        rows.append(f"| {n:02d} | {p.get('text') or pid} | pair_{n:02d}_A.wav | pair_{n:02d}_B.wav |  |")
        key.append({"pair": n, "prompt": pid, "generator_side": "A" if gen_is_a else "B", "seed": take["seed"],
                    "generator_file": Path(take["file"]).name, "reference_file": Path(p["reference"]).name})
    md = ["# Blind A/B listening sheet", "",
          f"Kind: {report['kind']}. Per pair, listen to A and B and write which one fits the prompt better: `A`, `B` or `same`.",
          "Which side is which is not shown here; do not open `sheet_key.json` before you have answered every pair.", "",
          "| Pair | Prompt | A | B | Your answer |", "|---|---|---|---|---|", *rows, ""]
    write_text_atomic(out / "sheet_key.json", json.dumps({"schema": KEY_SCHEMA, "seed": seed, "report_sha256": None,
                                                           "pairs": key}, indent=1) + "\n")
    path = out / "sheet.md"
    write_text_atomic(path, "\n".join(md))
    return path


# -- the admission -----------------------------------------------------------------------------------------------------

def admission_path(path: Path | str | None = None) -> Path:
    return Path(path) if path else Path(os.environ[ENV]) if os.environ.get(ENV) else ADMISSION


def load_admissions(path: Path | str | None = None) -> dict:
    p = admission_path(path)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"version": 1, "admissions": []}


def admitted(kind: str, *, path: Path | str | None = None) -> dict | None:
    """The standing admission (the latest record) for a kind, or None. With no file nothing is admitted."""
    found = [a for a in load_admissions(path)["admissions"] if a.get("kind") == kind]
    return found[-1] if found else None


def get(admission_id: str, *, path: Path | str | None = None) -> dict | None:
    return next((a for a in load_admissions(path)["admissions"] if a.get("id") == admission_id), None)


def _picks(sheet_md: Path, report_sha: str) -> dict:
    """The answered sheet against its key. The key (``sheet_key.json`` beside the sheet) must name this report's sha256, or the
    sheet belongs to another measurement. Returns how many of his answers (A / B / same) went to the generator and how many he gave;
    the ratio is recorded for the eye, no minimum is invented here (his recorded word is the gate, D8)."""
    key_path = sheet_md.parent / "sheet_key.json"
    if not key_path.is_file():
        raise ContractError(f"{key_path.name} is missing beside the sheet: it is written by `sheet` and proves which report the sheet is for")
    key = json.loads(key_path.read_text(encoding="utf-8"))
    if key.get("schema") != KEY_SCHEMA:
        raise ContractError(f"{key_path} is not a {KEY_SCHEMA} document")
    if key.get("report_sha256") != report_sha:
        raise ContractError(f"{key_path.name} was made for another report (report_sha256 {key.get('report_sha256')!r}, this report is "
                            f"{report_sha[:12]}...): make the sheet from this report")
    side = {f"{int(p['pair']):02d}": p["generator_side"].lower() for p in key.get("pairs", [])}
    given = total = 0
    for line in sheet_md.read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 5 and cells[0] in side and cells[-1].lower() in ("a", "b", "same"):
            total += 1
            given += cells[-1].lower() == side[cells[0]]
    return {"for_generator": given, "total": total}


def admit(generator: str, kind: str, report: Path, *, creator_ref: str, at: str, sheet: Path | None = None,
          prefer_rate: float | None = None, model: str = "", path: Path | str | None = None) -> dict:
    """Write one admission record. Refused without the creator's recorded word (``creator_ref`` = his message id, ``at`` = when),
    without the blind sheet he answered (and its key for this report), or when the report misses BP-163 (re-derived from its numbers,
    not from its ``pass``). ``creator_ref`` must resolve to a ``generator_admit`` record for ``<generator>:<kind>`` in
    ``jobs/creator_ok.jsonl`` (``governance ok``), the same lookup the channel voice uses (VC-08); a free string is not his word."""
    ref = creator_ref.strip() if isinstance(creator_ref, str) else ""
    if not ref:
        raise ContractError("creator_ref is blank: an admission needs the creator's recorded word (BP-162)")
    try:
        datetime.fromisoformat(str(at).strip().replace("Z", "+00:00"))
    except ValueError as exc:
        raise ContractError(f"at {at!r} is not an ISO time: {exc}") from exc
    if kind not in KINDS:
        raise ContractError(f"unknown kind {kind!r}; known: {KINDS}")
    if not generator.strip():
        raise ContractError("generator is blank")
    if sheet is None or not Path(sheet).is_file():
        raise ContractError("the blind A/B sheet he answered is missing (admit --sheet): quality is his ear, not a number (BP-163)")
    report = Path(report)
    doc = json.loads(report.read_text(encoding="utf-8"))
    if doc.get("kind") != kind:
        raise ContractError(f"the report measured kind {doc.get('kind')!r}, not {kind!r}")
    if doc.get("generator") and doc["generator"] != generator:
        raise ContractError(f"the report is for generator {doc['generator']!r}, not {generator!r}")
    problems = verdict(doc)
    if problems:
        raise ContractError("the report does not pass BP-163: " + "; ".join(problems))
    rsha = sha256_of(report)
    picks = _picks(Path(sheet), rsha)                       # the key must belong to this very report (it is the blind sheet's proof)
    if records.find("generator_admit", f"{generator}:{kind}", ref) is None:
        raise ContractError(f"BP-162: no recorded creator word {ref!r} for {generator}:{kind}: record it first (`python -m "
                            f"explainer_engine.governance ok generator_admit {generator}:{kind} <message id> \"<his words>\"`)")
    entry = {"id": f"{generator}-{kind}-{rsha[:8]}", "generator": generator, "model": model or doc.get("model", ""), "kind": kind,
             "report_sha256": rsha, "sheet_sha256": sha256_of(Path(sheet)), "prefer_rate": prefer_rate, "creator_ref": ref,
             "picks_for_generator": picks["for_generator"], "picks_total": picks["total"], "at": str(at).strip()}
    admissions = load_admissions(path)
    admissions["admissions"] = [a for a in admissions["admissions"] if a["id"] != entry["id"]] + [entry]
    write_json_atomic(admission_path(path), admissions)
    return entry


def item_problems(item: dict, *, path: Path | str | None = None) -> list[str]:
    """Why a library item of ``source.kind`` open_model is not allowed (SD-13's library half): no admission named, an admission the
    file does not hold, one for another kind or for another model. An item of any other source has no problem here."""
    src = item.get("source") or {}
    if src.get("kind") != "open_model":
        return []
    ident = item.get("id", "?")
    aid = src.get("admission")
    if not aid:
        return [f"{ident}: a free-generator take without an admission (BP-162): library first, then the connector"]
    adm = get(aid, path=path)
    if adm is None:
        return [f"{ident}: admission {aid!r} is not in {admission_path(path).name} (BP-162)"]
    out = []
    want = kind_of_item(item.get("category", ""), item.get("tags"))
    if want != adm["kind"]:
        out.append(f"{ident}: admission {aid!r} is for {adm['kind']}, this take is {want or 'a kind no generator is admitted for'} (BP-162)")
    if adm.get("model") and src.get("model") and src["model"] != adm["model"]:
        out.append(f"{ident}: admission {aid!r} is for model {adm['model']!r}, this take is from {src['model']!r} (BP-162)")
    return out


# -- CLI ---------------------------------------------------------------------------------------------------------------

def _reference_files(args: list[str]) -> list[Path]:
    out: list[Path] = []
    for a in args:
        p = Path(a)
        out += sorted(p.glob("*.wav")) if p.is_dir() else [p]
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("measure")
    m.add_argument("--takes", required=True)
    m.add_argument("--kind", required=True, choices=KINDS)
    m.add_argument("--prompts", required=True, help="JSON: prompt id -> {seconds, loop, text, reference}")
    m.add_argument("--reference", required=True, nargs="+", help="reference WAV files or folders (the library's ElevenLabs items)")
    m.add_argument("--generator", default="")
    m.add_argument("--model", default="")
    m.add_argument("--out", required=True)
    s = sub.add_parser("sheet")
    s.add_argument("report")
    s.add_argument("--out", required=True)
    s.add_argument("--seed", type=int, required=True)
    d = sub.add_parser("admit")
    d.add_argument("report")
    d.add_argument("--generator", required=True)
    d.add_argument("--kind", required=True, choices=KINDS)
    d.add_argument("--sheet", required=True)
    d.add_argument("--creator-ref", required=True)
    d.add_argument("--at", required=True)
    d.add_argument("--prefer-rate", type=float)
    d.add_argument("--model", default="")
    d.add_argument("--admissions", help="the admission file (default assets/audio/generator_admission.json)")
    t = sub.add_parser("status")
    t.add_argument("--kind", choices=KINDS)
    t.add_argument("--admissions")
    a = ap.parse_args(argv)
    if a.cmd == "measure":
        rep = measure(Path(a.takes), kind=a.kind, prompts=json.loads(Path(a.prompts).read_text(encoding="utf-8")),
                      reference=_reference_files(a.reference), generator=a.generator, model=a.model)
        write_json_atomic(Path(a.out), rep)
        print(f"technical: {rep['technical']['clean_prompts']}/{rep['technical']['prompts']} prompts clean "
              f"{rep['technical']['misses_by_rule']}; variety ratio {rep['variety']['ratio']}, "
              f"{len(rep['variety']['duplicates'])} duplicate pair(s); {'PASS' if rep['pass'] else 'does not pass'} (BP-163, REVIEW)")
        return 0 if rep["pass"] else 1
    if a.cmd == "sheet":
        rep = json.loads(Path(a.report).read_text(encoding="utf-8"))
        p = sheet(rep, Path(a.out), seed=a.seed)
        key = Path(a.out) / "sheet_key.json"
        doc = json.loads(key.read_text(encoding="utf-8"))
        doc["report_sha256"] = sha256_of(Path(a.report))
        write_json_atomic(key, doc)
        print(f"sheet: {p} (answer there; the key is {key.name}, opened after)")
        return 0
    if a.cmd == "admit":
        try:
            e = admit(a.generator, a.kind, Path(a.report), creator_ref=a.creator_ref, at=a.at, sheet=Path(a.sheet),
                      prefer_rate=a.prefer_rate, model=a.model, path=a.admissions)
        except ContractError as exc:
            print(f"refused: {exc}", file=sys.stderr)
            return 1
        print(f"admitted {e['generator']} for {e['kind']} as {e['id']} (his word: {e['creator_ref']})")
        return 0
    rows = [x for x in load_admissions(a.admissions)["admissions"] if not a.kind or x["kind"] == a.kind]
    for x in rows:
        print(f"{x['id']:40} {x['kind']:10} {x['generator']} {x['at']} {x['creator_ref']}")
    print(f"{len(rows)} admission(s) in {admission_path(a.admissions)}" + ("" if rows else ": none; library first, then the connector"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
