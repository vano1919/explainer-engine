"""The stereo mix of the sound director (P4, production/assemble.py ``build_audio_v2``): short synthetic audio, a stub sound
library, no network. The LUFS check needs ffmpeg and carries the ``media`` marker; the old mono path stays pinned by the existing
assemble tests (``build_audio`` is untouched)."""

from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pytest

from explainer_engine.audio import acoustics as A
from explainer_engine.audio import duck, sfx_library
from explainer_engine.audio import sound_director as SD
from explainer_engine.production import assemble as ASM
from explainer_engine.qa import targets
from explainer_engine.standards import sourced_rules as SR

SRATE = ASM.SR
FPS = 50
ROOT = Path(__file__).resolve().parents[2]


class Stub:
    """A sound library of arrays: ``load(ref)`` and ``loopable(ref)`` are all the mixer asks of it."""

    def __init__(self, items: dict | None = None, meta: dict | None = None):
        self.items, self.meta = items or {}, meta or {}

    def load(self, ref):
        return np.asarray(self.items[ref], dtype=np.float64)

    def loopable(self, ref):
        return True


def noise(seconds: float, seed: int = 1, amp: float = 0.2) -> np.ndarray:
    return (np.random.default_rng(seed).standard_normal(int(seconds * SRATE)) * amp).astype(np.float32)


def speechlike(total_s: float, stretches: list[tuple[float, float]], seed: int = 3) -> tuple[np.ndarray, list[dict]]:
    """Band-limited noise inside the stretches (one word every 0.4 s) and silence between them."""
    x = np.zeros(int(total_s * SRATE), np.float32)
    words = []
    body = A.F._band(noise(total_s, seed, 0.3), 150, 3500)
    for a, z in stretches:
        x[int(a * SRATE):int(z * SRATE)] = body[int(a * SRATE):int(z * SRATE)]
        t = a
        while t + 0.35 <= z:
            words.append({"start_frame": round(t * FPS), "end_frame": round((t + 0.35) * FPS)})
            t += 0.4
    return x, words


def spine_of(words, total, windows=()):
    return {"fps": FPS, "words": words, "post_hoc_shots": list(windows), "total_frames": total, "segments": []}


def manifest_of(total: int, **kw) -> dict:
    m = {"schema": "sound_mix_manifest/2", "fps": FPS, "total_frames": total,
         "scenes": [{"scene": "S01", "start_frame": 0, "end_frame": total, "acoustic": "neutral", "acoustic_source": "declared", "ir_seed": 5,
                     "entry": "butt", "lead_frames": 0}], "beds": [], "music": [], "vacuums": [], "cues": [], "spots": [], "dialogue": []}
    m.update(kw)
    return m


def spot(ref="s", frame=100, pan=0.0, persp="mid", gain=-12.0, **kw):
    return {"id": kw.pop("id", "sp001"), "shot_id": "a", "ref": ref, "word_index": None, "frame": frame, "stem": "sfx", "pan": pan,
            "perspective": persp, "gain_db": gain, "group": None, "layer": "single", "origin": "foley", **kw}


def render(manifest, spine, nar, items=None, meta=None):
    stats: dict = {}
    mix, stems = ASM.build_audio_v2(manifest, spine, nar, Stub(items, meta), stats)
    return mix, stems, stats


def mid(x):
    return x.mean(axis=1) if x.ndim == 2 else x


# --- pan, centre -------------------------------------------------------------------------------------------------------------

