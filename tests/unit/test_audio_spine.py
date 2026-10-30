"""The audio spine (P4, docs/CONTRACTS.md audio_spine/1 and /2, D-88): compiled from the two shipped episodes' real words.json and
timed.json, never repaired; post-hoc dialogue windows move later words and read_time inverts them. Free: committed files only."""

from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path

import pytest

from explainer_engine.audio import spine as SP
from explainer_engine.core import contracts as C
from explainer_engine.core.errors import ContractError

ROOT = Path(__file__).resolve().parents[2]
EPISODES = ["titans_from_zero", "syndicate_wars_ep1"]
REFS = {k: {"path": f"{k}.json", "sha256": "a" * 64} for k in ("words", "timed", "film_shots")}


def load(name: str, what: str) -> dict:
    return json.loads((ROOT / "examples" / name / f"{what}.json").read_text(encoding="utf-8"))


def words_and_timed(name: str):
    return load(name, "words"), load(name, "timed")


@pytest.mark.parametrize("name", EPISODES)
def test_the_real_episodes_compile_to_a_valid_spine_1(name):
    words, timed = words_and_timed(name)
    spine = SP.compile_spine(words, timed, refs=REFS)
    assert spine["schema"] == "audio_spine/1" and spine["post_hoc_shots"] == []  # no film_shots, no window: the /1 every reader knows
    assert C.errors(spine) == []
    fps = timed["fps"]
    assert fps == 30 and spine["fps"] == 30
    assert len(spine["words"]) == len(words["words"])
    assert spine["total_frames"] == timed["frames"] and spine["duration_s"] == words["duration"]
    for w, src in zip(spine["words"], words["words"]):
        assert w["text"] == src["w"]
        assert w["start_frame"] == round(w["start_s"] * fps) and w["end_frame"] == round(w["end_s"] * fps)
        line = timed["lines"][w["line"]]  # the global line index finds the line, and the line gives the segment
        assert line["segment"] == w["segment"]
        assert line["start"] <= (src["s"] + src["e"]) / 2 <= line["end"] + 1e-9


@pytest.mark.parametrize("name,count", [("titans_from_zero", 2293), ("syndicate_wars_ep1", 1498)])
def test_every_word_is_in_a_segment_and_segments_follow_the_timed_order(name, count):
    words, timed = words_and_timed(name)
    spine = SP.compile_spine(words, timed, refs=REFS)
    assert len(spine["words"]) == count
    assert [s["id"] for s in spine["segments"]] == [s["id"] for s in timed["segments"]]
    by_seg = {s["id"]: s for s in spine["segments"]}
    assert {w["segment"] for w in spine["words"]} == set(by_seg)
    for w in spine["words"]:
        seg = by_seg[w["segment"]]
        assert seg["start_frame"] <= w["start_frame"] and w["end_frame"] <= seg["end_frame"]
    starts = [s["start_frame"] for s in spine["segments"]]
    assert starts == sorted(starts)


def test_a_word_between_two_lines_goes_to_the_previous_line():
    lines = [{"segment": "S01", "start": 0.0, "end": 1.0}, {"segment": "S01", "start": 2.0, "end": 3.0}]
    words = [{"w": "a", "s": 0.1, "e": 0.5}, {"w": "pad", "s": 1.2, "e": 1.5}, {"w": "b", "s": 2.1, "e": 2.5}]
    assert SP.word_segments(words, lines) == [("S01", 0), ("S01", 0), ("S01", 1)]
    with pytest.raises(ContractError):  # before the first line: nothing is invented for it
        SP.word_segments([{"w": "early", "s": 0.0, "e": 0.1}], [{"segment": "S01", "start": 1.0, "end": 2.0}])


