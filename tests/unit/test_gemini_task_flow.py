"""The Gemini Task route's code (A2: build list items 1-7 of GEMINI_TASK_FLOW_PLAN_ka.md, spec Q3, Q4, Q7, Q9-Q11;
GC-20..GC-27). Everything runs on a small episode in a temp folder; nothing calls Gemini."""

from __future__ import annotations

import json
import random
from pathlib import Path

import pytest

from explainer_engine.core.errors import ContractError
from explainer_engine.gemini_task import batch as BT
from explainer_engine.gemini_task import ep as EP
from explainer_engine.gemini_task import gate as GT
from explainer_engine.gemini_task import pack as PK
from explainer_engine.gemini_task import prompts as PR
from explainer_engine.gemini_task import queue as QU
from explainer_engine.gemini_task import report as RP
from explainer_engine.gemini_task import review as RV
from explainer_engine.gemini_task import texts as TX
from explainer_engine.gemini_task import timing as TM

ERA = ("The world is the Late Pleistocene of 74,000 BCE: the only light sources are hearth fires, torches and the low "
       "sun, and everything is made of hide, wood, bone and stone.")
KAEL = "Kael, a 45-year-old hunter with weathered dark skin, coarse braided hair and a cracked antelope-hide cloak"
SENA = "Sena, a 26-year-old stone artisan with intense dark eyes, a woven leather apron and a shell necklace"
CAVE = "a rock shelter above a dry gorge, a hearth ring of blackened stones, hides hung against the wind"


def _shot(sid, size, chars, route, *, end=False, role=None, visual="cinematic_video", lid="S01_L00"):
    return {"shot_id": sid, "segment_id": "S01", "target_duration_seconds": 3.0, "visual_type": visual, "route": route,
            "route_reason": "test", "location_id": "loc_cave", "character_ids": chars, "prop_ids": [],
            "audio_line_ids": [lid + sid[-1]], "shot_role": role,
            "action_start_state": "Kael kneels by the hearth and blows on the embers",
            "action_end_state": "the flames rise and light his face",
            "camera_spec": {"shot_size": size}, "screen_composition": {"background": "the dark gorge"},
            "lighting_and_time": "firelight at dusk", "keyframe_plan": {"needs_start_frame": True, "needs_end_frame": end}}


def make_episode(root: Path) -> Path:
    root.mkdir(parents=True)
    (root / "story").mkdir()
    shots = [_shot("S01_SH001", "close_up", ["char_kael"], "still_25d"),
             _shot("S01_SH002", "medium", ["char_kael", "char_sena"], "wan", end=True),
             _shot("S01_SH003", "wide", [], "still_25d"),
             _shot("S01_SH004", "top_down_map", [], "map_action", visual="map_visualization")]
    lines = [{"line_id": f"S01_L00{k}", "segment_id": "S01", "speaker_type": "narrator", "speaker_id": "narrator_main",
              "addressee_id": None, "text": f"Line number {k} of the story."} for k in range(1, 5)]
    script = {"schema_version": "4.0.0", "episode_id": "ep_test", "title": "Test", "segments": [
        {"segment_id": "S01", "title": "Ember", "narrative_purpose": "the fire is kept"}],
        "visual_mix_target": {"cinematic_video_target": 0.6, "composed_illustration_target": 0.3, "map_visualization_target": 0.1},
        "world_bible": {"characters": [
            {"character_id": "char_kael", "name": "Kael", "fixed_appearance_prompt": KAEL},
            {"character_id": "char_sena", "name": "Sena", "fixed_appearance_prompt": SENA}],
            "locations": [{"location_id": "loc_cave", "name": "The Rift Shelter", "fixed_environment_prompt": CAVE}],
            "props": []},
        "audio_lines": lines, "shots": shots}
    (root / "story" / "production_script.json").write_text(json.dumps(script), encoding="utf-8")
    (root / "story" / "short_story.md").write_text("Kael keeps the last fire alive through the long ash winter.\n",
                                                   encoding="utf-8")
    man = {"episode_id": "ep_test", "title": "The Last Fire", "era_line": ERA}
    (root / "episode.json").write_text(json.dumps(man), encoding="utf-8")
    return root