def test_a_focal_spot_pans_right_by_the_constant_power_amount_and_the_narration_and_cues_stay_centred():
    total = 10 * FPS
    nar, words = speechlike(10, [(1.0, 4.0)])
    p = 0.36  # focal 0.9 with BP-121's range (0.45)
    click = noise(0.5, 2, 0.4)
    m = manifest_of(total, spots=[spot("s", 300, p, "near")], cues=[{"name": "tick", "frame": 50, "gain_db": -26.0, "max_ms": None}])
    mix, stems, _ = render(m, spine_of(words, total), nar, {"s": click})
    assert mix.shape == (total * SRATE // FPS, 2) and mix.dtype == np.float32
    seg = stems["sfx"][300 * SRATE // FPS:300 * SRATE // FPS + len(click)]
    theta = (p + 1) * np.pi / 4
    want = 20 * np.log10(np.sin(theta) / np.cos(theta))
    got = A.rms_db(seg[:, 1]) - A.rms_db(seg[:, 0])
    assert want > 4 and abs(got - want) < 0.3  # the right channel louder by the pan law (neutral room: no impulse response)
    assert np.array_equal(stems["narration"][:, 0], stems["narration"][:, 1])
    assert np.array_equal(stems["cues"][:, 0], stems["cues"][:, 1]) and np.abs(stems["cues"]).max() > 0
    left = render(manifest_of(total, spots=[spot("s", 300, -0.36, "near")]), spine_of(words, total), nar, {"s": click})[1]["sfx"]
    seg = left[300 * SRATE // FPS:300 * SRATE // FPS + len(click)]
    assert A.rms_db(seg[:, 0]) > A.rms_db(seg[:, 1]) + 4  # focal 0.1: the left


def test_the_stems_add_up_to_the_mix_before_the_peak_scale_is_the_only_difference():
    total = 12 * FPS
    nar, words = speechlike(12, [(1.0, 5.0)])
    m = manifest_of(total, music=[{"id": "mu01", "ref": "m", "motif_of": None, "start_frame": 0, "end_frame": total, "gain_db": -20.0,
                                   "fade_in_frames": 50, "fade_out_frames": 100, "beat_grid": None}],
                    spots=[spot("s", 400, 0.2, "far")])
    mix, stems, _ = render(m, spine_of(words, total), nar, {"m": noise(12, 4), "s": noise(0.4, 5, 0.4)})
    parts = sum(stems[k] for k in ("narration", "music", "sfx", "ambience", "cues"))
    assert np.abs(parts - mix).max() < 1e-4
    assert "room_tone" in stems and stems["music"].dtype == np.float32 and stems["music"].shape == mix.shape
    assert np.abs(mix).max() <= 0.89 + 1e-6


# --- the presence-band dip (SD-04) ------------------------------------------------------------------------------------------

def _dip_case(monkeypatch=None, dip=True):
    total = 40 * FPS
    nar, words = speechlike(40, [(2.0, 12.0), (20.0, 30.0)])
    pink = A.room_tone("room", 9, 40.0)
    m = manifest_of(total, music=[{"id": "mu01", "ref": "m", "motif_of": None, "start_frame": 0, "end_frame": total, "gain_db": -18.0,
                                   "fade_in_frames": 0, "fade_out_frames": 0, "beat_grid": None}])
    if not dip and monkeypatch is not None:
        monkeypatch.setattr(ASM.acoustics, "band_dip", lambda x, *a, **k: x)
    spine = spine_of(words, total)
    mix, stems, stats = render(m, spine, nar, {"m": pink})
    out = SD.check(m, spine=spine, timeline=[], stems=dict(stems, mix=mix))
    return [f for f in out if f["rule"] == "SD-04"], stems, spine


def test_the_music_leaves_the_voice_band_under_speech_and_without_the_dip_sd04_fires(monkeypatch):
    on, stems, spine = _dip_case()
    assert on == []
    lo, hi = SR.T("BP-118", "measure_band_hz")
    speech, pause = SD.speech_masks(spine, len(stems["music"]))
    s_in, s_out = (A.band_share(stems["music"], SRATE, lo, hi, m) for m in (speech, pause))
    assert 10 * np.log10(s_in / s_out) <= -SR.T("BP-118", "notch_depth_db")[0]
    off, _stems, _ = _dip_case(monkeypatch, dip=False)
    assert [f["rule"] for f in off] == ["SD-04"] and off[0]["severity"] == SR.level("BP-118", SR.severity("BP-118"))


# --- vacuums (SD-06) --------------------------------------------------------------------------------------------------------

def test_a_vacuum_pulls_the_background_to_the_registry_level_in_a_dip_not_a_cut_and_leaves_the_hit_alone():
    total = 30 * FPS
    nar, words = speechlike(30, [(1.0, 8.0)])
    music = {"id": "mu01", "ref": "m", "motif_of": None, "start_frame": 0, "end_frame": total, "gain_db": -18.0, "fade_in_frames": 0,
             "fade_out_frames": 0, "beat_grid": None}
    bed = {"id": "amb01", "scene": "S01", "kind": "ambience", "ref": "b", "gain_db": -26.0, "start_frame": 0, "end_frame": total,
           "fade_in_frames": 0, "fade_out_frames": 0}
    hit = [spot("h", 700, 0.0, "mid", -16.0, id=f"sp00{k}", group="hit@700", layer=layer, origin="hit") for k, layer in enumerate(("sub", "body", "air"), 1)]
    base = manifest_of(total, music=[music], beds=[bed], spots=hit)
    items = {"m": noise(30, 4), "b": noise(30, 6), "h": noise(0.3, 7, 0.5)}
    spine = spine_of(words, total)
    plain = render(base, spine, nar, items)
    vac = dict(base, vacuums=[{"start_frame": 650, "end_frame": 700, "reason": "reveal", "reveal_frame": 700}])  # a 1.0 s pause
    mix, stems, stats = render(vac, spine, nar, items)
    a, z = 650 * SRATE // FPS, 700 * SRATE // FPS
    ramp = int(SD.VACUUM_RAMP_MS / 1000 * SRATE)
    target = SR.T("BP-120", "vacuum_dbfs")
    for name in ("music", "ambience"):
        level = A.rms_db(mid(stems[name][a + ramp:z]))
        assert abs(level - target) <= 1.0, (name, level)
    # a dip, not a cut: the ratio to the render without the vacuum never steps faster than BP-53's limit, and it is back after the release
    for name in ("music", "ambience"):
        blocks = lambda x: np.sqrt((mid(x)[: len(x) // 48 * 48].reshape(-1, 48) ** 2).mean(axis=1) + 1e-18)  # noqa: E731
        ratio = blocks(stems[name]) / blocks(plain[1][name])
        assert duck.max_step_db_per_ms(np.repeat(ratio, 48), SRATE) <= SR.T("BP-53", "max_step_db_per_ms") + 0.05
        assert abs(20 * np.log10(ratio[(z + SRATE) // 48])) < 0.2  # the release has finished a second after the reveal
    # the hit starts on its frame and is not pulled
    hit_seg = (stems["sfx"][z:z + 4800], plain[1]["sfx"][z:z + 4800])
    assert np.abs(hit_seg[0]).max() > 0 and np.allclose(hit_seg[0], hit_seg[1], atol=1e-6)
    assert [v["pull_db"] < 0 for v in stats["vacuums"]["music"]] == [True]
    # narration and room tone are outside the curve
    assert np.array_equal(stems["narration"], plain[1]["narration"]) and np.array_equal(stems["room_tone"], plain[1]["room_tone"])


# --- room tone, perspective -------------------------------------------------------------------------------------------------

def test_room_tone_lands_in_bp116_s_band_and_a_close_spot_keeps_more_of_the_top_than_a_wide_one():
    total = 20 * FPS
    nar, words = speechlike(20, [(1.0, 3.0)])
    lo, hi = SR.T("BP-116", "room_tone_dbfs")
    tone = A.room_tone("room", 2, 30.0)
    crest = 20 * np.log10(np.abs(tone).max() / (np.sqrt(np.mean(tone.astype(np.float64) ** 2))))
    gain = (lo + hi) / 2 + crest
    rt = {"id": "rt01", "scene": "S01", "kind": "room_tone", "ref": "rt", "gain_db": gain, "start_frame": 0, "end_frame": total,
          "fade_in_frames": 0, "fade_out_frames": 0}
    burst = noise(0.8, 3, 0.4)
    m = manifest_of(total, beds=[rt], spots=[spot("n", 500, 0.0, "far", id="sp001"), spot("n", 700, 0.0, "near", id="sp002")])
    m["scenes"][0]["acoustic"] = "room"
    mix, stems, _ = render(m, spine_of(words, total), nar, {"rt": tone, "n": burst}, {"rt": {"source": {"kind": "procedural"}}})
    quiet = stems["room_tone"][10 * SRATE:18 * SRATE]  # long after the words: the duck has released
    assert lo - 0.5 <= A.rms_db(quiet[:, 0]) <= hi + 0.5
    assert A.band_share(quiet, SRATE, 0, SR.T("BP-116", "hpf_hz") / 2) < 1e-2  # nothing below the high-pass
    n_ = len(burst)
    far, near = (stems["sfx"][f * SRATE // FPS:f * SRATE // FPS + n_ + 4000] for f in (500, 700))
    assert A.band_share(far, SRATE, 6000, 20000) < A.band_share(near, SRATE, 6000, 20000) - 0.01  # BP-122: the wide shot loses the top
    wet = lambda x: A.rms_db(x[n_:])  # noqa: E731  the tail after the sound: the room's decay
    assert wet(far) > wet(near)  # more of the room in the wide shot


def test_the_room_tone_has_no_digital_silence_even_where_nothing_else_plays():
    total = 8 * FPS
    nar = np.zeros(total * SRATE // FPS, np.float32)
    lo, hi = SR.T("BP-116", "room_tone_dbfs")
    tone = A.room_tone("hall", 3, 30.0)
    crest = 20 * np.log10(np.abs(tone).max() / np.sqrt(np.mean(tone.astype(np.float64) ** 2)))
    rt = {"id": "rt01", "scene": "S01", "kind": "room_tone", "ref": "rt", "gain_db": (lo + hi) / 2 + crest, "start_frame": 0, "end_frame": total,
          "fade_in_frames": 0, "fade_out_frames": 0}
    m = manifest_of(total, beds=[rt])
    m["scenes"][0]["acoustic"] = "hall"
    words = [{"start_frame": 10, "end_frame": 20}]
    mix, stems, _ = render(m, spine_of(words, total), nar, {"rt": tone}, {"rt": {"source": {"kind": "procedural"}}})
    assert not [f for f in SD.check(m, spine=spine_of(words, total), timeline=[], stems=dict(stems, mix=mix)) if f["rule"] == "SD-02"]
    bare = manifest_of(total)
    mix2, stems2, _ = render(bare, spine_of(words, total), nar)
    assert [f["rule"] for f in SD.check(bare, spine=spine_of(words, total), timeline=[], stems=dict(stems2, mix=mix2)) if f["rule"] == "SD-02"] == ["SD-02"]


# --- dialogue windows (D-88) ------------------------------------------------------------------------------------------------

def test_the_narrator_waits_in_a_dialogue_window_and_a_missing_clip_leaves_the_room_tone():
    fps_total = 20 * FPS
    read_s = 18.0  # the read is 2 s shorter than the film: one 2 s window
    nar = np.zeros(int(read_s * SRATE), np.float32)
    nar[int(14.0 * SRATE)] = 1.0  # a click at 14 s of the read, which is 16 s of the film
    nar[int(2.0 * SRATE)] = 0.5
    win = {"shot_id": "d", "start_frame": 10 * FPS, "end_frame": 12 * FPS, "after_word": 0, "source": "planned", "clip_sha256": None}
    words = [{"start_frame": 2 * FPS, "end_frame": 2 * FPS + 10}, {"start_frame": 16 * FPS, "end_frame": 16 * FPS + 10}]
    m = manifest_of(fps_total, dialogue=[{"shot_id": "d", "ref": None, "start_frame": win["start_frame"], "end_frame": win["end_frame"]}])
    spine = spine_of(words, fps_total, [win])
    mix, stems, _ = render(m, spine, nar)
    n_ = stems["narration"][:, 0]
    assert abs(int(np.argmax(np.abs(n_))) - int(16.0 * SRATE)) <= 8  # the click moved by the window
    a, z = 10 * SRATE, 12 * SRATE
    assert np.abs(n_[a:z]).max() == 0.0 and "dialogue" in stems and np.abs(stems["dialogue"]).max() == 0.0  # the clip is absent
    assert abs(int(np.argmax(np.abs(n_[: 10 * SRATE]))) - int(2.0 * SRATE)) <= 8  # before the window nothing moved
    clip = noise(2.0, 8, 0.3)
    m2 = manifest_of(fps_total, dialogue=[{"shot_id": "d", "ref": "clip", "start_frame": win["start_frame"], "end_frame": win["end_frame"]}])
    _mix, stems2, _ = render(m2, spine, nar, {"clip": clip})
    d = stems2["dialogue"][:, 0]
    assert np.abs(d[a + 2400:z - 2400]).max() > 0 and np.abs(d[:a]).max() == 0.0 and np.abs(d[z:]).max() == 0.0
    assert np.array_equal(stems2["dialogue"][:, 0], stems2["dialogue"][:, 1])  # centred


# --- selection, stems on disk, the old path -------------------------------------------------------------------------------------

def test_a_job_without_a_manifest_takes_the_old_path_and_a_stale_manifest_stops_the_render(tmp_path):
    assert ASM.v2_manifest(None) is None and ASM.v2_manifest(tmp_path) is None
    job, _path = _fresh_job(tmp_path)
    (job / "timed.json").write_bytes((job / "timed.json").read_bytes() + b" ")  # one byte: the plan is stale
    with pytest.raises(SystemExit) as exc:
        ASM.v2_manifest(job)
    assert "SD-15" in str(exc.value) and "stale" in str(exc.value)
    assert ASM.build_audio.__module__ == ASM.__name__ and "manifest" not in ASM.build_audio.__code__.co_varnames  # the mono path is untouched


def test_the_stems_are_written_as_wavs_and_read_back_by_the_checker(tmp_path):
    x = (np.random.default_rng(1).standard_normal((SRATE, 2)) * 0.1).astype(np.float32)
    mono = np.broadcast_to(x[:, :1], (SRATE, 2))
    paths = ASM.write_stems({"music": x, "narration": mono}, tmp_path / "stems")
    assert [p.name for p in paths] == ["music.wav", "narration.wav"]
    back = SD._load_stems(tmp_path / "stems")
    assert back["music"].shape == (SRATE, 2) and np.abs(back["music"] - x).max() < 1e-4
    assert np.array_equal(back["narration"][:, 0], back["narration"][:, 1])


def test_the_sounds_library_argument_reads_another_folder(tmp_path):
    root = tmp_path / "lib"
    item = sfx_library.add(root, name="tone", take=1, category="foley", tags=["room_tone"], rate=48000, loop=True,
                           samples=noise(1.0), source={"kind": "procedural", "seed": 1},
                           licence={"status": "own_procedural", "note": "t"})
    s = ASM.Sounds([], library=root)
    assert s.exists(item["id"]) and s.loopable(item["id"]) and not ASM.Sounds([]).exists(item["id"])


# --- the loudness numbers have one home --------------------------------------------------------------------------------------

def test_the_loudness_targets_are_written_only_in_targets_and_the_registry():
    pat = re.compile(r"(?i)(lufs|\bI=|loudnorm|integrated)[^\n]*[-−]\s?1[46](\.\d)?\b|[-−]\s?1[46](\.\d)?\s?(LUFS|LU\b)")
    bad = []
    for folder in ("audio", "production"):
        for p in sorted((ROOT / "explainer_engine" / folder).glob("*.py")):
            for k, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
                if pat.search(line):
                    bad.append(f"{p.name}:{k}: {line.strip()[:80]}")
    assert bad == [], bad  # qa/targets.py and sourced_rules.json are the only homes of -14 / -16


@pytest.mark.media
def test_a_stereo_mix_normalised_through_targets_loudnorm_measures_inside_the_pass_band(tmp_path):
    total = 20 * FPS
    nar, words = speechlike(20, [(1.0, 9.0), (11.0, 18.0)])
    m = manifest_of(total, music=[{"id": "mu01", "ref": "m", "motif_of": None, "start_frame": 0, "end_frame": total, "gain_db": -22.0,
                                   "fade_in_frames": 50, "fade_out_frames": 100, "beat_grid": None}])
    mix, _stems, _ = render(m, spine_of(words, total), nar, {"m": noise(20, 4)})
    ASM.write_wav(tmp_path / "raw.wav", mix)
    meas = targets.normalise_file(tmp_path / "raw.wav", tmp_path / "audio.wav", "long", SRATE, channels=2)
    assert targets.loudness_verdict(meas["lufs"], "long") == "PASS"
    import wave
    with wave.open(str(tmp_path / "audio.wav")) as w:
        assert w.getnchannels() == 2 and w.getframerate() == SRATE


@pytest.mark.media
def test_assemble_renders_the_stereo_mix_from_a_fresh_manifest_writes_the_stems_and_stops_on_a_stale_one(tmp_path):
    from test_sound_director import make_job
    from explainer_engine.audio import sound_director as D
    job, spine = make_job(tmp_path, plan_of={"S01": [("a", "KEYFRAME_LTX", "WS", "r", {})], "S02": [("b", "KEYFRAME_LTX", "MS", "r", {})],
                                             "S03": [("c", "KEYFRAME_LTX", "CU", "r", {})]}, places={"r": "a room"})
    lib = tmp_path / "lib"
    D.plan(job, library=lib)
    total = spine["total_frames"]
    nar, _words = speechlike(total / FPS, [(1.0, 6.0), (11.0, 16.0), (21.0, 26.0)])
    ASM.write_wav(tmp_path / "nar.wav", nar)
    timed = json.loads((job / "timed.json").read_text())
    timed["findings"] = []
    out = tmp_path / "out"
    rep = ASM.assemble(timed, tmp_path / "nar.wav", out, [], [], audio_only=True, job=job)
    assert rep["audio"]["engine"] == "v2" and "voice_lu" in rep["audio"] and "sound_director" in rep
    assert not [f for f in rep["sound_director"] if f["severity"] == "FAIL"]
    import wave
    with wave.open(str(out / "audio.wav")) as w:
        assert w.getnchannels() == 2
    stems = SD._load_stems(job / "audio" / "stems")
    assert {"narration", "ambience", "room_tone", "music", "sfx", "cues"} <= set(stems) and np.abs(stems["room_tone"]).max() > 0
    (job / "timed.json").write_bytes((job / "timed.json").read_bytes() + b" ")  # one byte: the manifest is stale
    with pytest.raises(SystemExit) as exc:
        ASM.assemble(timed, tmp_path / "nar.wav", out, [], [], audio_only=True, job=job)
    assert "SD-15" in str(exc.value)


# --- only a valid, fresh /2 manifest selects the stereo path (invariant 7) ---------------------------------------------------------

def _fresh_job(tmp_path):
    from test_sound_director import make_job
    job, _spine = make_job(tmp_path, plan_of={"S01": [("a", "KEYFRAME_LTX", "WS", "r", {})], "S02": [("b", "KEYFRAME_LTX", "MS", "r", {})],
                                              "S03": [("c", "KEYFRAME_LTX", "CU", "r", {})]}, places={"r": "a room"})
    SD.plan(job, library=tmp_path / "lib")
    return job, job / "audio" / "sound_mix_manifest.json"


def test_a_fresh_planned_manifest_is_accepted(tmp_path):
    job, path = _fresh_job(tmp_path)
    assert ASM.v2_manifest(job) == json.loads(path.read_text(encoding="utf-8"))


@pytest.mark.parametrize("forge, word", [
    (lambda m: m.update(derived_from={}), "invalid"),                     # nothing to be stale against
    (lambda m: m.pop("derived_from"), "invalid"),
    (lambda m: m.update(schema="sound_mix_manifest/1"), "sound_mix_manifest/2"),  # the old contract is not the stereo plan
    (lambda m: m.update(schema="audio_spine/2"), "sound_mix_manifest/2"),
    (lambda m: m["scenes"].__setitem__(1, dict(m["scenes"][1], start_frame=m["scenes"][1]["start_frame"] + 5)), "invalid"),  # hand edit: a gap (CN-16)
    (lambda m: m["spots"].append({"id": "x"}), "invalid"),                 # hand edit: a spot that breaks the schema
])
def test_a_forged_or_hand_edited_manifest_stops_the_render(tmp_path, forge, word):
    job, path = _fresh_job(tmp_path)
    m = json.loads(path.read_text(encoding="utf-8"))
    forge(m)
    path.write_text(json.dumps(m), encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        ASM.v2_manifest(job)
    assert "SD-15" in str(exc.value) and word in str(exc.value)


def test_a_manifest_that_is_not_json_stops_the_render(tmp_path):
    job, path = _fresh_job(tmp_path)
    path.write_text("{ not json", encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        ASM.v2_manifest(job)
    assert "SD-15" in str(exc.value) and "not JSON" in str(exc.value)


# --- the old mono path is byte-identical to main's (P4 changed none of it) -------------------------------------------------------

def test_the_old_mono_path_renders_the_same_samples_as_main():
    """Golden hash of ``build_audio`` on a fixed synthetic input (beds, music, an effect, a cue; int16, so a numpy build's last
    float digit cannot flip it). The same value was measured on main (39f347c..origin/main) and on the P4 head on 2026-10-30."""
    import hashlib

    class Snd:
        def __init__(self, n):
            self.n = n

        def load(self, name):
            return np.random.default_rng(len(name)).standard_normal(self.n) * 0.3

        def loopable(self, name):
            return True

    n = SRATE * 8
    voice = np.zeros(n)
    voice[SRATE:5 * SRATE] = np.random.default_rng(7).standard_normal(4 * SRATE) * 0.3
    timed = {"duration": 8.0, "shots": [{"id": "SH001", "start": 0.0, "end": 8.0, "bubbles": []}],
             "audio": {"beds": [{"sound": "bed", "start": 0.0, "end": 8.0, "gain_db": -20, "fade_s": 1.0}],
                       "music": [{"track": "mus", "start": 0.0, "end": 8.0, "gain_db": -22, "fade_in_s": 1.0, "fade_out_s": 2.0}],
                       "sfx": [{"sound": "hit", "start": 2.0, "end": 3.0, "gain_db": -16}], "cues": [{"sound": "tick", "start": 4.0}]}}
    mix = ASM.build_audio(timed, voice, Snd(n), {})
    digest = hashlib.sha256((np.clip(mix, -1, 1) * 32767).astype("<i2").tobytes()).hexdigest()
    assert digest == "296151e67aa46d9cba9957a1d724f1f2284444dd2b404d33fdf8f8ceac8f3537"
