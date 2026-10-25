"""Scene continuity (D-69, CS-01..CS-12, production/staging.py): consecutive pictures of one staged scene are shots of ONE
room with one master frame, the roster in it and the seats kept; a camera change never starts a new scene; a new place or
time does; a painted picture is checked against its own shot spec and repainted at most MAX_REPAINTS times. No network:
the Gemini client gets a fake ``post`` and the review answers are written by the test."""
import base64
import copy
import json

import pytest

from explainer_engine.core.ledger import Run
from explainer_engine.imagegen import gemini as G
from explainer_engine.imagegen import plan as P
from explainer_engine.production import compile as C
from explainer_engine.production import paint
from explainer_engine.production import script as S
from explainer_engine.production import staging as ST
from explainer_engine.production import validate as V
from test_editorial_gate import valid_doc, valid_review
from test_production_script import mini, rules

MODEL, SIZE = "gemini-nano-banana-2.1", "2K"
ROSTER = ["einstein", "franklin", "curie"]


def staged() -> dict:
    """mini() plus one staged scene over two segments (S03, S04) and a new place the next morning (S05)."""
    doc = mini()
    doc["cast"]["curie"] = {"names": ["curie"], "card": "Marie Curie, dark dress, hair pinned up, a steady gaze"}
    doc["segments"] += [
        {"id": "S03", "beat": "council", "light_beat": 7,
         "staging": {"location": "the camp around the fire", "time": "the first night", "roster": ROSTER,
                     "positions": {"einstein": "on the left stone", "franklin": "in the middle",
                                   "curie": "on the right stone"},
                     "fixed": ["a ring of flat stones", "the dark hills behind"]},
         "lines": [{"text": "Einstein sits at the left of the fire."}, {"text": "Franklin leans in to listen."},
                   {"text": "Curie waits on the right, arms folded."}],
         "shots": [{"at": "Einstein sits", "type": "A", "motion": {"kind": "push", "z0": 1.0, "z1": 1.04},
                    "picture": {"id": "council_wide", "heroes": ROSTER,
                                "subject": "wide view of three scientists sitting around the fire on flat stones"}},
                   {"at": "Franklin leans", "type": "B", "motion": {"kind": "push", "z0": 1.0, "z1": 1.04},
                    "picture": {"id": "franklin_close", "heroes": ["franklin"],
                                "subject": "close on Franklin leaning in to listen, firelight on his spectacles"}},
                   {"at": "Curie waits", "type": "B", "motion": {"kind": "push", "z0": 1.0, "z1": 1.04},
                    "picture": {"id": "ots_curie", "heroes": ["curie", "einstein"],
                                "subject": "over Einstein's shoulder, Curie waits with her arms folded"}}]},
        {"id": "S04", "beat": "council", "light_beat": 7, "staging": {"continues": True},
         "lines": [{"text": "Curie speaks at last."}, {"text": "She points at the dark hills."}],
         "shots": [{"at": "Curie speaks", "type": "B", "picture": "ots_curie", "reuse": "reframe",
                    "motion": {"kind": "push", "z0": 1.0, "z1": 1.04}},
                   {"at": "She points", "type": "B", "motion": {"kind": "push", "z0": 1.0, "z1": 1.04},
                    "picture": {"id": "ots_curie_points", "heroes": ["curie", "einstein"],
                                "change": "Curie raises her arm and points at the hills",
                                "subject": "over Einstein's shoulder, Curie points at the dark hills"}}]},
        {"id": "S05", "beat": "river", "light_beat": 8,
         "staging": {"location": "the river below the camp", "time": "the next morning"},
         "lines": [{"text": "At dawn, Franklin walks down to the river."}],
         "shots": [{"at": "At dawn", "type": "A", "motion": {"kind": "push", "z0": 1.0, "z1": 1.04},
                    "picture": {"id": "river_wide", "heroes": ["franklin"],
                                "subject": "wide view of the river below the camp, Franklin walking down to the water"}}]},
    ]
    return doc


