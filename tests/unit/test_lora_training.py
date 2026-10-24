"""LoRA training control (D-72, docs/LORA_TRAINING.md): dataset audit, config check, spend projection and the checkpoint
judge, on synthetic data (no GPU, no network)."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from explainer_engine.training import audit, judge

T = "wldnk style"


def _img(path, size=(1024, 768), seed=0):
    rng = np.random.default_rng(seed)
    Image.fromarray(rng.integers(0, 255, (size[1], size[0], 3), dtype=np.uint8)).save(path)


def _set(folder, n, caption=lambda k: f"{T}, a fisherman number {k} mending nets on a pier at dawn", size=(1024, 768),
         seed0=0):
    folder.mkdir(parents=True, exist_ok=True)
    for k in range(n):
        _img(folder / f"im{k:02d}.png", size, seed0 + k)
        (folder / f"im{k:02d}.txt").write_text(caption(k), encoding="utf-8")


def rules(findings, status=None):
    return {f["rule"] for f in findings if status is None or f["status"] == status}


# ---- dataset ---------------------------------------------------------------------------------------------------------

def test_clean_style_dataset_passes(tmp_path):
    caps = ["a fisherman mending nets on a pier at dawn", "two knights arguing over a map in a tent",
            "a baker chasing a goose through a market", "an astronaut watering a cactus on the moon"]
    _set(tmp_path / "his", 24, lambda k: f"{T}, {caps[k % 4]}, scene {k}")
    rep = audit.audit_style([tmp_path / "his"])
    assert audit.verdict(rep["findings"]) in ("PASS", "WARN") and not rules(rep["findings"], "FAIL")


def test_missing_trigger_and_caption_fail(tmp_path):
    _set(tmp_path / "his", 21, lambda k: "a fisherman mending nets on a pier" if k == 0 else f"{T}, a cat on a roof {k}")
    (tmp_path / "his" / "im01.txt").unlink()
    f = audit.audit_style([tmp_path / "his"])["findings"]
    assert "LT-01" in rules(f, "FAIL")


def test_shared_long_phrase_fails_v2_lesson(tmp_path):
    """v2 (2026-10-23): one long style phrase in every caption took the style away from the trigger."""
    _set(tmp_path / "his", 20, lambda k: f"{T}, scene {k}, bold ink line, bulging caricature eyes, painterly background")
    f = audit.audit_style([tmp_path / "his"])["findings"]
    assert "LT-02" in rules(f, "FAIL")


def test_low_resolution_and_duplicates(tmp_path):
    _set(tmp_path / "his", 20, lambda k: f"{T}, a goat on a cliff {k}")
    _img(tmp_path / "his" / "tiny.png", (504, 278), 99)
    (tmp_path / "his" / "tiny.txt").write_text(f"{T}, a tiny picture", encoding="utf-8")
    (tmp_path / "his" / "copy.png").write_bytes((tmp_path / "his" / "im00.png").read_bytes())
    (tmp_path / "his" / "copy.txt").write_text(f"{T}, a goat on a cliff 0", encoding="utf-8")
    f = audit.audit_style([tmp_path / "his"])["findings"]
    assert {"LT-05", "LT-04"} <= rules(f, "FAIL")
    assert any("captions used for several images" in x["msg"] for x in f)


def test_creator_share_counts_repeats(tmp_path):
    _set(tmp_path / "his", 10, lambda k: f"{T}, a monk feeding pigeons {k}")
    _set(tmp_path / "aux", 30, lambda k: f"{T}, a robot fixing a clock {k}", seed0=50)
    low = audit.audit_style([tmp_path / "his", tmp_path / "aux"])
    assert "LT-06" in rules(low["findings"], "FAIL") and low["creator_share"] == 0.25
    ok = audit.audit_style([tmp_path / "his", tmp_path / "aux"], repeats={"his": 5, "aux": 1})
    assert "LT-06" not in rules(ok["findings"], "FAIL") and ok["creator_share"] == pytest.approx(50 / 80, abs=1e-3)


def test_edit_pairs_must_match(tmp_path):
    _set(tmp_path / "targets", 3, lambda k: f"the man raises his arm {k}", size=(600, 600))
    (tmp_path / "control").mkdir()
    for k in (0, 1):
        _img(tmp_path / "control" / f"im{k:02d}.png", (600, 600), k)
    f = audit.audit_edit(tmp_path / "targets", [tmp_path / "control"])["findings"]
    assert "LT-08" in rules(f, "FAIL")


def test_video_frames_and_dims():
    clips = [{"path": "a.mp4", "frames": 121, "width": 960, "height": 544, "caption": "a figure leaps and lands, arms out"},
             {"path": "b.mp4", "frames": 120, "width": 960, "height": 540, "caption": "a figure spins on one foot slowly"}]
    f = audit.audit_video(clips)["findings"]
    msgs = " ".join(x["msg"] for x in f if x["rule"] == "LT-07" and x["status"] == "FAIL")
    assert "b.mp4" in msgs and "a.mp4" not in msgs


# ---- config ----------------------------------------------------------------------------------------------------------

def _cfg(**over):
    p = {"trigger_word": T, "network": {"linear": 32, "linear_alpha": 32},
         "save": {"save_every": 250, "max_step_saves_to_keep": 8},
         "datasets": [{"folder_path": "/workspace/ds/his", "caption_dropout_rate": 0.0, "num_repeats": 5}],
         "train": {"steps": 1500, "lr": 1e-4, "cache_text_embeddings": True},
         "model": {"name_or_path": "Qwen/Qwen-Image-2512"},
         "sample": {"sample_every": 250, "seed": 42, "samples": [
             {"prompt": f"{T}, a vast ice age tundra with a yellow bus in snow"},
             {"prompt": f"{T}, a roman forum, a senator arguing with a baker"},
             {"prompt": f"{T}, close-up of a bald old man, terrified"},
             {"prompt": "a lighthouse keeper reading by a lamp"}]}}
    for k, v in over.items():
        p[k] = v
    return {"config": {"process": [p]}}


def test_good_config_passes():
    rep = audit.check_config(_cfg(), "style", captions=["wldnk style, a fisherman on a pier"],
                             launch={"image": "ostris/aitoolkit:latest", "boot_minutes": 25})
    assert audit.verdict(rep["findings"]) != "FAIL" and rep["view"]["repeats"] == {"his": 5}


def test_config_failures():
    bad = _cfg(train={"steps": 1500, "lr": 1e-3, "cache_text_embeddings": True},
               save={"save_every": 500}, datasets=[{"folder_path": "x", "caption_dropout_rate": 0.05}])
    f = audit.check_config(bad, "style", launch={"image": "ostris/aitoolkit:latest", "boot_minutes": 10})["findings"]
    assert {"LT-10", "LT-11", "LT-15"} <= rules(f, "FAIL")
    assert "LT-13" in rules(f, "WARN")


def test_heldout_and_trigger_off_probe():
    cfg = _cfg(sample={"seed": 1, "sample_every": 250, "samples": [{"prompt": f"{T}, a fisherman on a pier"}] * 4})
    f = audit.check_config(cfg, "style", captions=[f"{T}, a fisherman on a pier"])["findings"]
    assert any(x["rule"] == "LT-12" and x["status"] == "WARN" and "held-out" in x["msg"] for x in f)
    assert any(x["rule"] == "LT-12" and "without the trigger" in x["msg"] for x in f)


def test_cost_projection_and_80_percent():
    p = audit.project_cost(steps=1500, done_steps=500, sec_per_step=5.21, price_per_hour=0.59, n_ckpt_samples=4,
                           n_prompts=7, sec_per_sample=40, spent_usd=0.6)
    assert p["usd_left"] == pytest.approx(1000 * 5.21 / 3600 * 0.59 + 4 * 7 * 40 / 3600 * 0.59, abs=0.01)
    assert rules(audit.spend_findings(p, 2.0), "WARN") == {"LT-14"}
    assert rules(audit.spend_findings(p, 3.0)) == {"LT-14"} and audit.spend_findings(p, 3.0)[0]["status"] == "INFO"
    assert rules(audit.spend_findings(p, 1.0), "FAIL") == {"LT-14"}
    assert judge.log_progress("x:  40%|####| 500/1250 [53:28<1:05:07,  5.21s/it, lr: 1e-4]") == (500, 1250, 5.21)
    log = "x:  20%|##| 250/1250 [29:15<1:42:38,  6.16s/it, lr: 1e-4]\rGenerating Samples:  14%| | 1/7 [00:47<04:46, 47.70s/it]"
    assert judge.log_progress(log) == (250, 1250, 6.16)  # a sample bar is not a training step


# ---- judge -----------------------------------------------------------------------------------------------------------

def _run(moves, *, n=6, dim=64, seed=0, copy_at=None, collapse_at=None):
    """Synthetic run: prompt contents c_i and a style direction s of equal size; step k's sample = c_i + moves[k] * s;
    the creator's references = s + other content. Texts = the contents (an adherence that only falls as style grows,
    so tests that are not about adherence leave texts out)."""
    rng = np.random.default_rng(seed)
    content = rng.normal(size=(n, dim))
    style = rng.normal(size=dim)
    refs = style + rng.normal(size=(20, dim))
    train = refs + rng.normal(size=(20, dim)) * 0.3
    by = {}
    for step, m in moves.items():
        emb = {i: content[i] + m * style for i in range(n)}
        if step == copy_at:
            emb[0] = train[3].copy()
        if step == collapse_at:
            emb = {i: style + content[0] for i in range(n)}
        by[step] = emb
    texts = {i: content[i] for i in range(n)}
    return by, refs, train, texts


def test_progress_rises_then_plateau_stops():
    by, refs, train, texts = _run({0: 0.0, 250: 0.4, 500: 0.8, 750: 0.81, 1000: 0.82})
    rows = judge.score_run(by, refs, train=train)
    assert rows[0]["progress"] == 0 and rows[2]["progress"] > rows[1]["progress"] > 0.1
    d = judge.decide(rows, 1500)
    assert d["action"] == "STOP_KEEP_BEST" and "plateau" in d["why"]
    assert judge.decide(rows[:3], 1500)["action"] == "CONTINUE"


def test_not_learning_fails_after_500():
    by, refs, train, texts = _run({0: 0.0, 250: 0.01, 500: 0.02})
    d = judge.decide(judge.score_run(by, refs, train=train), 1500)
    assert d["action"] == "STOP_FAIL" and "not learning" in d["why"]


def test_memorization_flags_and_keeps_earlier_best():
    by, refs, train, texts = _run({0: 0.0, 250: 0.5, 500: 0.7}, copy_at=500)
    rows = judge.score_run(by, refs, train=train)
    assert not rows[1]["flags"]
    assert any("LT-23" in f for f in rows[-1]["flags"])
    d = judge.decide(rows, 1500)
    assert d["action"] == "STOP_KEEP_BEST" and d["best"] == 250


def test_collapse_flag():
    by, refs, train, texts = _run({0: 0.0, 250: 0.5, 500: 0.6}, collapse_at=500)
    rows = judge.score_run(by, refs, texts=texts)
    assert any("LT-24" in f for f in rows[-1]["flags"]) and any("LT-22" in f for f in rows[-1]["flags"])
    assert not any("LT-24" in f for f in judge.score_run(by, refs)[1]["flags"])


def test_parse_sample_names(tmp_path):
    names = ["1792761122909__000000000_0.jpg", "1792763211801__000000250_3.jpg", "junk.jpg"]
    got = judge.parse_samples([tmp_path / n for n in names] + [tmp_path / ".thumbs" / names[0]])
    assert set(got) == {0, 250} and set(got[250]) == {3}


def test_video_motion_freeze_and_jitter():
    t = np.linspace(0, 1, 25)
    base = np.stack([np.tile(np.sin(np.linspace(0, 6, 64) + 3 * x), (48, 1)) for x in t]) * 100 + 128
    frozen = np.stack([base[0]] * 25)
    jitter = base + np.random.default_rng(1).normal(0, 20, base.shape)
    mb = judge.video_metrics(base, {0: base[0]})
    assert rules(judge.compare_video(mb, judge.video_metrics(frozen, {0: base[0]})), "FAIL") == {"LT-31"}
    assert "LT-32" in rules(judge.compare_video(mb, judge.video_metrics(jitter, {0: base[0]})), "FAIL")
    assert rules(judge.compare_video(mb, mb)) == {"LT-30"}


def test_edit_drift_and_copy():
    rng = np.random.default_rng(0)
    scene = rng.integers(0, 255, (256, 256)).astype(float)

    def moved(img, dx):
        out = img.copy()
        out[96:160, 96:160] = np.roll(img[96:160, 96:160], dx, axis=1)
        return out

    dataset = [judge.edit_pair_metrics(scene, moved(scene, 20)) for _ in range(5)]
    good = [judge.edit_pair_metrics(scene, moved(scene, 15))]
    drifted = [judge.edit_pair_metrics(scene, np.roll(moved(scene, 15), 30, axis=0))]
    copied = [judge.edit_pair_metrics(scene, scene)]
    assert rules(judge.judge_edit(good, dataset)) == {"LT-40"}
    assert "LT-41" in rules(judge.judge_edit(drifted, dataset), "FAIL")
    assert "LT-42" in rules(judge.judge_edit(copied, dataset), "FAIL")


def test_yaml_string_learning_rate_is_read():
    """PyYAML reads ``lr: 1e-4`` (no dot) as a string; v4's real config has it."""
    f = audit.check_config(_cfg(train={"steps": 1500, "lr": "1e-4"}), "style")["findings"]
    assert "LT-10" not in rules(f)


