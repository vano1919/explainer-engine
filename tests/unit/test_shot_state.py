"""W3: the plan 5.1 shot state machine bound to asset hashes. No media, no network."""
from __future__ import annotations

import json

import pytest

from explainer_engine.core import contracts
from explainer_engine.episode import shot_state as SS

PATH = ["IMAGE_GENERATED", "IMAGE_OBSERVED", "IMAGE_ACCEPTED", "VIDEO_GENERATED", "VIDEO_OBSERVED", "CLIP_ACCEPTED",
        "SCENE_QA", "CREATOR_APPROVAL", "READY_FOR_ASSEMBLY"]


def _root(tmp_path):
    r = tmp_path / "ep_t"
    (r / "assets").mkdir(parents=True)
    (r / "assets" / "p.png").write_bytes(b"picture-1")
    (r / "assets" / "c.mp4").write_bytes(b"clip-1")
    return r


def _walk(st, sid, root, upto):
    for state in PATH[: PATH.index(upto) + 1]:
        kind = SS.ASSET_STATES[state]
        f = "assets/p.png" if kind == "image" else "assets/c.mp4"
        st.advance(sid, state, SS.sha256_of(root / f), f)


def test_the_full_legal_path_walks_to_ready(tmp_path):
    root = _root(tmp_path)
    st = SS.ShotStates(root)
    _walk(st, "S1", root, "READY_FOR_ASSEMBLY")
    assert st.state("S1") == "READY_FOR_ASSEMBLY"
    st.save()
    assert contracts.errors(json.loads((root / SS.REL).read_text())) == []


@pytest.mark.parametrize("a,b", [("PLANNED", "IMAGE_ACCEPTED"), ("PLANNED", "VIDEO_GENERATED"),
                                 ("IMAGE_GENERATED", "IMAGE_ACCEPTED"), ("IMAGE_ACCEPTED", "CLIP_ACCEPTED"),
                                 ("READY_FOR_ASSEMBLY", "PLANNED"), ("VIDEO_OBSERVED", "SCENE_QA")])
def test_illegal_transitions_are_refused(a, b, tmp_path):
    root = _root(tmp_path)
    st = SS.ShotStates(root)
    if a != "PLANNED":
        _walk(st, "S1", root, a)
    with pytest.raises(SS.ShotStateError, match="not allowed"):
        st.advance("S1", b, "x" * 64, "assets/p.png")


def test_an_asset_state_needs_a_hash(tmp_path):
    with pytest.raises(SS.ShotStateError, match="sha256"):
        SS.ShotStates(_root(tmp_path)).advance("S1", "IMAGE_GENERATED")


def test_image_retry_is_capped_at_two(tmp_path):
    root = _root(tmp_path)
    st = SS.ShotStates(root)
    _walk(st, "S1", root, "IMAGE_OBSERVED")
    sha = SS.sha256_of(root / "assets/p.png")
    for _ in range(2):
        st.advance("S1", "IMAGE_RETRY")
        st.advance("S1", "IMAGE_GENERATED", sha, "assets/p.png")
        st.advance("S1", "IMAGE_OBSERVED", sha, "assets/p.png")
    with pytest.raises(SS.ShotStateError, match="cap"):
        st.advance("S1", "IMAGE_RETRY")


def test_video_retry_is_capped_and_the_fallback_is_reachable(tmp_path):
    root = _root(tmp_path)
    st = SS.ShotStates(root)
    _walk(st, "S1", root, "VIDEO_OBSERVED")
    sha = SS.sha256_of(root / "assets/c.mp4")
    for _ in range(2):
        st.advance("S1", "VIDEO_RETRY")
        st.advance("S1", "VIDEO_GENERATED", sha, "assets/c.mp4")
        st.advance("S1", "VIDEO_OBSERVED", sha, "assets/c.mp4")
    with pytest.raises(SS.ShotStateError, match="cap"):
        st.advance("S1", "VIDEO_RETRY")
    st.advance("S1", "FALLBACK_25D")
    assert st.state("S1") == "FALLBACK_25D"