def noise(path: Path, w=1376, h=774, seed=0) -> Path:
    from PIL import Image
    rnd = random.Random(seed)
    im = Image.frombytes("RGB", (w // 8, h // 8), bytes(rnd.randrange(256) for _ in range((w // 8) * (h // 8) * 3)))
    im = im.resize((w, h))
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path, quality=92)
    return path


def flat(path: Path, w=1376, h=774) -> Path:
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (w, h), (240, 240, 240))
    ImageDraw.Draw(im).rectangle([100, 100, 600, 300], fill=(20, 20, 20))
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path)
    return path


def report(batch: str, ids: list[str], made=None, limit_from=None, prompt="AS GIVEN") -> str:
    lines = [f"BATCH REPORT {batch}"]
    n = 0
    for k, i in enumerate(ids, 1):
        if limit_from is not None and k >= limit_from:
            lines.append(f"{k} | {i} | NOT MADE | reason: limit")
        elif made is not None and i not in made:
            lines.append(f"{k} | {i} | NOT MADE | reason: refused")
        else:
            lines.append(f"{k} | {i} | MADE | refs: 1 | prompt: {prompt} | note: -")
            n += 1
    lines.append(f"MADE {n} of {len(ids)}")
    return "**" + "\n".join(lines) + "**"


@pytest.fixture()
def env(tmp_path, monkeypatch):
    cfg = json.loads(EP.CONFIG.read_text(encoding="utf-8"))
    cfg_path = tmp_path / "gemini_task.json"
    cfg_path.write_text(json.dumps(cfg), encoding="utf-8")
    monkeypatch.setattr(EP, "CONFIG", cfg_path)
    EP.config.cache_clear()
    monkeypatch.setattr(GT, "record_path", lambda: tmp_path / "t0_record.json")
    monkeypatch.setattr(EP, "commit", lambda: "abcdef123456")
    root = make_episode(tmp_path / "ep_test")
    yield root
    EP.config.cache_clear()


def pass_t0(root: Path, tmp: Path, n_files=6, model="Gemini 3.8 Flash", prompt="AS GIVEN", drive_ok=True, write=True):
    PK.export(root)
    sent = GT.render_t0(root)
    files = [noise(tmp / "t0dl" / f"{k:02d}.jpg", seed=k) for k in range(1, n_files + 1)]
    made = sent["ids"][:n_files]
    body = report("0", sent["ids"], made=made, prompt=prompt).strip("*")
    read = f'DRIVE READ: OK "Pack version: {sent["pack_version"]}"' if drive_ok else "DRIVE READ: FAILED no access"
    ans = f"T0 REPORT {sent['sha8']}\nMODEL: {model} | MODE: Task\n{read}\nDRIVE WRITE: OK x\n{body}\nLIMIT: not reached"
    return GT.record_t0(root, ans, files, "test", write=write)


# --- texts and pack (item 1) -----------------------------------------------------------------------------------------
def test_fill_refuses_undeclared_and_unfilled_placeholders_and_renders_bp_percent():
    with pytest.raises(ContractError, match="not declared"):
        TX.fill("a {{nope}}", {})
    with pytest.raises(ContractError, match="without a value"):
        TX.fill("a {{episode_id}}", {})
    assert TX.fill("{{bp:BP-105.nominal_narrator_share|percent}}", {}).endswith("%")
    with pytest.raises(ContractError, match="secret"):
        TX.clean_gate("key AIza" + "x" * 35, "t")
    with pytest.raises(ContractError, match="Georgian"):
        TX.clean_gate("კი", "t")


def test_pack_export_fills_every_file_strips_notes_and_copies_the_main_style(env):
    doc = PK.export(env)
    rules = EP.drive_dir(env) / "rules"
    names = sorted(p.name for p in rules.glob("*.md"))
    assert names == sorted(Path(f["path"]).name for f in PK.pack_files())
    for p in rules.glob("*.md"):
        t = p.read_text(encoding="utf-8")
        assert "{{" not in t and "<!--" not in t
    assert doc["pack_version"] in (rules / "00_START_HERE.md").read_text(encoding="utf-8")
    assert ERA in (rules / "05_STYLE.md").read_text(encoding="utf-8")
    assert any(f["path"].endswith("refs/main_style_5709.png") for f in doc["files"])
    assert PK.current_version(env) == doc["pack_version"]


def test_era_line_must_follow_the_shape_and_avoid_never_words(env):
    man = json.loads((env / "episode.json").read_text())
    lk = EP.look(man)
    assert EP.era_line(man, lk) == ERA
    with pytest.raises(ContractError, match="shape"):
        EP.era_line(dict(man, era_line="Stone Age."), lk)
    with pytest.raises(ContractError, match="lantern"):
        EP.era_line(dict(man, era_line=ERA.replace("torches", "a lantern")), lk)


