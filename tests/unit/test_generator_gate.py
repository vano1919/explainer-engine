"""The free-generator gate (P4, D8, BP-162, BP-163, SD-13): measured takes, the blind sheet, the admission and where it bites
(assets_reuse, the ElevenLabs hook, register, sfx_library.validate). Synthetic audio only; nothing paid, no network."""

from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pytest

from explainer_engine import assets_reuse as AR
from explainer_engine.audio import generator_gate as G
from explainer_engine.audio import register, sfx_library
from explainer_engine.core.errors import ContractError
from explainer_engine.governance import records
from explainer_engine.standards import hook
from explainer_engine.standards import sourced_rules as SR

RATE = 16000
BANDS = {"p1": (100, 300), "p2": (500, 900), "p3": (1500, 2500), "p4": (3000, 6000), "p5": (300, 500)}
SEED_SHIFT = (1.0, 1.35, 1.8)  # the three seeds of one prompt sit at different pitches: not near-duplicates


def band(lo, hi, seed, secs=2.0, rate=RATE, peak=0.4):
    x = np.random.default_rng(seed).standard_normal(int(secs * rate))
    spec = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / rate)
    spec[(f < lo) | (f > hi)] = 0
    y = np.fft.irfft(spec, len(x))
    env = np.minimum(1.0, np.minimum(np.arange(len(y)), np.arange(len(y))[::-1]) / (0.05 * rate))  # 50 ms fades
    return (peak * y / np.max(np.abs(y)) * env).astype(np.float32)


def write(path: Path, x, rate=RATE):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(sfx_library.wav_bytes(np.asarray(x, dtype=np.float32), rate))
    return path


def take_for(pid, s, secs=2.0):
    lo, hi = BANDS[pid]
    k = SEED_SHIFT[s]
    return band(lo * k, hi * k, seed=hash(pid) % 1000 + s, secs=secs)


def make_set(tmp_path, *, prompts=("p1", "p2", "p3", "p4"), secs=2.0):
    """A clean generator (3 seeds per prompt) and a reference set that sounds like the same variety of prompts."""
    takes, ref = tmp_path / "takes", tmp_path / "ref"
    for pid in prompts:
        for s in range(3):
            write(takes / f"{pid}__s{s}.wav", take_for(pid, s, secs))
        lo, hi = BANDS[pid]
        write(ref / f"{pid}.wav", band(lo * 1.1, hi * 1.1, seed=99, secs=secs))
    spec = {pid: {"seconds": secs, "text": f"prompt {pid}"} for pid in prompts}
    return takes, ref, spec


def run(tmp_path, **kw):
    takes, ref, spec = make_set(tmp_path)
    spec = kw.pop("prompts", spec)
    return G.measure(takes, kind=kw.pop("kind", "sfx"), prompts=spec, reference=sorted(ref.glob("*.wav")), generator="gen-x")


# --- measure ----------------------------------------------------------------------------------------------------------------

def test_a_clean_generator_passes_technical_and_variety(tmp_path):
    rep = run(tmp_path)
    assert rep["technical"] == {"prompts": 4, "clean_prompts": 4, "clean_share": 1.0, "misses_by_rule": {}, "pass": True}
    assert rep["variety"]["duplicates"] == [] and rep["variety"]["ratio"] >= SR.T("BP-163", "variety_ratio_min")
    assert rep["pass"] and G.verdict(rep) == []
    assert all(t["sha256"] and t["dc_offset"] is not None for t in rep["takes"])


