"""The hyped read (BP-171, WP-R5): tags per zone, stressed words, chunk reset, audition score."""

import pytest

from explainer_engine.audio import hype_read as HR


def test_each_zone_has_its_own_tag_palette_and_the_hook_is_hotter_than_the_middle():
    assert "shouting" in HR.allowed_tags("hook_0_30s") and "shouting" not in HR.allowed_tags("middle_calm_90_480s")
    assert "softly" in HR.allowed_tags("middle_calm_90_480s")
    with pytest.raises(KeyError):
        HR.allowed_tags("nowhere")


def test_a_line_gets_at_most_one_tag_at_its_start_and_the_calm_zone_none():
    hook = {"text": "This is the GREATEST trade in history.", "start_s": 3}
    assert HR.format_line_for_tts(hook) == "[excited] This is the GREATEST trade in history."
    assert HR.format_line_for_tts({"text": "He walked home.", "start_s": 200}) == "He walked home."
    own = {"text": "[amazed] Ten thousand men.", "start_s": 3}
    assert HR.format_line_for_tts(own) == "[amazed] Ten thousand men."          # the writer's own tag is kept, none added


def test_a_foreign_tag_three_stressed_words_and_a_long_chunk_are_flagged():
    lines = [{"id": "a", "text": "[softly] Look at THIS.", "start_s": 3},
             {"id": "b", "text": "It was HUGE, FAST and LOUD.", "start_s": 3},
             {"id": "c", "text": "The US army and NATO moved.", "start_s": 3},
             {"id": "d", "text": "x" * 700, "chunk": "k1", "seconds": 50, "start_s": 10},
             {"id": "e", "text": "y" * 200, "chunk": "k1", "seconds": 50, "start_s": 12}]
    found = HR.check_prosody_plan(lines)
    by = {(f["rule"], f["where"]) for f in found}
    assert ("HR-01", "a") in by and ("HR-02", "b") in by and ("HR-04", "chunk k1") in by
    assert not any(f["where"] == "c" for f in found)                            # acronyms are not stressed words
    assert all(f["severity"] == "REVIEW" for f in found)


def test_audition_takes_rank_by_the_three_measures():
    good = {"voice": "a", "profile": {"f0_iqr_st": 6.1, "speaking_wps": 3.7, "dynamic_range_db": 11.0}}
    flat = {"voice": "b", "profile": {"f0_iqr_st": 2.0, "speaking_wps": 2.8, "dynamic_range_db": 5.0}}
    mid = {"voice": "c", "profile": {"f0_iqr_st": 5.5, "speaking_wps": 3.0, "dynamic_range_db": 12.0}}
    ranked = HR.rank_audition_takes([flat, mid, good])
    assert [t["voice"] for t in ranked] == ["a", "c", "b"]
    assert ranked[0]["hype"]["score"] == 3 and ranked[2]["hype"]["score"] == 0