def test_out_of_order_words_raise_and_are_never_sorted():
    words, timed = words_and_timed("titans_from_zero")
    bad = copy.deepcopy(words)
    bad["words"][10], bad["words"][11] = bad["words"][11], bad["words"][10]
    with pytest.raises(ContractError, match="out of order"):
        SP.compile_spine(bad, timed, refs=REFS)
    bad = copy.deepcopy(words)
    bad["words"][5]["e"] = bad["words"][5]["s"] - 0.1  # ends before it starts
    with pytest.raises(ContractError, match="out of order"):
        SP.compile_spine(bad, timed, refs=REFS)
    assert words["words"][10]["s"] <= words["words"][11]["s"]  # the input was not touched


def test_a_word_past_the_read_or_another_read_raises():
    words, timed = words_and_timed("titans_from_zero")
    late = copy.deepcopy(words)
    late["words"][-1]["e"] = words["duration"] + 5
    with pytest.raises(ContractError, match="past the"):
        SP.compile_spine(late, timed, refs=REFS)
    other = copy.deepcopy(timed)
    other["duration"] = timed["duration"] + 2 / timed["fps"]
    with pytest.raises(ContractError, match="not the same read"):
        SP.compile_spine(words, other, refs=REFS)
    within = copy.deepcopy(timed)
    within["duration"] = timed["duration"] + 0.5 / timed["fps"]  # inside one frame: the same read
    SP.compile_spine(words, within, refs=REFS)


def test_a_segment_the_read_skipped_raises():
    words, timed = words_and_timed("syndicate_wars_ep1")
    skipped = copy.deepcopy(timed)
    skipped["segments"].append({"id": "S99", "beat": "ghost", "start": 1.0, "end": 2.0})
    with pytest.raises(ContractError, match="S99"):
        SP.compile_spine(words, skipped, refs=REFS)
    shuffled = copy.deepcopy(timed)
    shuffled["segments"][0], shuffled["segments"][1] = shuffled["segments"][1], shuffled["segments"][0]
    with pytest.raises(ContractError, match="timed order"):
        SP.compile_spine(words, shuffled, refs=REFS)


def test_without_a_p6_marker_there_are_no_windows_even_for_dialogue_shots():
    words, timed = words_and_timed("titans_from_zero")
    shots = {"schema": "film_shots/2", "shots": [{"id": "s1", "lane": "DIALOGUE_CU", "duration_frames": 49,
                                                 "dialogue": {"who": "a", "to": "b", "text": "Hello."}}]}
    assert SP.windows(shots, words["words"], timed["lines"], 30) == []
    assert SP.windows(None, words["words"], timed["lines"], 30) == []
    spine = SP.compile_spine(words, timed, film_shots=shots, refs=REFS)
    assert spine["schema"] == "audio_spine/2" and spine["post_hoc_shots"] == []  # film_shots alone makes it a /2, with no window
    assert spine["derived_from"]["film_shots"] == REFS["film_shots"]
    assert spine["words"] == SP.compile_spine(words, timed, refs=REFS)["words"]
    with pytest.raises(ContractError, match="refs"):
        SP.compile_spine(words, timed, film_shots=shots, refs={"words": REFS["words"], "timed": REFS["timed"]})


def _native(timed, line, frames=49, shot_id="s9"):
    return [{"shot_id": shot_id, "line": line, "frames": frames}]


def test_the_window_opens_after_the_last_word_before_its_line():
    words, timed = words_and_timed("titans_from_zero")
    wl = [k for _s, k in SP.word_segments(words["words"], timed["lines"])]
    first_of_line_3 = wl.index(3)
    (h,) = SP.windows(None, words["words"], timed["lines"], 30, native=_native(timed, 3))
    assert h == {"shot_id": "s9", "after_word": first_of_line_3 - 1, "frames": 49}
    (h,) = SP.windows(None, words["words"], timed["lines"], 30, native=_native(timed, 0))
    assert h["after_word"] == -1  # before the first word
    for bad in (_native(timed, 9999), _native(timed, 3, frames=0)):
        with pytest.raises(ContractError):
            SP.windows(None, words["words"], timed["lines"], 30, native=bad)