def test_each_technical_rule_fires_once(tmp_path):
    takes, ref, spec = make_set(tmp_path, prompts=("p1", "p2", "p3", "p4"))
    spec["p5"] = {"seconds": 20.0, "loop": True, "text": "a bed"}
    t = np.arange(20 * 8000) / 8000
    bed = (0.3 * np.sin(2 * np.pi * 110 * t) + 0.2 * np.sin(2 * np.pi * 220 * t)).astype(np.float32)
    for s in range(3):
        write(takes / f"p5__s{s}.wav", bed, rate=8000)
    write(takes / "p1__s0.wav", take_for("p1", 0, secs=3.0))  # duration: asked 2 s, got 3 s
    lo, hi = BANDS["p2"]
    write(takes / "p2__s0.wav", np.concatenate([band(lo, hi, seed=5, secs=1.0), np.zeros(RATE, dtype=np.float32)]))  # half silent
    write(takes / "p3__s0.wav", np.clip(1.6 * np.sin(2 * np.pi * 440 * np.arange(2 * RATE) / RATE), -1, 1))  # clipped
    write(takes / "p5__s0.wav", bed * np.linspace(1.0, 0.1, len(bed)).astype(np.float32), rate=8000)  # the seam steps
    spec["p3"]["text"] = "a clipped one"
    rep = G.measure(takes, kind="sfx", prompts=spec, reference=sorted(ref.glob("*.wav")), generator="gen-x")
    assert rep["technical"]["misses_by_rule"] == {"duration": 1, "silence_share": 1, "clipped_share": 1, "loop_seam": 1}
    by = {(r["prompt"], r["seed"]): r["misses"] for r in rep["takes"] if r["misses"]}
    assert by == {("p1", 0): ["duration"], ("p2", 0): ["silence_share"], ("p3", 0): ["clipped_share"], ("p5", 0): ["loop_seam"]}
    assert rep["technical"]["clean_prompts"] == 1 and not rep["technical"]["pass"] and not rep["pass"]
    assert any("technical" in p for p in G.verdict(rep))


def test_eighty_percent_of_prompts_clean_is_enough(tmp_path):
    takes, ref, spec = make_set(tmp_path, prompts=("p1", "p2", "p3", "p4", "p5"))
    write(takes / "p1__s0.wav", take_for("p1", 0, secs=3.0))  # one bad take in one of five prompts = 0.8 clean
    rep = G.measure(takes, kind="sfx", prompts=spec, reference=sorted(ref.glob("*.wav")))
    assert rep["technical"]["clean_share"] == 0.8 and rep["technical"]["pass"]
    write(takes / "p2__s0.wav", take_for("p2", 0, secs=3.0))
    assert not G.measure(takes, kind="sfx", prompts=spec, reference=sorted(ref.glob("*.wav")))["technical"]["pass"]


def test_a_prompt_with_too_few_takes_is_not_clean(tmp_path):
    takes, ref, spec = make_set(tmp_path)
    (takes / "p4__s2.wav").unlink()
    rep = G.measure(takes, kind="sfx", prompts=spec, reference=sorted(ref.glob("*.wav")))
    assert rep["prompts"]["p4"]["takes_missing"] and not rep["prompts"]["p4"]["clean"]


def test_two_identical_seeds_are_one_near_duplicate(tmp_path):
    takes, ref, spec = make_set(tmp_path)
    write(takes / "p3__s1.wav", take_for("p3", 0))  # seed 1 is seed 0 again
    rep = G.measure(takes, kind="sfx", prompts=spec, reference=sorted(ref.glob("*.wav")))
    assert [(d["prompt"], d["seeds"]) for d in rep["variety"]["duplicates"]] == [("p3", [0, 1])]
    assert rep["technical"]["pass"] and not rep["variety"]["pass"] and not rep["pass"]
    assert any("near-duplicate" in p for p in G.verdict(rep))


def test_a_generator_that_sounds_the_same_for_every_prompt_fails_variety(tmp_path):
    takes, ref, spec = make_set(tmp_path)
    for pid in spec:
        for s in range(3):
            write(takes / f"{pid}__s{s}.wav", band(500 * SEED_SHIFT[s], 900 * SEED_SHIFT[s], seed=s))
    rep = G.measure(takes, kind="sfx", prompts=spec, reference=sorted(ref.glob("*.wav")))
    assert rep["variety"]["ratio"] < SR.T("BP-163", "variety_ratio_min") and not rep["variety"]["pass"]