def spec(doc, pid):
    return ST.plan(doc)["pictures"][pid]


# --- planning ----------------------------------------------------------------------------------------------------------

def test_consecutive_segments_of_one_scene_keep_the_scene_id():
    plan = ST.plan(staged())
    ids = {s["segment"]: s for s in plan["segments"]}
    assert ids["S03"]["scene_id"] == ids["S04"]["scene_id"] == "SC03"
    assert ids["S03"]["starts_scene"] and not ids["S04"]["starts_scene"]
    assert {plan["pictures"][p]["scene_id"] for p in ("council_wide", "franklin_close", "ots_curie", "ots_curie_points")} \
        == {"SC03"}


def test_the_same_place_and_time_continue_without_a_flag():
    doc = staged()
    doc["segments"][3]["staging"] = {"location": "The camp, around the fire!", "time": "the first night"}
    assert ST.scene_ids(doc)[2:4] == ["SC03", "SC03"]


def test_a_camera_change_stays_in_the_scene():
    doc = staged()
    close, ots = spec(doc, "franklin_close"), spec(doc, "ots_curie")
    assert (close["framing"], close["kind"], close["scene_id"]) == ("close", "reframe", "SC03")
    assert (ots["framing"], ots["kind"], ots["scene_id"]) == ("over_shoulder", "reframe", "SC03")
    assert close["master"] == ots["master"] == "council_wide"


def test_a_new_place_or_time_starts_a_new_scene():
    doc = staged()
    river = spec(doc, "river_wide")
    assert river["scene_id"] == "SC05" and river["kind"] == "master" and river["master"] is None
    doc["segments"][4]["staging"] = {"location": "the camp around the fire", "time": "a week later"}
    assert ST.scene_ids(doc)[4] == "SC05"  # same place, another time: a new scene, never suppressed


def test_an_unstaged_segment_paints_each_picture_alone_as_before():
    doc = staged()
    assert spec(doc, "cold_hands")["kind"] == "montage"
    assert ST.prompt_block(doc, "cold_hands").startswith("One single full-frame picture")
    plain = C.compile_doc(mini())  # a script without staging compiles exactly as before D-69
    assert "SCENE" not in json.dumps(plain) and "single full-frame" not in json.dumps(plain)


def test_same_camera_with_a_stated_change_is_an_edit_of_the_shot_before():
    doc = staged()
    pts = spec(doc, "ots_curie_points")
    assert pts["kind"] == "action" and pts["prev"] == "ots_curie" and pts["master"] == "council_wide"
    assert ST.refs_for(doc, "ots_curie_points", ["style"]) == ["council_wide", "ots_curie", "style"]
    block = ST.prompt_block(doc, "ots_curie_points")
    assert "reference image 2 is the previous shot (ots_curie)" in block
    assert "Edit reference image 2" in block and "Curie raises her arm" in block


def test_a_reverse_angle_is_not_an_edit_of_the_shot_before():
    doc = staged()
    doc["segments"][3]["shots"][1]["picture"].update(heroes=["einstein", "curie"], change="",
                                                     subject="over Curie's shoulder, Einstein listens")
    s = spec(doc, "ots_curie_points")
    assert s["kind"] == "reframe" and s["prev"] is None


def test_required_characters_are_in_the_shot_spec_and_the_prompt():
    doc = staged()
    wide, ots = spec(doc, "council_wide"), spec(doc, "ots_curie")
    assert wide["kind"] == "master" and wide["visible"] == ROSTER
    assert ots["visible"] == ["curie"] and ots["partial"] == ["einstein"] and ots["offscreen"] == ["franklin"]
    master = ST.prompt_block(doc, "council_wide")
    assert "MASTER FRAME" in master and "all 3 of them in frame" in master
    assert master.index("einstein (on the left stone)") < master.index("franklin (in the middle)") \
        < master.index("curie (on the right stone)")
    block = ST.prompt_block(doc, "ots_curie")
    for want in ("SCENE SC03", "master frame (council_wide)", "must show with readable faces: curie",
                 "seen only in part (shoulder or back): einstein", "outside this frame: franklin",
                 "a ring of flat stones", "never the room or the seats", "never a collage, split screen"):
        assert want in block, want