# ---- footage (FS-xx) -------------------------------------------------------------------------------------------------

def _synthetic_video(path, *, seconds=12, fps=24, size=(320, 180)):
    """Three shots: a fixed camera with a moving square, a hard cut to a panning scene, a cut to a static scene."""
    import cv2
    w, h = size
    out = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
    rng = np.random.default_rng(0)
    bg1 = rng.integers(40, 200, (h, w, 3), dtype=np.uint8)
    bg2 = rng.integers(40, 200, (h, w * 2, 3), dtype=np.uint8)
    bg3 = np.full((h, w, 3), 90, dtype=np.uint8)
    n = seconds * fps
    for i in range(n):
        t = i / n
        if t < 0.4:
            fr = bg1.copy()
            x = int(20 + (w - 80) * (i / (0.4 * n)))
            fr[60:120, x:x + 40] = (250, 30, 30)
        elif t < 0.75:
            off = int((i - 0.4 * n) / (0.35 * n) * w)
            fr = bg2[:, off:off + w].copy()
        else:
            fr = bg3.copy()
        out.write(fr)
    out.release()


def test_footage_split_measure_classify(tmp_path):
    pytest.importorskip("scenedetect")
    raw = tmp_path / "raw"
    raw.mkdir()
    _synthetic_video(raw / "testshow_1999.mp4")
    from explainer_engine.training import footage
    rep = footage.index(raw, tmp_path / "work")
    assert rep["files"][0]["show"] == "testshow" and rules(rep["findings"], "FAIL") == set()
    shots = footage.split(tmp_path / "work")
    assert 2 <= len(shots) <= 4
    shots = footage.measure(tmp_path / "work")
    kinds = [footage.classify(s) for s in shots]
    assert "pair" in kinds and "clip" in kinds and "static" in kinds, [(s["camera"], s["motion"]) for s in shots]
    bal = footage.balance(shots)
    assert "FS-04" in rules(bal["findings"], "WARN")  # one show only: nothing held out
    made = footage.pairs(tmp_path / "work", tmp_path / "pairs")
    assert made and (tmp_path / "pairs" / "train" / "control" / made[0]["name"]).exists()
    clip = footage.clips(tmp_path / "work", tmp_path / "clips", max_per_show=2)
    assert clip and clip[0]["frames"] == 89
    assert not rules(audit.audit_video(clip)["findings"], "FAIL")