def test_a_technical_miss_takes_the_take_out_of_the_variety_and_no_reference_cannot_pass(tmp_path):
    takes, ref, spec = make_set(tmp_path)
    rep = G.measure(takes, kind="sfx", prompts=spec, reference=[])
    assert rep["variety"]["ratio"] is None and not rep["pass"]
    with pytest.raises(ContractError):
        G.measure(takes, kind="vocal", prompts=spec, reference=[])


# --- the blind sheet --------------------------------------------------------------------------------------------------------

def _tree(d: Path):
    return {p.name: p.read_bytes() for p in sorted(d.iterdir())}


def test_the_sheet_is_deterministic_per_seed_and_blind(tmp_path):
    rep = run(tmp_path)
    one = G.sheet(rep, tmp_path / "s1", seed=7)
    G.sheet(rep, tmp_path / "s1b", seed=7)
    G.sheet(rep, tmp_path / "s2", seed=8)
    assert _tree(tmp_path / "s1") == _tree(tmp_path / "s1b")  # same seed, same bytes
    assert _tree(tmp_path / "s1") != _tree(tmp_path / "s2")
    md = one.read_text(encoding="utf-8")
    key = json.loads((tmp_path / "s1" / "sheet_key.json").read_text(encoding="utf-8"))
    assert len(key["pairs"]) == 4 and md.count("pair_") == 8
    for word in ("gen-x", "generator", "ElevenLabs", "reference", "__s", "p1__", "elevenlabs"):
        assert word not in md  # the sheet never says which side is which
    names = {p.name for p in (tmp_path / "s1").glob("*.wav")}
    assert names == {f"pair_{n:02d}_{s}.wav" for n in range(1, 5) for s in "AB"}  # neutral names, no take or seed in them
    sides = {k["generator_side"] for s in (7, 8, 9, 10) for k in _sheet_key(rep, tmp_path / f"k{s}", s)["pairs"]}
    assert sides == {"A", "B"}  # the side is drawn, not fixed
    first = {k["prompt"]: k for k in key["pairs"]}
    a, b = (sfx_library.read_wav(tmp_path / "s1" / f"pair_01_{s}.wav")[0] for s in "AB")
    assert abs(float(np.sqrt(np.mean(a ** 2))) - float(np.sqrt(np.mean(b ** 2)))) < 0.01 and first  # levelled: loudness gives nothing away


def _sheet_key(rep, out, seed):
    G.sheet(rep, out, seed=seed)
    return json.loads((out / "sheet_key.json").read_text(encoding="utf-8"))


def test_the_sheet_skips_prompts_without_a_clean_take_or_a_reference(tmp_path):
    takes, ref, spec = make_set(tmp_path)
    (ref / "p4.wav").unlink()
    rep = G.measure(takes, kind="sfx", prompts=spec, reference=sorted(ref.glob("*.wav")))
    key = _sheet_key(rep, tmp_path / "s", 1)
    assert sorted(k["prompt"] for k in key["pairs"]) == ["p1", "p2", "p3"]
    with pytest.raises(ContractError):
        G.sheet({"schema": "nope"}, tmp_path / "x", seed=1)


# --- the admission ----------------------------------------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _creators_word(monkeypatch):
    """BP-162: an admission needs a recorded creator word (`governance ok generator_admit <generator>:<kind> ...`). These tests
    stand in for it; the tests that name the refusal override this."""
    monkeypatch.setattr(records, "find", lambda action, target, message_id, **kw:
                        {"action": action, "target": target, "message_id": message_id} if action == "generator_admit" else None)


def _passing(tmp_path, kind="sfx", answer="A"):
    """A passing report, its blind sheet made like the `sheet` command makes it (the key names the report's sha256), and the sheet
    answered: every pair `answer`."""
    rep = run(tmp_path, kind=kind)
    path = tmp_path / "report.json"
    path.write_text(json.dumps(rep), encoding="utf-8")
    sheet_md = G.sheet(rep, tmp_path / "sheet", seed=3)
    key = sheet_md.parent / "sheet_key.json"
    doc = json.loads(key.read_text(encoding="utf-8"))
    doc["report_sha256"] = G.sha256_of(path)
    key.write_text(json.dumps(doc), encoding="utf-8")
    sheet_md.write_text(sheet_md.read_text(encoding="utf-8").replace(" |  |", f" | {answer} |"), encoding="utf-8")
    return rep, path, sheet_md