def test_compile_appends_the_block_and_the_prompt_stays_lint_clean():
    doc = C.compile_doc(staged())
    pics, _ = S.pictures(doc)
    assert "SCENE SC03, continuous with its master frame" in pics["ots_curie"]["prompt"]
    found = V.check_script(doc)
    assert not [f for f in found if f["rule"] == "PV-11"], [f for f in found if f["rule"] == "PV-11"]
    assert not {r for r in rules(found) if r.startswith("CS-")}
    gem, _ = C.jobs(doc)
    refs = {j["id"]: j["refs"] for j in gem}
    assert refs["ots_curie"][0] == "council_wide" and refs["council_wide"] == []


def test_a_split_screen_subject_keeps_its_split():
    doc = staged()
    doc["segments"][2]["shots"][1]["picture"]["subject"] = "a split frame: Franklin on the left, the fire on the right"
    assert "single full-frame" not in ST.prompt_block(doc, "franklin_close")
    assert "single_frame" not in ST.questions(doc, "franklin_close")


# --- the script lint ---------------------------------------------------------------------------------------------------

def test_a_master_that_leaves_someone_out_fails():
    doc = staged()
    doc["segments"][2]["shots"][0]["picture"]["heroes"] = ["einstein", "franklin"]
    doc["segments"][2]["staging"]["master"] = "council_wide"
    found = ST.lint(doc)
    assert any(f["rule"] == "CS-02" and f["severity"] == "FAIL" and "curie" in f["detail"] for f in found)


def test_a_hero_outside_the_room_fails_unless_cut_away():
    doc = staged()
    doc["segments"][2]["shots"][1]["picture"]["heroes"] = ["darwin"]
    doc["cast"]["darwin"] = {"names": ["darwin"], "card": "Charles Darwin, long white beard"}
    assert "CS-03" in rules(ST.lint(doc))
    doc["segments"][2]["shots"][1]["picture"]["cut_away"] = True
    assert "CS-03" not in rules(ST.lint(doc))
    assert spec(doc, "franklin_close")["kind"] == "cut_away"


def test_a_counted_group_with_fewer_named_heroes_is_flagged():
    doc = staged()
    doc["segments"][2]["shots"][0]["picture"]["subject"] = "ten ruined men sit on the long bench"
    assert any(f["rule"] == "CS-05" and "10 men" in f["detail"] for f in ST.lint(doc))


def test_references_are_trimmed_to_the_models_slots_and_named():
    doc = staged()
    lib = doc["library"]
    for who in ROSTER + ["newton", "darwin"]:
        doc["cast"].setdefault(who, {"names": [who], "card": f"{who} as our caricature, long coat"})
        lib[f"p_{who}"] = {"file": f"p_{who}.png", "heroes": [who], "shows": []}
        doc["cast"][who]["reference"] = {"collage": "c.jpg", "tile": 1, "picture": f"p_{who}", "approved_by": "creator",
                                         "approved_at": "2026-10-22"}
    item = {"id": "council_wide", "prompt": "p", "refs": ["p_einstein.png", "p_franklin.png", "p_curie.png", "p_newton.png",
                                                          "p_darwin.png", "style.png"]}
    items, notes = ST.fit_refs(doc, [item], "gemini", MODEL)
    assert G.ref_limits(MODEL)["characters"] == 4
    assert items[0]["refs"] == ["p_einstein.png", "p_franklin.png", "p_curie.png", "p_newton.png", "style.png"]
    assert notes and notes[0]["rule"] == "CS-08" and "p_darwin" in notes[0]["detail"]


# --- the review ---------------------------------------------------------------------------------------------------------