# --- T0 (item 7) ---------------------------------------------------------------------------------------------------
def test_t0_message_has_six_gated_prompts_and_the_route_stays_off_until_it_passes(env, tmp_path):
    PK.export(env)
    sent = GT.render_t0(env)
    text = (env / sent["message"]).read_text(encoding="utf-8")
    assert text.count("PICTURE ") == 6 and "{{" not in text and ERA in text
    assert sent["attach"][0]["drive_name"] == "main_style_5709.png"
    with pytest.raises(ContractError, match="T0"):
        RV.render_check(env, "short_story")
    rec = pass_t0(env, tmp_path)
    assert rec["status"] == "PASS" and rec["batch_size"] == 6 and rec["batch_mode"] == "queue_on_drive"
    assert GT.state()["status"] == "PASS"


@pytest.mark.parametrize("n,status,size", [(5, "PASS", 5), (4, "PASS", 4), (3, "FAIL", None)])
def test_t0_counts_set_the_batch_size_or_fail_with_a_card(env, tmp_path, n, status, size):
    rec = pass_t0(env, tmp_path, n_files=n)
    assert rec["status"] == status and rec["batch_size"] == size
    assert ("card" in rec) == (status == "FAIL")
    assert rec["batch_mode"] == "self_contained"     # a NOT MADE line means not every prompt came back AS GIVEN


def test_t0_fails_on_another_model_and_mode_needs_drive_read_and_verbatim_prompts(env, tmp_path):
    assert pass_t0(env, tmp_path, model="Gemini Pro")["status"] == "FAIL"
    assert pass_t0(env, tmp_path, model="Argon")["status"] == "FAIL"
    assert pass_t0(env, tmp_path, model="4 Argon")["status"] == "FAIL"
    assert pass_t0(env, tmp_path, model="4 Hydrogen")["status"] == "PASS"  # creator 2026-11-12 19:56 UTC: Flash = Hydrogen
    assert pass_t0(env, tmp_path, prompt="CHANGED shortened")["batch_mode"] == "self_contained"
    assert pass_t0(env, tmp_path, drive_ok=False)["batch_mode"] == "self_contained"


def test_t0_refuses_a_count_mismatch_and_a_card_drawn_by_code(env, tmp_path):
    PK.export(env)
    sent = GT.render_t0(env)
    ans = (f"T0 REPORT {sent['sha8']}\nMODEL: Flash | MODE: Task\nDRIVE READ: FAILED x\nDRIVE WRITE: FAILED x\n"
           + report("0", sent["ids"]).strip("*"))
    files = [noise(tmp_path / "d" / f"{k:02d}.jpg", seed=k) for k in range(5)]
    with pytest.raises(ContractError, match="Q9"):
        GT.record_t0(env, ans, files, "test", write=False)
    files.append(flat(tmp_path / "d" / "06.png"))
    rec = GT.record_t0(env, ans, files, "test", write=False)
    assert rec["real_pictures"] == 5 and rec["batch_size"] == 5
    assert any(g["gate"] == "not_a_card" and g["status"] == "FAIL" for g in rec["pictures"][5]["gates"])


# --- reports -------------------------------------------------------------------------------------------------------
def test_batch_report_parser_is_strict_on_counts_and_tolerant_of_markdown():
    rep = RP.parse_batch_report("```\n" + report("3", ["a", "b"], made=["a"]) + "\n```", expect="3")
    assert [i["status"] for i in rep["items"]] == ["MADE", "NOT MADE"] and rep["made"] == 1
    with pytest.raises(ContractError, match="MADE 2"):
        RP.parse_batch_report("BATCH REPORT 3\n1 | a | MADE | refs: 1 | prompt: AS GIVEN | note: -\nMADE 2 of 1")
    with pytest.raises(ContractError, match="batch"):
        RP.parse_batch_report(report("3", ["a"]), expect="4")
    with pytest.raises(ContractError, match="AS GIVEN"):
        RP.parse_batch_report("BATCH REPORT 1\n1 | a | MADE | refs: 1 | note: -\nMADE 1 of 1")