def test_admit_needs_his_word_and_a_passing_report(tmp_path):
    rep, path, sheet_md = _passing(tmp_path)
    adm = tmp_path / "adm.json"
    kw = dict(sheet=sheet_md, path=adm)
    for bad in ("", "   "):
        with pytest.raises(ContractError, match="creator_ref"):
            G.admit("gen-x", "sfx", path, creator_ref=bad, at="2026-10-31T10:00:00Z", **kw)
    with pytest.raises(ContractError, match="ISO"):
        G.admit("gen-x", "sfx", path, creator_ref="cmsg_1", at="yesterday", **kw)
    with pytest.raises(ContractError, match="sheet"):
        G.admit("gen-x", "sfx", path, creator_ref="cmsg_1", at="2026-10-31T10:00:00Z", sheet=None, path=adm)
    with pytest.raises(ContractError, match="kind"):
        G.admit("gen-x", "music", path, creator_ref="cmsg_1", at="2026-10-31T10:00:00Z", **kw)
    with pytest.raises(ContractError, match="generator"):
        G.admit("other", "sfx", path, creator_ref="cmsg_1", at="2026-10-31T10:00:00Z", **kw)
    assert not adm.exists() and G.admitted("sfx", path=adm) is None
    failing = dict(rep, prompts={k: dict(v, clean=False) for k, v in rep["prompts"].items()}, **{"pass": True})  # a hand-set pass
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(failing), encoding="utf-8")
    with pytest.raises(ContractError, match="BP-163"):
        G.admit("gen-x", "sfx", bad, creator_ref="cmsg_1", at="2026-10-31T10:00:00Z", **kw)
    assert not adm.exists()


def test_admit_refuses_a_creator_ref_that_is_not_a_recorded_word(tmp_path, monkeypatch):
    """BP-162: any non-empty string used to pass. The ref now resolves like the channel voice's (`records.find`)."""
    _, path, sheet_md = _passing(tmp_path)
    adm = tmp_path / "adm.json"
    asked = []
    monkeypatch.setattr(records, "find", lambda *a, **kw: asked.append(a) or None)
    with pytest.raises(ContractError, match=r"governance ok generator_admit gen-x:sfx"):
        G.admit("gen-x", "sfx", path, creator_ref="cmsg_made_up", at="2026-10-31T10:00:00Z", sheet=sheet_md, path=adm)
    assert asked == [("generator_admit", "gen-x:sfx", "cmsg_made_up")] and not adm.exists()
    assert "generator_admit" in records.ACTIONS


def test_admit_refuses_a_key_made_for_another_report_or_missing(tmp_path):
    rep, path, sheet_md = _passing(tmp_path)
    adm = tmp_path / "adm.json"
    key = sheet_md.parent / "sheet_key.json"
    good = key.read_text(encoding="utf-8")
    doc = json.loads(good)
    doc["report_sha256"] = "0" * 64
    key.write_text(json.dumps(doc), encoding="utf-8")
    with pytest.raises(ContractError, match="another report"):
        G.admit("gen-x", "sfx", path, creator_ref="cmsg_1", at="2026-10-31T10:00:00Z", sheet=sheet_md, path=adm)
    doc["report_sha256"] = None                        # a key `sheet()` wrote and the CLI never bound
    key.write_text(json.dumps(doc), encoding="utf-8")
    with pytest.raises(ContractError, match="another report"):
        G.admit("gen-x", "sfx", path, creator_ref="cmsg_1", at="2026-10-31T10:00:00Z", sheet=sheet_md, path=adm)
    key.unlink()
    with pytest.raises(ContractError, match="sheet_key.json is missing"):
        G.admit("gen-x", "sfx", path, creator_ref="cmsg_1", at="2026-10-31T10:00:00Z", sheet=sheet_md, path=adm)
    assert not adm.exists()
    key.write_text(good, encoding="utf-8")
    assert G.admit("gen-x", "sfx", path, creator_ref="cmsg_1", at="2026-10-31T10:00:00Z", sheet=sheet_md, path=adm)["creator_ref"] == "cmsg_1"