def test_motion_caption_names_banned():
    from explainer_engine.training import footage
    f = footage.caption_findings_motion(["a girl leaps over a log, cloak trailing", "Aladdin runs in Disney style"],
                                        banned=["aladdin"])
    assert len(rules(f, "FAIL")) == 1 and "caption 1" in f[0]["msg"]


def test_launch_gate_catches_wrong_run():
    """2026-10-23: v4's first pod loaded v3's cfg.yaml from the launcher's old path ($0.38 lost)."""
    cfg = _cfg(datasets=[{"folder_path": "/workspace/ds/dataset_style_v7/his", "num_repeats": 5}])
    cfg["config"]["name"] = "wldnk_qwen_v3"
    f = audit.check_launch(cfg, run_name="v4", dataset="dataset_style_v7", cfg_path="trainq3/cfg.yaml")["findings"]
    assert len(rules(f, "FAIL")) == 1 and sum(x["rule"] == "LT-16" for x in f) == 2
    cfg["config"]["name"] = "wldnk_qwen_v4"
    assert not audit.check_launch(cfg, run_name="v4", dataset="dataset_style_v7", cfg_path="trainq4/cfg.yaml")["findings"]


# ---- video QA (LT-50..LT-59) -----------------------------------------------------------------------------------------

def _drawn_clip(n=72, *, melt_from=None, pop_at=None, legs_off_from=None, extra_from=None, backdrop=(200, 200, 200),
                shirt=None, line=2):
    """Line-art test shot at 320x180: a hatched backdrop and a walking outlined figure (head box over a body with legs);
    ``shirt`` fills the body, ``backdrop`` paints the set, ``line`` is the ink width."""
    import cv2
    frames = []
    for i in range(n):
        f = np.full((180, 320, 3), backdrop, np.uint8)
        for x in range(0, 320, 16):
            cv2.line(f, (x, 0), (x + 40, 180), (60, 60, 60), 1)
        x = 60 + i
        if shirt:
            cv2.rectangle(f, (x - 5, 72), (x + 35, 120), shirt, -1)
        cv2.rectangle(f, (x, 40), (x + 30, 70), (20, 20, 20), line)          # head
        cv2.rectangle(f, (x - 5, 72), (x + 35, 120), (20, 20, 20), line)     # body
        if legs_off_from is None or i < legs_off_from:
            for k in range(6):
                cv2.line(f, (x + 3 * k, 122), (x + 3 * k - 4, 160), (20, 20, 20), 2)
        if extra_from is not None and i >= extra_from:                        # a figure the layout never had
            for k in range(8):
                cv2.circle(f, (280, 140), 6 + 4 * k, (10, 10, 10), 2)
        if melt_from is not None and i >= melt_from:
            f = cv2.GaussianBlur(f, (0, 0), 0.5 + (i - melt_from) * 0.25)
        if pop_at is not None and i == pop_at:
            f = np.clip(f.astype(int) + 60, 0, 255).astype(np.uint8)
        frames.append(f)
    return np.stack(frames)