def test_a_window_moves_later_words_and_read_time_inverts_it():
    """D-88: one 49-frame window after word 10; word 11 and everything after move by 49 frames; read_time takes it back out."""
    words, timed = words_and_timed("titans_from_zero")
    plain = SP.compile_spine(words, timed, refs=REFS)
    after = 10
    wl = [w["line"] for w in plain["words"]]
    line = next(wl[i] for i in range(after + 1, len(wl)) if wl[i] > wl[after])  # a native line right after word 10's line
    native = _native(timed, line)
    got = SP.windows(None, words["words"], timed["lines"], 30, native=native)
    anchor = got[0]["after_word"]
    spine = SP.compile_spine(words, timed, native=native, refs=REFS)
    assert spine["schema"] == "audio_spine/2" and C.errors(spine) == []
    (win,) = spine["post_hoc_shots"]
    assert win["after_word"] == anchor and win["source"] == "planned" and win["clip_sha256"] is None
    assert win["end_frame"] - win["start_frame"] == 49
    assert win["start_frame"] == plain["words"][anchor]["end_frame"]  # opens right after the last read word before it
    assert spine["total_frames"] == plain["total_frames"] + 49
    assert spine["duration_s"] == round(plain["duration_s"] + 49 / 30, 3)
    for a, b in zip(plain["words"], spine["words"]):
        moved = 49 if a["i"] > anchor else 0
        assert b["start_frame"] == a["start_frame"] + moved and b["end_frame"] == a["end_frame"] + moved, a["i"]
        assert b["start_frame"] == round(b["start_s"] * 30) and b["end_frame"] == round(b["end_s"] * 30)
        assert abs((b["start_s"] - a["start_s"]) - moved / 30) <= 0.5 / 30 + 0.001  # the frame is exact, the seconds within half a frame
        assert not (b["start_frame"] < win["end_frame"] and b["end_frame"] > win["start_frame"])  # no word inside the window
        assert SP.read_time(spine, b["start_frame"]) == a["start_frame"] / 30  # read_time inverts the shift
    mid = (win["start_frame"] + win["end_frame"]) // 2
    assert SP.read_time(spine, mid) == SP.read_time(spine, win["start_frame"])  # the read waits inside a window
    assert SP.read_time(spine, 0) == 0.0 and SP.read_time(plain, 123) == 123 / 30  # no window, no shift
    assert [s["id"] for s in spine["segments"]] == [s["id"] for s in plain["segments"]]


def test_two_windows_after_the_same_word_stack_and_in_order():
    words, timed = words_and_timed("syndicate_wars_ep1")
    native = [{"shot_id": "b", "line": 2, "frames": 24}, {"shot_id": "a", "line": 2, "frames": 36}]
    spine = SP.compile_spine(words, timed, native=native, refs=REFS)
    a, b = spine["post_hoc_shots"]
    assert (a["shot_id"], b["shot_id"]) == ("b", "a") and a["after_word"] == b["after_word"]
    assert b["start_frame"] == a["end_frame"] and spine["total_frames"] == timed["frames"] + 60
    plain = SP.compile_spine(words, timed, refs=REFS)
    nxt = a["after_word"] + 1
    assert spine["words"][nxt]["start_frame"] == plain["words"][nxt]["start_frame"] + 60
    assert SP.read_time(spine, spine["words"][nxt]["start_frame"]) == plain["words"][nxt]["start_frame"] / 30


def test_a_window_before_the_first_word_shifts_the_whole_read():
    words, timed = words_and_timed("syndicate_wars_ep1")
    spine = SP.compile_spine(words, timed, native=_native(timed, 0, frames=12), refs=REFS)
    (win,) = spine["post_hoc_shots"]
    assert (win["after_word"], win["start_frame"], win["end_frame"]) == (-1, 0, 12)
    assert spine["words"][0]["start_frame"] == 12 and SP.read_time(spine, 12) == 0.0