def test_admit_records_his_picks_for_the_eye_and_invents_no_minimum(tmp_path):
    rep, path, sheet_md = _passing(tmp_path, answer="A")
    key = json.loads((sheet_md.parent / "sheet_key.json").read_text(encoding="utf-8"))
    pairs = len(key["pairs"])
    on_a = sum(p["generator_side"] == "A" for p in key["pairs"])
    e = G.admit("gen-x", "sfx", path, creator_ref="cmsg_1", at="2026-10-31T10:00:00Z", sheet=sheet_md, path=tmp_path / "adm.json")
    assert (e["picks_for_generator"], e["picks_total"]) == (on_a, pairs)             # "A" went to the generator on exactly those pairs
    answered = sheet_md.read_text(encoding="utf-8")
    sheet_md.write_text(re.sub(r"\| A \|$", "|  |", answered, count=1, flags=re.M), encoding="utf-8")   # one pair left blank
    with pytest.raises(ContractError, match="answer every pair"):
        G.admit("gen-x", "sfx", path, creator_ref="cmsg_1", at="2026-10-31T10:00:00Z", sheet=sheet_md, path=tmp_path / "adm2.json")
    sheet_md.write_text(re.sub(r"\| A \|$", "|  |", answered, flags=re.M), encoding="utf-8")            # no pair answered
    with pytest.raises(ContractError, match="answer every pair"):
        G.admit("gen-x", "sfx", path, creator_ref="cmsg_1", at="2026-10-31T10:00:00Z", sheet=sheet_md, path=tmp_path / "adm2.json")
    assert not (tmp_path / "adm2.json").exists()
    assert SR.rule("BP-162")["thresholds"] == {}


def test_admit_writes_the_record_and_admitted_reads_it(tmp_path, monkeypatch):
    rep, path, sheet_md = _passing(tmp_path)
    adm = tmp_path / "adm.json"
    e = G.admit("gen-x", "sfx", path, creator_ref="cmsg_9", at="2026-10-31T10:00:00Z", sheet=sheet_md, prefer_rate=0.6,
                model="m-1", path=adm)
    assert e["report_sha256"] == G.sha256_of(path) and e["sheet_sha256"] == G.sha256_of(sheet_md)
    assert (e["generator"], e["kind"], e["model"], e["prefer_rate"], e["creator_ref"]) == ("gen-x", "sfx", "m-1", 0.6, "cmsg_9")
    assert G.admitted("sfx", path=adm) == e and G.get(e["id"], path=adm) == e
    assert G.admitted("music", path=adm) is None  # only the kind he admitted
    monkeypatch.setenv(G.ENV, str(adm))
    assert G.admitted("sfx") == e  # the env var points the code at another file
    monkeypatch.setenv(G.ENV, str(tmp_path / "none.json"))
    assert G.admitted("sfx") is None  # no file, nothing admitted
    assert G.ADMISSION.name == "generator_admission.json" and not G.ADMISSION.exists()  # today nothing is admitted in the repo