def ok(doc, pid):
    return {k: True for k in ST.questions(doc, pid)}


def test_a_close_up_is_not_failed_for_the_people_outside_it():
    doc = staged()
    q = ST.questions(doc, "franklin_close")
    assert "visible_franklin" in q and "visible_einstein" not in q and "visible_curie" not in q
    assert ST.verdict(doc, "franklin_close", ok(doc, "franklin_close"))["status"] == "PASS"


def test_a_missing_required_character_fails_with_a_targeted_correction():
    doc = staged()
    ans = ok(doc, "council_wide")
    ans["visible_curie"] = False
    v = ST.verdict(doc, "council_wide", ans)
    assert v["status"] == "FAIL" and v["fails"][0].startswith("CS-10 curie must be visible")
    assert "curie must be clearly in frame" in v["correction"] and "on the right stone" in v["correction"]


def test_an_unexplained_change_of_room_fails():
    doc = staged()
    ans = ok(doc, "ots_curie")
    ans["place"] = False
    v = ST.verdict(doc, "ots_curie", ans)
    assert v["status"] == "FAIL" and "room changed from the master frame council_wide" in v["fails"][0]
    ans = ok(doc, "ots_curie")
    ans["single_frame"] = False
    assert ST.verdict(doc, "ots_curie", ans)["fails"][0].startswith("CS-11 not one single frame")


def test_a_seat_or_action_doubt_is_a_review_not_a_fail():
    doc = staged()
    ans = ok(doc, "council_wide")
    ans.pop("action")
    assert ST.verdict(doc, "council_wide", ans)["status"] == "REVIEW"


def test_a_pixel_seam_hints_at_a_split_screen(tmp_path):
    from PIL import Image
    im = Image.new("RGB", (640, 360), (20, 20, 20))
    im.paste((230, 230, 230), (320, 0, 640, 360))
    im.save(tmp_path / "split.png")
    assert ST.seam_findings(tmp_path / "split.png")[0]["severity"] == "REVIEW"
    Image.new("RGB", (640, 360), (90, 90, 90)).save(tmp_path / "flat.png")
    assert ST.seam_findings(tmp_path / "flat.png") == []


# --- painting: order, review gate, bounded repaints --------------------------------------------------------------------

PNG = b"\x89PNG fake"


@pytest.fixture
def episode(tmp_path, monkeypatch):
    from PIL import Image
    doc = C.compile_doc(staged())
    doc["episode"]["gemini_exception"] = {"decision": "D-44", "cap_usd": 6.0}
    for name in ("camp", "valley", "duo"):
        Image.new("RGB", (16, 9)).save(tmp_path / f"{name}.png")
    doc["editorial"] = valid_doc()["editorial"]
    for seg in doc["segments"]:
        for ln in seg["lines"]:
            ln["kind"] = "transition"
    doc["segments"][0]["lines"][0].update(kind="fact", claims=["C1"])
    script = tmp_path / "production_script.json"
    S.save(doc, script)
    (tmp_path / "editorial_review.json").write_text(json.dumps(valid_review(script)))
    (tmp_path / "sample_approval.json").write_text(json.dumps(  # OR-19: these tests paint the rest, after the sample
        {"approved_by": "creator", "approved_at": "2026-10-21T10:00:00Z", "ref": "test"}))
    calls = []

    def post(self, model, body):
        parts = body["contents"][0]["parts"]
        calls.append({"prompt": parts[0]["text"], "images": len(parts) - 1})
        from PIL import Image
        import io
        b = io.BytesIO()
        Image.new("RGB", (32, 18), (len(calls) * 20 % 255, 40, 40)).save(b, "PNG")
        return {"candidates": [{"content": {"parts": [{"inlineData": {"mimeType": "image/png",
                                                                       "data": base64.b64encode(b.getvalue()).decode()}}]}}]}
    monkeypatch.setattr(G.GeminiClient, "_http", post)
    monkeypatch.setenv("EXPLAINER_IMAGE_CACHE", str(tmp_path / "cache"))
    Run.open(tmp_path / "run.json", caps={"gemini_usd": 6.0})
    return tmp_path, script, calls