def test_retime_replaces_the_planned_length_with_the_clip_and_moves_what_follows():
    words, timed = words_and_timed("titans_from_zero")
    native = [{"shot_id": "s9", "line": 4, "frames": 49}, {"shot_id": "s10", "line": 20, "frames": 30}]
    spine = SP.compile_spine(words, timed, native=native, refs=REFS)
    snapshot = copy.deepcopy(spine)
    sha = "c" * 64
    new = SP.retime_post_hoc(spine, "s9", 73, sha)
    assert spine == snapshot  # nothing is edited in place
    w9, w10 = new["post_hoc_shots"]
    assert (w9["source"], w9["clip_sha256"]) == ("clip", sha) and w9["end_frame"] - w9["start_frame"] == 73
    assert w10["source"] == "planned" and w10["start_frame"] == snapshot["post_hoc_shots"][1]["start_frame"] + 24
    assert new["total_frames"] == spine["total_frames"] + 24
    for a, b in zip(spine["words"], new["words"]):
        moved = 24 if a["start_frame"] >= snapshot["post_hoc_shots"][0]["end_frame"] else 0
        assert b["start_frame"] == a["start_frame"] + moved, a["i"]
    assert C.errors(new) == []
    again = SP.retime_post_hoc(new, "s10", 10, sha)  # a shorter clip moves the rest back; read_time still inverts
    assert again["total_frames"] == new["total_frames"] - 20
    plain = SP.compile_spine(words, timed, refs=REFS)
    for a, b in zip(plain["words"], again["words"]):
        assert SP.read_time(again, b["start_frame"]) == pytest.approx(a["start_frame"] / 30, abs=1e-9)
    same = SP.retime_post_hoc(spine, "s9", 49, sha)  # the planned length held: only the source changes
    assert same["words"] == spine["words"] and same["post_hoc_shots"][0]["source"] == "clip"


def test_retime_refuses_what_it_cannot_anchor():
    words, timed = words_and_timed("titans_from_zero")
    spine = SP.compile_spine(words, timed, native=_native(timed, 4), refs=REFS)
    with pytest.raises(ContractError, match="no-such"):
        SP.retime_post_hoc(spine, "no-such", 40, "c" * 64)
    with pytest.raises(ContractError):
        SP.retime_post_hoc(spine, "s9", 0, "c" * 64)
    with pytest.raises(ContractError):
        SP.retime_post_hoc(spine, "s9", 40, "not-a-hash")
    with pytest.raises(ContractError, match="audio_spine/2"):
        SP.retime_post_hoc(SP.compile_spine(words, timed, refs=REFS), "s9", 40, "c" * 64)


def test_the_cli_writes_a_fresh_spine_and_a_changed_input_makes_it_stale(tmp_path, capsys):
    job = tmp_path / "job"
    (job / "audio").mkdir(parents=True)
    shutil.copy(ROOT / "examples" / "syndicate_wars_ep1" / "words.json", job / "audio" / "words.json")
    shutil.copy(ROOT / "examples" / "syndicate_wars_ep1" / "timed.json", job / "timed.json")
    assert SP.main([str(job)]) == 0
    out = job / "audio" / "audio_spine.json"
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "audio_spine/1" and doc["derived_from"]["words"]["path"] == "audio/words.json"
    assert C.errors(doc, job) == []
    first = out.read_bytes()
    assert SP.main([str(job)]) == 0 and out.read_bytes() == first  # deterministic
    (job / "timed.json").write_bytes((job / "timed.json").read_bytes() + b" ")
    assert {f["rule"] for f in C.errors(doc, job)} == {"CN-02"}
    shots = job / "film_shots.json"
    shots.write_text(json.dumps({"schema": "film_shots/2", "shots": []}), encoding="utf-8")
    assert SP.main([str(job)]) == 0
    assert json.loads(out.read_text(encoding="utf-8"))["schema"] == "audio_spine/2"
    bad = json.loads((job / "audio" / "words.json").read_text(encoding="utf-8"))
    bad["words"][3], bad["words"][4] = bad["words"][4], bad["words"][3]
    (job / "audio" / "words.json").write_text(json.dumps(bad), encoding="utf-8")
    before = out.read_bytes()
    assert SP.main([str(job)]) == 1 and out.read_bytes() == before  # a refused compile writes nothing
    assert "out of order" in capsys.readouterr().out
    assert SP.main([]) == 2