def test_cli_measure_sheet_admit_status(tmp_path, capsys):
    takes, ref, spec = make_set(tmp_path)
    (tmp_path / "prompts.json").write_text(json.dumps(spec), encoding="utf-8")
    rp, adm = tmp_path / "r.json", tmp_path / "adm.json"
    assert G.main(["measure", "--takes", str(takes), "--kind", "sfx", "--prompts", str(tmp_path / "prompts.json"), "--reference",
                   str(ref), "--generator", "gen-x", "--out", str(rp)]) == 0
    assert G.main(["sheet", str(rp), "--out", str(tmp_path / "sh"), "--seed", "5"]) == 0
    assert G.main(["status", "--admissions", str(adm)]) == 0 and "none" in capsys.readouterr().out
    base = ["admit", str(rp), "--generator", "gen-x", "--kind", "sfx", "--sheet", str(tmp_path / "sh" / "sheet.md"),
            "--admissions", str(adm), "--at", "2026-10-31T10:00:00Z"]
    assert G.main(base + ["--creator-ref", " "]) == 1 and not adm.exists()
    assert G.main(base + ["--creator-ref", "cmsg_2"]) == 1 and not adm.exists()          # the sheet is still blank
    blank = (tmp_path / "sh" / "sheet.md").read_text(encoding="utf-8")
    (tmp_path / "sh" / "sheet.md").write_text(re.sub(r"\|  \|$", "| A |", blank, flags=re.M), encoding="utf-8")
    assert G.main(base + ["--creator-ref", "cmsg_2"]) == 0 and G.admitted("sfx", path=adm)["creator_ref"] == "cmsg_2"


# --- where it bites ---------------------------------------------------------------------------------------------------------

def _admit_sfx(tmp_path, monkeypatch):
    _, path, sheet_md = _passing(tmp_path)
    adm = tmp_path / "adm.json"
    e = G.admit("gen-x", "sfx", path, creator_ref="cmsg_9", at="2026-10-31T10:00:00Z", sheet=sheet_md, model="m-1", path=adm)
    monkeypatch.setenv(G.ENV, str(adm))
    return e, adm


def test_register_refuses_an_open_model_take_without_the_right_admission(tmp_path, monkeypatch):
    src = write(tmp_path / "take.wav", take_for("p1", 0))
    lib = tmp_path / "lib"
    kw = dict(root=lib, name="door_slam", take=1, category="foley", tags=["door"], model="m-1", source_kind="open_model",
              licence_status="cc0", licence_note="the model's own terms")
    with pytest.raises(ContractError, match="without an admission"):
        register.register(src, **kw)  # no admission named
    monkeypatch.setenv(G.ENV, str(tmp_path / "none.json"))
    with pytest.raises(ContractError, match="not in"):
        register.register(src, admission="gen-x-sfx-00000000", **kw)  # no file at all
    e, adm = _admit_sfx(tmp_path, monkeypatch)
    with pytest.raises(ContractError, match="is for sfx"):
        register.register(src, **dict(kw, category="music", name="a_bed"), admission=e["id"])  # a music take, an sfx admission
    with pytest.raises(ContractError, match="is for sfx"):
        register.register(src, **dict(kw, tags=["room_tone"], name="a_room"), admission=e["id"])  # room tone is its own kind
    with pytest.raises(ContractError, match="model"):
        register.register(src, **dict(kw, model="m-2"), admission=e["id"])
    with pytest.raises(ContractError, match="licence"):
        register.register(src, **dict(kw, licence_note=register.DEFAULT_LICENCE_NOTE), admission=e["id"])
    assert not (lib / "manifest.json").exists()  # nothing was stored by a refusal
    item = register.register(src, admission=e["id"], seed=4, **kw)
    assert item["source"] == {"kind": "open_model", "model": "m-1", "prompt": "", "cost_usd_estimate": 0.0, "seed": 4,
                              "admission": e["id"]}
    assert sfx_library.validate(lib) == []


def test_register_cli_refuses_with_exit_1_and_still_registers_connector_takes(tmp_path, monkeypatch, capsys):
    src = write(tmp_path / "take.wav", take_for("p1", 0))
    monkeypatch.setenv(G.ENV, str(tmp_path / "none.json"))
    base = [str(src), "--root", str(tmp_path / "lib"), "--name", "x", "--category", "foley", "--tags", "door"]
    assert register.main(base + ["--source-kind", "open_model", "--model", "m", "--licence-note", "n"]) == 1
    assert "refused" in capsys.readouterr().out
    assert register.main(base) == 0 and sfx_library.find(tmp_path / "lib", tags=["door"])[0]["source"]["kind"] == "elevenlabs"