def plan_and_run(tmp, script, pid, extra=()):
    args = ["plan", str(script), "--out", str(tmp / "pics"), "--id", pid, "--provider", "gemini", "--model", MODEL,
            "--size", SIZE, "--purpose", "test", "--run", str(tmp / "run.json")] + list(extra)
    assert paint.main(args) == 0
    plan = tmp / "pics" / "plans" / f"{pid}.json"
    assert paint.main(["approve", str(plan), "--run", str(tmp / "run.json"), "--by", "creator", "--ref", "cmsg_x"]) == 0
    code = paint.main(["run", str(plan), str(script), "--run", str(tmp / "run.json"), "--out", str(tmp / "pics"),
                       "--refs", str(tmp), "--workers", "1"])
    return code, json.loads(plan.read_text())


def review(tmp, doc, answers):
    path = tmp / "continuity_review.json"
    path.write_text(json.dumps({"schema": ST.SCHEMA, "by": "claude", "pictures": answers}))
    return ST.main(["apply", str(tmp / "production_script.json"), str(path), "--run", str(tmp / "run.json"),
                    "--pictures", str(tmp / "pics")])


def test_masters_first_then_the_shots_after_a_passing_review(episode, capsys):
    tmp, script, calls = episode
    doc = S.load(script)
    code, plan = plan_and_run(tmp, script, "B1", ["--masters"])
    assert code == 0 and {i["id"] for i in plan["items"]} == {"council_wide", "river_wide"}
    assert all("MASTER FRAME" in c["prompt"] for c in calls)
    code, _ = plan_and_run(tmp, script, "B2")
    out = capsys.readouterr().out
    assert "wait ots_curie: waits for council_wide: the master frame needs a PASS continuity review" in out
    assert len(calls) == 3  # B2 painted only cold_hands (unstaged); every shot of SC03 waited for the review
    assert review(tmp, doc, {"council_wide": ok(doc, "council_wide"), "river_wide": ok(doc, "river_wide")}) == 0
    code, _ = plan_and_run(tmp, script, "B3")
    assert code == 0
    sent = {c["prompt"].split("SCENE ")[1][:4] for c in calls[3:]}
    assert sent == {"SC03"} and len(calls) == 6  # franklin_close, ots_curie, then ots_curie_points (an edit of ots_curie)
    pts = calls[-1]
    assert "Edit reference image 2" in pts["prompt"] and pts["images"] == 2  # the master and the previous shot


def test_a_rejected_picture_is_repainted_with_its_correction_at_most_twice(episode, capsys):
    tmp, script, calls = episode
    doc = S.load(script)
    plan_and_run(tmp, script, "M1", ["--masters"])
    bad = ok(doc, "council_wide")
    bad["visible_curie"] = False
    for attempt in (1, 2):
        assert review(tmp, doc, {"council_wide": bad}) == 1
        code, plan = plan_and_run(tmp, script, f"R{attempt}", ["--only", "council_wide"])
        item = plan["items"][0]
        assert "CORRECTION of the previous attempt: curie must be clearly in frame" in item["correction"]
        assert "CORRECTION" in calls[-1]["prompt"] and code == 0
    assert len(list((tmp / "pics" / "rejected").glob("council_wide.v*.png"))) == 2
    assert review(tmp, doc, {"council_wide": bad}) == 1  # the third failure: no repaint left
    assert "CS-12" in capsys.readouterr().out
    n = len(calls)
    args = ["plan", str(script), "--out", str(tmp / "pics"), "--id", "R3", "--provider", "gemini", "--model", MODEL,
            "--size", SIZE, "--purpose", "test", "--run", str(tmp / "run.json"), "--only", "council_wide"]
    assert paint.main(args) == 0
    assert json.loads((tmp / "pics" / "plans" / "R3.json").read_text())["items"] == []
    assert "CS-12: not planned" in capsys.readouterr().out
    assert len(calls) == n
    run = Run.open(tmp / "run.json")
    assert ST.exhausted(run, "council_wide") and ST.attempts(run, "council_wide") == ST.MAX_REPAINTS