def test_review_parser_downgrades_a_blocker_without_source_and_trusts_findings_over_verdict():
    rv = RP.parse_review("REVIEW script ep 0123abcd round 1\nVERDICT: REVISE\nSTORY FIRST: fine.\nFINDINGS\n"
                         'F1 | BLOCKER | - | "q" | p | fix\nMEASURED: x\nNOT CHECKED: -')
    assert rv["findings"][0]["severity"] == "IDEA" and rv["findings"][0]["downgraded"]
    assert rv["verdict"] == "APPROVE_WITH_NOTES" and rv["notes"]


# --- queue (items 3, 6) --------------------------------------------------------------------------------------------
def test_queue_style_anchor_by_shot_type_reference_order_and_batches(env):
    doc = QU.build(env)
    shots = {s["shot_id"]: s for s in doc["shots"]}
    assert shots["S01_SH001"]["shot_type"] == "B" and shots["S01_SH002"]["shot_type"] == "E"
    assert shots["S01_SH003"]["shot_type"] == "A" and shots["S01_SH004"]["pictures"] == []
    pics = QU.items_by_id(doc)
    start, end = pics["S01_SH002_start"], pics["S01_SH002_end"]
    assert [r["ref_id"] for r in start["references"]] == [
        "style_E", "ref_char_kael_portrait", "ref_char_sena_portrait", "ref_loc_cave_place"]   # Q4, GC-02
    assert [r["ref_id"] for r in end["references"]][:2] == ["style_E", "S01_SH002_start"]      # GC-09 amended by GC-21
    assert TX.clause("keep_scene") in start["prompt"] and ERA in start["prompt"] and KAEL in start["prompt"]
    kinds = [b["kind"] for b in doc["batches"]]
    assert kinds[:3] == ["R1", "R1", "R2"] and set(kinds[3:]) == {"scene"}                     # GC-23
    for b in doc["batches"]:
        assert not ({"S01_SH002_start", "S01_SH002_end"} <= set(b["ids"]))
    full = pics["ref_char_kael_full_body"]
    assert [r["ref_id"] for r in full["references"]] == ["style_main", "ref_char_kael_portrait"]  # Q7
    assert TX.clause("keep_full_body") in full["prompt"]
    assert all(it["needs_approval"] for it in doc["pictures"])                                   # nothing approved yet
    assert doc["timed"] is False and doc["counts"]["pictures"] == 4


def test_queue_refuses_a_never_word_and_reports_shares_in_the_frame(env):
    sp = env / "story" / "production_script.json"
    s = json.loads(sp.read_text())
    s["world_bible"]["characters"][0]["fixed_appearance_prompt"] = KAEL + ", a realistic face"
    sp.write_text(json.dumps(s))
    doc = QU.build(env)
    assert any(f["rule"] == "GC-18" for f in doc["prompt_fails"])
    with pytest.raises(ContractError, match="FAIL"):
        QU.write(env, doc)
    assert set(doc["mix"]["frame"]) == {"map_action", "still_25d", "wan"}


def test_frame_band_and_wan_clip():
    assert TM.in_band(10.9, 10) and TM.in_band(9.1, 10) and not TM.in_band(11.2, 10)
    assert TM.wan_frames(3.0, 16) == 49 and (TM.wan_frames(2.0, 16) - 1) % 4 == 0
    assert TM.wan_clip(3.0)["status"] == "PASS" and TM.wan_clip(9.0)["status"] == "REVIEW"


def test_timed_read_sets_lengths_and_marks_a_measure_outside_the_frame(env):
    tim = {"fps": 24, "shots": {"S01_SH001": {"seconds": 3.2}, "S01_SH002": {"seconds": 4.0},
                                "S01_SH003": {"seconds": 2.9}, "S01_SH004": {"seconds": 3.0}}}
    (env / "audio").mkdir()
    (env / "audio" / "timing.json").write_text(json.dumps(tim))
    doc = QU.build(env)
    shots = {s["shot_id"]: s for s in doc["shots"]}
    assert doc["timed"] and shots["S01_SH001"]["duration_s"] == 3.2 and shots["S01_SH001"]["frame"]["status"] == "PASS"
    assert shots["S01_SH002"]["frame"]["status"] == "REVIEW" and shots["S01_SH002"]["wan_clip"]["frames"] == 65


# --- reviews (item 2) ----------------------------------------------------------------------------------------------
def _review(stage, sha, rnd, verdict, findings=""):
    return f"REVIEW {stage} ep_test {sha} round {rnd}\nVERDICT: {verdict}\nSTORY FIRST: ok.\nFINDINGS\n{findings}MEASURED: -\nNOT CHECKED: -"