def _qa_rules(found):
    return {f["rule"] for f in found if f["status"] != "PASS"}


def test_video_qa_clean_shot_passes():
    from explainer_engine.training import video_qa
    m = video_qa.analyse(_drawn_clip(), 24.0)
    assert _qa_rules(video_qa.judge(m)) == set() and m["breaks_at_second"] is None


def test_video_qa_melting_and_flicker():
    from explainer_engine.training import video_qa
    melt = video_qa.judge(video_qa.analyse(_drawn_clip(melt_from=24), 24.0))
    assert "LT-53" in _qa_rules(melt)
    pop = video_qa.judge(video_qa.analyse(_drawn_clip(pop_at=30), 24.0))
    assert "LT-51" in _qa_rules(pop)


def test_video_qa_lost_legs_and_invented_content():
    from explainer_engine.training import video_qa
    clip = _drawn_clip(legs_off_from=30)
    m = video_qa.analyse(clip, 24.0, regions=[{"label": "walker", "box": [55 / 320, 38 / 180, 100 / 320, 165 / 180]}])
    assert m["regions"]["walker"]["legs_lost_at_s"] is not None and m["regions"]["walker"]["head_lost_at_s"] is None
    layout = _drawn_clip()
    lf = video_qa.layout_fidelity(_drawn_clip(extra_from=24), layout, fps=24.0)
    assert lf["cells"] and all(c["render"] == "gains" for c in lf["cells"]) and lf["cells"][0]["at_s"] >= 0.9
    assert video_qa.layout_fidelity(layout, layout, fps=24.0)["cells"] == []


