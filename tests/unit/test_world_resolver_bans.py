"""ICW-01 RW-08 (D-102, world bible v1.5): the look's ban list names the real enemy (photoreal, raw CGI, PBR), not 3D.

The UR-22/UR-24 prompt lint of ``world/resolver.py`` reads ``look_v2.banned_words``, so reference-art prompts still refuse a
photoreal look while the Ink Chronicle illustrated-from-3D look is the house look."""
from explainer_engine.world import bible as B
from explainer_engine.world import resolver as R


def test_look_v2_bans_photoreal_raw_cgi_and_pbr_and_no_longer_bans_3d():
    words = R.load_look()["banned_words"]
    assert {"photoreal", "raw cgi", "pbr", "realistic", "unreal engine", "octane"} <= set(words)
    assert "3d render" not in words


def test_the_resolver_lint_flags_a_photoreal_prompt_and_passes_a_3d_word():
    look = R.load_look()
    assert R.words_in("a photoreal harbour at dawn", look["banned_words"]) == ["photoreal"]
    assert R.words_in("a PBR material on the shield", look["banned_words"]) == ["pbr"]
    assert R.words_in("an illustrated 3D tableau of the harbour", look["banned_words"]) == []


def test_bible_v15_bans_photoreal_and_names_blender_as_the_motion_default():
    b = B.load()
    major, minor = map(int, b["version"].split("."))
    assert (major, minor) >= (1, 5)
    drift = " ".join(b["banned_drift"]).lower()
    assert "raw/pbr cgi" in drift and "photo-realism" in drift and "3d-render look" not in drift
    assert "Blender VIDEO_3D / STILL_3D" in b["motion"]["default"]
    assert any("ink_chronicle" in g for g in b["graphics_style"])
    assert B.check() == []  # the parts' hashes are pinned again (rehash)