def test_review_deadlock_makes_a_card_and_only_the_creator_closes_it(env, tmp_path):
    pass_t0(env, tmp_path)
    sent = RV.render_check(env, "short_story")
    RV.intake_review(env, "short_story", _review("short_story", sent["sha8"], 1, "REVISE",
                                                 'F1 | BLOCKER | ST-02 | "last fire" | no turn | add a turn\n'))
    assert RV.stage_status(env, "short_story")["status"] == "OPEN"
    with pytest.raises(ContractError, match="source"):
        RV.reply(env, "short_story", {"F1": {"action": "REJECT"}})
    r1 = RV.reply(env, "short_story", {"F1": {"action": "REJECT", "source": "D-61", "reason": "the turn is shown"}})
    rec = RV.record(env, "short_story")
    assert rec["findings"]["F1"]["disagreement"]["claude_source"] == "D-61"
    RV.intake_reply(env, "short_story", f"REPLY short_story ep_test {r1['sha8']} round 1\nF1 | HOLD | YT-01-HOOK | still flat\n"
                    "OPEN: F1 | STAGE: NOT YET")
    r2 = RV.reply(env, "short_story", {"F1": {"action": "REJECT", "source": "D-61", "reason": "same"}})
    out = RV.intake_reply(env, "short_story", f"REPLY short_story ep_test {r2['sha8']} round 2\n"
                          "DEADLOCK short_story ep_test F1\nCLAUDE: shown | SOURCE: D-61\nGEMINI: flat | SOURCE: YT-01-HOOK\n"
                          "FOR THE VIEWER: A = calm; B = a jolt\nOPEN: F1 | STAGE: CREATOR")
    assert out["cards"] and RV.stage_status(env, "short_story")["status"] == "OPEN"
    card = json.loads((env / out["cards"][0]).read_text())
    assert [o["source"] for o in card["options"]] == ["D-61", "YT-01-HOOK"]
    with pytest.raises(ContractError, match="no reply round 3"):
        RV.reply(env, "short_story", {"F1": {"action": "REJECT", "source": "x", "reason": "y"}})
    RV.decide(env, "short_story", "F1", "A", "cmsg_test")
    assert RV.stage_status(env, "short_story")["status"] == "PASS"
    (env / "story" / "short_story.md").write_text("changed\n")
    assert RV.stage_status(env, "short_story")["status"] == "STALE"


def test_accepted_change_needs_the_artefact_changed_and_a_fixed_answer(env, tmp_path):
    pass_t0(env, tmp_path)
    sent = RV.render_check(env, "short_story")
    RV.intake_review(env, "short_story", _review("short_story", sent["sha8"], 1, "REVISE",
                                                 'F1 | BLOCKER | ST-02 | "q" | p | f\nF2 | IDEA | - | "q" | p | f\n'))
    with pytest.raises(ContractError, match="unchanged"):
        RV.reply(env, "short_story", {"F1": {"action": "ACCEPT", "change": "a turn added"}, "F2": {"action": "NOTED"}})
    (env / "story" / "short_story.md").write_text("Kael keeps the fire; then the river dies.\n")
    r = RV.reply(env, "short_story", {"F1": {"action": "ACCEPT", "change": "a turn added"}, "F2": {"action": "NOTED"}})
    assert "Kael keeps the fire" in (env / r["message"]).read_text()
    RV.intake_reply(env, "short_story", f"REPLY short_story ep_test {r['sha8']} round 1\nF1 | FIXED\nOPEN: - | STAGE: PASS")
    assert RV.stage_status(env, "short_story")["status"] == "PASS"


# --- batches (items 4, 5) ------------------------------------------------------------------------------------------
def _pass_stages(env):
    for stage in ("short_story", "script"):
        s = RV.render_check(env, stage)
        RV.intake_review(env, stage, _review(stage, s["sha8"], 1, "APPROVE"))
    QU.write(env, QU.build(env))
    s = RV.render_check(env, "video_script")
    RV.intake_review(env, "video_script", _review("video_script", s["sha8"], 1, "APPROVE"))