def test_a_changed_file_resets_every_later_state_and_the_old_qa_no_longer_counts(tmp_path):
    root = _root(tmp_path)
    st = SS.ShotStates(root)
    _walk(st, "S1", root, "SCENE_QA")
    st.save()
    assert st.has_valid("S1", "IMAGE_ACCEPTED") and st.has_valid("S1", "SCENE_QA")
    (root / "assets" / "p.png").write_bytes(b"picture-2 (a different picture)")
    assert not st.has_valid("S1", "IMAGE_ACCEPTED")           # the old pass is dead the moment the bytes differ
    found = SS.ShotStates(root).check()
    assert found and found[0]["asset"] == "image" and "IMAGE_ACCEPTED" in found[0]["dropped"]
    st2 = SS.ShotStates(root)
    st2.check()
    assert st2.state("S1") == "PLANNED" and not st2.has_valid("S1", "IMAGE_ACCEPTED")
    assert not st2.has_valid("S1", "SCENE_QA") and st2.shot("S1")["resets"]


def test_a_changed_clip_keeps_the_image_acceptance_but_drops_the_clip_states(tmp_path):
    root = _root(tmp_path)
    st = SS.ShotStates(root)
    _walk(st, "S1", root, "CLIP_ACCEPTED")
    (root / "assets" / "c.mp4").write_bytes(b"clip-2")
    st.check()
    assert st.state("S1") == "IMAGE_ACCEPTED" and st.has_valid("S1", "IMAGE_ACCEPTED")
    assert not st.has_valid("S1", "CLIP_ACCEPTED") and not st.has_valid("S1", "VIDEO_GENERATED")


def test_a_missing_file_resets_like_a_changed_one(tmp_path):
    root = _root(tmp_path)
    st = SS.ShotStates(root)
    _walk(st, "S1", root, "IMAGE_ACCEPTED")
    (root / "assets" / "p.png").unlink()
    st.check()
    assert st.state("S1") == "PLANNED"


def test_the_runner_hooks_bind_pictures_and_clips_and_check_resets(tmp_path):
    root = _root(tmp_path)
    (root / "production").mkdir()
    (root / "production" / "pictures.json").write_text(json.dumps(
        {"pictures": {"S1_start": {"file": "assets/p.png", "grade": "master", "sha256": "x"},
                      "S1_end": {"file": "assets/p.png", "grade": "master", "sha256": "x"}}}))
    (root / "production" / "shot_records.json").write_text(json.dumps(
        {"shots": [{"shot_id": "S1", "clip_path": "assets/c.mp4"}, {"shot_id": "S2", "clip_path": None}]}))
    assert SS.record_stage(root, "pictures") == 1 and SS.record_stage(root, "clips") == 1
    st = SS.ShotStates(root)
    assert st.state("S1") == "IMAGE_GENERATED" and st.shot("S1")["assets"]["clip"]["sha256"] == SS.sha256_of(root / "assets/c.mp4")
    assert SS.record_stage(root, "assemble") == 1 and st.shot("S1")
    (root / "assets" / "p.png").write_bytes(b"changed")
    assert SS.check_all(root)[0]["shot"] == "S1"
    assert SS.ShotStates(root).state("S1") == "PLANNED"


def test_binding_a_new_hash_resets_what_rested_on_the_old_one(tmp_path):
    root = _root(tmp_path)
    st = SS.ShotStates(root)
    st.bind("S1", "image", "assets/p.png")
    st.advance("S1", "IMAGE_OBSERVED", st.sha("S1", "IMAGE_GENERATED"), "assets/p.png")
    (root / "assets" / "p.png").write_bytes(b"retake")
    st.bind("S1", "image", "assets/p.png")
    assert st.state("S1") == "IMAGE_GENERATED" and st.sha("S1", "IMAGE_GENERATED") == SS.sha256_of(root / "assets/p.png")
    assert not st.has_valid("S1", "IMAGE_OBSERVED")