def test_validate_refuses_an_open_model_item_whose_admission_is_missing_or_for_another_kind(tmp_path, monkeypatch):
    e, adm = _admit_sfx(tmp_path, monkeypatch)
    lib = tmp_path / "lib"
    for n, (aid, tags, cat) in enumerate(((None, ["door"], "foley"), ("nope", ["door"], "foley"), (e["id"], ["door"], "music"),
                                          (e["id"], ["door"], "foley"))):
        src = {"kind": "open_model", "model": "m-1"}
        if aid:
            src["admission"] = aid
        sfx_library.add(lib, name=f"t_{cat}_{n}", take=1, category=cat, tags=tags, samples=take_for("p1", 0), rate=RATE,
                        source=src, licence={"status": "cc0", "note": "n"})
    problems = sfx_library.validate(lib, admissions=adm)
    assert len(problems) == 3
    assert any("without an admission" in p for p in problems) and any("'nope'" in p for p in problems)
    assert any("is for sfx, this take is music" in p for p in problems)
    assert not any("t_foley_3__v1" in p for p in problems)  # the right admission for the right kind and model passes


def test_assets_reuse_generate_free_needs_an_admission_and_generate_new_needs_a_why_once_one_exists(tmp_path, monkeypatch):
    monkeypatch.setenv(G.ENV, str(tmp_path / "none.json"))
    with pytest.raises(ValueError, match="no free generator"):
        AR.record(tmp_path, kind="sfx", tags=["door"], matches=[], decision="generate_free")
    AR.record(tmp_path, kind="sfx", tags=["door"], matches=[], decision="generate_new")  # today's behaviour: unchanged
    assert AR.paid_justified(tmp_path, "sfx")
    e, _ = _admit_sfx(tmp_path, monkeypatch)
    ep = tmp_path / "ep2"
    ep.mkdir()
    assert not AR.paid_justified(ep, "sfx") and AR.paid_justified(ep, "music")  # only the admitted kind
    with pytest.raises(ValueError, match="what the free take could not do"):
        AR.record(ep, kind="sfx", tags=["door"], matches=[], decision="generate_new")  # even with no library match
    entry = AR.record(ep, kind="sfx", tags=["door"], matches=[], decision="generate_free")
    assert entry["generator"] == e["id"] and AR.has_lookup(ep, "sfx") and not AR.paid_justified(ep, "sfx")
    AR.record(ep, kind="sfx", tags=["door"], matches=[], decision="generate_new", why="the free take has no wood in it")
    assert AR.paid_justified(ep, "sfx")


def test_hook_refuses_a_paid_sfx_call_while_a_generator_is_admitted_and_no_reason_is_recorded(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    (root / ".claude").mkdir(parents=True)
    (root / ".claude" / "active_episode.json").write_text(json.dumps({"episode": "ep"}), encoding="utf-8")
    (root / "ep").mkdir()
    call = {"node_type": "sound-effect-generation", "generations_count": 1}
    tool = "mcp__ElevenLabs__creative_generate_in_flow"
    monkeypatch.setenv(G.ENV, str(tmp_path / "none.json"))
    AR.record(root / "ep", kind="sfx", tags=["door"], matches=[], decision="generate_new")
    reason = hook.decide(tool, call, root)
    assert reason and "OR-11" in reason  # no admission: past the library gate, the rulebook gate still stands
    _admit_sfx(tmp_path, monkeypatch)
    reason = hook.decide(tool, call, root)
    assert reason and reason.startswith("BP-162") and "--why" in reason and "sfx" in reason
    AR.record(root / "ep", kind="sfx", tags=["door"], matches=[], decision="generate_new", why="needs a real wooden creak")
    reason = hook.decide(tool, call, root)
    assert reason and "OR-11" in reason  # justified: on to the rulebook gate
    assert "BP-162" not in (hook.decide(tool, {"node_type": "music-generation", "generations_count": 1}, root) or "")  # music not admitted