def _take(env, tmp, no, seed, made=None, limit_from=None, redo=False):
    meta = BT.state(env)["redo_batches" if redo else "batches"][str(no)]
    ids = meta.get("resume_ids") or meta["ids"]
    k_made = [i for k, i in enumerate(ids, 1) if (made is None or i in made) and (limit_from is None or k < limit_from)]
    files = [noise(tmp / f"dl{no}_{seed}" / f"{k:02d}.jpg", seed=seed * 100 + k) for k in range(len(k_made))]
    ans = report(meta["expect"], ids, made=made, limit_from=limit_from)
    return (BT.intake_redo if redo else BT.intake)(env, no, ans, files)


def test_full_batch_flow_references_first_mapping_by_order_limit_resume_and_redo(env, tmp_path, monkeypatch):
    pass_t0(env, tmp_path)
    QU.write(env, QU.build(env))
    with pytest.raises(ContractError, match="video script"):
        BT.render(env, 1)
    _pass_stages(env)
    doc = QU.load(env)
    m = BT.render(env, 1)                                                   # R1 portraits, P6
    assert m["msg"] == "P6" and m["attach"][0]["drive_name"] == "main_style_5709.png"
    with pytest.raises(ContractError, match="Q9"):
        BT.intake(env, 1, report("R1", m["ids"]), [noise(tmp_path / "x.jpg")])
    _take(env, tmp_path, 1, 1)
    BT.render(env, 2)
    _take(env, tmp_path, 2, 2)
    with pytest.raises(ContractError, match="approvals"):
        BT.render(env, 3)                                                   # R2 waits for the approved portraits
    for b in (1, 2):
        for pid in doc["batches"][b - 1]["ids"]:
            BT.verdict(env, pid, True)
            BT.approve(env, pid, "cmsg_creator")
    BT.render(env, 3)
    _take(env, tmp_path, 3, 3)
    for pid in doc["batches"][2]["ids"]:
        BT.verdict(env, pid, True)
        BT.approve(env, pid, "cmsg_creator")
    scene = next(b for b in doc["batches"] if b["kind"] == "scene")
    with pytest.raises(ContractError, match="timed"):
        BT.render(env, scene["no"])                                          # voice first
    tim = {"fps": 24, "shots": {s["shot_id"]: {"seconds": 3.0} for s in doc["shots"]}}
    (env / "audio").mkdir()
    (env / "audio" / "timing.json").write_text(json.dumps(tim))
    QU.write(env, QU.build(env))
    s = RV.render_check(env, "video_script")
    RV.intake_review(env, "video_script", _review("video_script", s["sha8"], s["round"], "APPROVE"))
    with pytest.raises(ContractError, match="approvals"):
        BT.render(env, scene["no"])                                          # style anchors not picked yet
    for t in ("A", "B", "E"):
        f = noise(tmp_path / "anchors" / f"{t}.jpg", seed=ord(t))
        BT.approve_anchor(t, str(f), "cmsg_creator")
    doc = QU.load(env)
    st = GT.state()
    assert doc["mode"] == st["batch_mode"]
    monkeypatch.setattr(QU, "load", lambda root: dict(doc, mode="self_contained"))
    scenes = [b for b in doc["batches"] if b["kind"] == "scene" and not any(i.endswith("_end") for i in b["ids"])]
    for b in scenes:
        m = BT.render(env, b["no"])
        assert m["msg"] == "P7"
        first = BT.QU.items_by_id(doc)[b["ids"][0]]
        assert first["references"][0]["ref_id"].startswith("style_")
        if len(b["ids"]) > 1:
            out = _take(env, tmp_path, b["no"], b["no"], limit_from=2)
            assert out["limit"] and BT.state(env)["batches"][str(b["no"])]["status"] == "partial"
            r = BT.resume(env, b["no"])
            assert r["msg"] == "P9"
            _take(env, tmp_path, b["no"], b["no"] + 50)
        else:
            _take(env, tmp_path, b["no"], b["no"])
        with pytest.raises(ContractError, match="never send it twice"):
            BT.render(env, b["no"])
    first_pic = scenes[0]["ids"][0]
    with pytest.raises(ContractError, match="positive"):
        BT.verdict(env, first_pic, False, "a glass lantern appeared", "Remove the glass lantern.")
    BT.verdict(env, first_pic, False, "a glass lantern appeared", "The only light is the hearth fire below his face.")
    for b in scenes:
        for pid in b["ids"]:
            if pid != first_pic:
                BT.verdict(env, pid, True)
    ends = [b for b in doc["batches"] if b["kind"] == "scene" and b not in scenes]
    with pytest.raises(ContractError, match="no redo inside the run"):
        BT.redo(env, "scene")
    for b in ends:
        BT.render(env, b["no"])
        _take(env, tmp_path, b["no"], b["no"] + 70)
        for pid in b["ids"]:
            BT.verdict(env, pid, True)
    metas = BT.redo(env, "scene")
    assert len(metas) == 1 and metas[0]["msg"] == "P10"
    text = (env / metas[0]["message"]).read_text(encoding="utf-8")
    assert "REPLACES:" in text and "The only light is the hearth fire below his face." in text
    _take(env, tmp_path, 1, 900, redo=True)
    BT.verdict(env, first_pic, False, "still wrong", "The only light is the hearth fire.")
    assert BT.state(env)["pictures"][first_pic]["status"] == "creator"                          # GC-25: no second redo
    assert first_pic in BT.status(env)["to_creator"]
    ledger = BT.ledger_rows(env)
    assert ledger and all("at" in r for r in ledger)