def test_shot_identity_across_a_cut():
    """LT-60..62 (ვანო 2026-10-24 07:17): the join between two shots keeps the set's palette, the line weight and the
    hero's colours; a recoloured set, a thicker drawing or a new shirt is caught, the same drawing passes."""
    from explainer_engine.training import video_qa
    a = _drawn_clip(shirt=(40, 90, 200))
    hero = [{"label": "walker", "a": [125 / 320, 38 / 180, 170 / 320, 165 / 180], "b": [55 / 320, 38 / 180, 100 / 320, 165 / 180]}]
    same = video_qa.shot_identity(a[-1], _drawn_clip(shirt=(40, 90, 200))[0], hero)
    assert _qa_rules(video_qa.judge_identity(same)) == set() and same["heroes"]["walker"] < 0.01
    recolour = video_qa.judge_identity(video_qa.shot_identity(a[-1], _drawn_clip(backdrop=(90, 140, 60), shirt=(40, 90, 200))[0], hero))
    assert "LT-60" in _qa_rules(recolour)
    thick = video_qa.judge_identity(video_qa.shot_identity(a[-1], _drawn_clip(shirt=(40, 90, 200), line=5)[0], hero))
    assert "LT-61" in _qa_rules(thick)
    shirt = video_qa.judge_identity(video_qa.shot_identity(a[-1], _drawn_clip(shirt=(220, 40, 40))[0], hero))
    assert _qa_rules(shirt) == {"LT-62"}


def test_video_criteria_registry_matches_the_rulebook():
    """VQ-01..50 (ვანო 2026-10-24): every criterion has one home in docs/LORA_TRAINING.md and every LT rule a code
    criterion points at exists in the rules table."""
    import json
    root = Path(__file__).resolve().parents[2]
    reg = json.loads((root / "explainer_engine/training/video_criteria.json").read_text(encoding="utf-8"))
    doc = (root / "docs/LORA_TRAINING.md").read_text(encoding="utf-8")
    ids = [c["id"] for c in reg["criteria"]]
    assert ids == [f"VQ-{i:02d}" for i in range(1, 51)]
    for c in reg["criteria"]:
        assert f"| {c['id']} |" in doc, c["id"]
        assert c["check"] in ("code", "eye", "na")
        if c["check"] == "code":
            assert c.get("rules"), c["id"]
        for r in c.get("rules", []):
            assert f"| {r} |" in doc, (c["id"], r)