def test_a_stopped_picture_is_refused_by_the_preflight(episode):
    tmp, script, _ = episode
    doc = S.load(script)
    run = Run.open(tmp / "run.json")
    for _ in range(ST.MAX_REPAINTS + 1):
        ST.record(run, "council_wide", {"status": "FAIL", "fails": ["CS-10 x"], "review": [], "correction": "c"}, None)
    plan = P.make("X", "mini", [{"id": "council_wide", "prompt": "p", "refs": []}], provider="gemini", model=MODEL,
                  size=SIZE, purpose="t")
    run.approve("X", plan["hash"], by="creator", ref="cmsg", provider="gemini", usd=plan["estimate_usd"])
    why = paint.preflight(plan, doc, [tmp], run, script)
    assert any(w.startswith("CS-12 council_wide") for w in why)


def test_max_repaints_cannot_be_raised_from_the_command_line(episode):
    tmp, script, _ = episode
    with pytest.raises(SystemExit):
        review_path = tmp / "r.json"
        review_path.write_text(json.dumps({"schema": ST.SCHEMA, "pictures": {}}))
        ST.main(["apply", str(script), str(review_path), "--run", str(tmp / "run.json"), "--pictures", str(tmp),
                 "--max-repaints", str(ST.MAX_REPAINTS + 1)])


def test_the_paid_judge_sends_the_master_and_respects_its_budget(episode, monkeypatch):
    tmp, script, _ = episode
    doc = S.load(script)
    (tmp / "pics").mkdir(exist_ok=True)
    from PIL import Image
    for pid in ("council_wide", "ots_curie"):
        Image.new("RGB", (16, 9)).save(tmp / "pics" / f"{pid}.png")
    seen = []

    def judge(self, image, question, *, model="x", images=None):
        seen.append(len(images or []))
        return json.dumps({k: True for k in json.loads(question.split("\n", 1)[1])})
    monkeypatch.setattr(G.GeminiClient, "judge", judge)
    client = G.GeminiClient(tmp / "g", cap_usd=1.0)
    with pytest.raises(ValueError):
        ST.judge(doc, [tmp / "pics"], client, max_usd=0.001)
    res = ST.judge(doc, [tmp / "pics"], client, max_usd=1.0)
    assert sorted(seen) == [0, 1] and set(res["pictures"]) == {"council_wide", "ots_curie"}
    assert ST.verdict(doc, "ots_curie", res["pictures"]["ots_curie"])["status"] == "PASS"


def test_the_gemini_judge_prices_every_image(tmp_path):
    run = Run.open(tmp_path / "run.json", caps={"gemini_usd": 6.0})
    client = G.GeminiClient(tmp_path, cap_usd=1.0, run=run,
                            post=lambda m, b: {"candidates": [{"content": {"parts": [{"text": "{}"}]}}]})
    client.judge(b"a", "q", images=[b"b"])
    assert client.spent == pytest.approx(2 * G.JUDGE_USD)


def test_waves_put_a_reference_before_the_picture_that_takes_it():
    items = [{"id": "b", "refs": ["a.png"]}, {"id": "c", "refs": ["b.png"]}, {"id": "a", "refs": []}]
    assert [[i["id"] for i in w] for w in ST.waves(items)] == [["a"], ["b"], ["c"]]


def test_a_correction_changes_the_item_hash_and_the_prompt_sent():
    it = {"id": "x", "prompt": "p", "refs": []}
    fixed = dict(it, correction="CORRECTION: y")
    assert P.item_hash(it) != P.item_hash(fixed) and P.full_prompt(fixed) == "p CORRECTION: y"
    assert P.item_hash(it) == P.item_hash(copy.deepcopy(it))