def test_queue_on_drive_needs_the_saved_queue_and_sends_p8(env, tmp_path):
    pass_t0(env, tmp_path)
    for t in ("A", "B", "E"):
        BT.approve_anchor(t, str(noise(tmp_path / "anc" / f"{t}.jpg", seed=ord(t))), "cmsg")
    (env / "audio").mkdir()
    (env / "audio" / "timing.json").write_text(json.dumps({"fps": 24, "shots": {f"S01_SH00{k}": {"seconds": 3.0} for k in range(1, 5)}}))
    _pass_stages(env)
    doc = QU.load(env)
    assert doc["mode"] == "queue_on_drive"
    refs = json.dumps({it["id"]: {"file": str(noise(env / "r" / f"{it['id']}.jpg", seed=k)), "sha256": "x", "approved_by": "c"}
                       for k, it in enumerate(doc["references"])})
    (EP.work(env) / "refs_approved.json").write_text(refs)
    scene = next(b for b in doc["batches"] if b["kind"] == "scene")
    with pytest.raises(ContractError, match="P5"):
        BT.render(env, scene["no"])
    p5 = BT.render_save_queue(env)
    assert p5["msg"] == "P5"
    BT.intake_save_queue(env, f"SAVED: CrossWorld/episodes/ep_test/shot_queue.json\nPICTURES: {p5['n']}\nSHA: {p5['sha8']}")
    m = BT.render(env, scene["no"])
    assert m["msg"] == "P8"


def test_prompt_check_rules():
    lk = {"style_sentence": "S.", "face_sentence": "F.", "style_reference_clause": "R.", "never_words": ["photo"]}
    p = PR.assemble(lk, ERA, "scene", "Kael by a lantern, a photo with a sign.", people=True)
    rules = {r["rule"] for r in PR.fails(PR.check(p, lk, ERA, "scene", [KAEL], subject="Kael by a lantern, a photo with a sign."))}
    assert {"GC-04", "GC-07", "GC-18", "GC-22"} <= rules
    ok = PR.assemble(lk, ERA, "scene", "Kael kneels by the hearth.", people=False)
    assert not PR.fails(PR.check(ok, lk, ERA, "scene", [], subject="Kael kneels by the hearth."))
    bad = PR.check(ok + " Two. Sentences.", lk, ERA, "scene", [], subject="x", correction="Two. Sentences.")
    assert any(r["rule"] == "GC-25" for r in bad)


def test_toba_dry_export_writes_the_pack_the_t0_message_and_a_clean_queue(env, tmp_path):
    import shutil
    src = Path(__file__).resolve().parents[2] / "episodes" / "ep_toba"
    root = tmp_path / "ep_toba"
    shutil.copytree(src, root)
    from explainer_engine.episode.context import validate_instance
    validate_instance(json.loads((root / "episode.json").read_text(encoding="utf-8")), "episode_manifest.schema.json")
    doc = PK.export(root)
    assert (EP.drive_dir(root) / "rules" / "00_START_HERE.md").exists() and doc["pack_version"]
    sent = GT.render_t0(root)
    assert (root / sent["message"]).exists() and len(sent["ids"]) == 6
    q = QU.build(root)
    assert not q["prompt_fails"] and q["counts"]["shots"] > 100
    assert all(it["references"][0]["ref_id"].startswith("style_") for it in q["pictures"] if it["kind"] == "scene")
    QU.write(root, q)
    assert QU.path(root).exists()
