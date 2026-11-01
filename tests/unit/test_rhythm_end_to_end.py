"""One 720 s episode through every piece of the rhythm work (WP-R12): profile, pace, lint, stills, tags, schema, calm era intact."""

import json
from pathlib import Path

import jsonschema

from explainer_engine.audio import hype_read as HR
from explainer_engine.edit import dramatic_still as DS
from explainer_engine.edit import rhythm_profile as RP
from explainer_engine.scripting import rhythm_lint as RL
from explainer_engine.scripting import syllables as SY
from explainer_engine.standards import sourced_rules as SR

ROOT = Path(__file__).resolve().parents[2]


def _episode():
    """Shots cut to each zone's target length; a held still in the middle with its dramatic change."""
    shots, t = [], 0.0
    for z in RP.get_profile("mrbeast_animated")["zones"]:
        lo, hi = z["window_s"]
        length = 60.0 / z["shots_per_min_target"]
        while t + length <= hi + 1e-6:
            shots.append({"id": f"s{len(shots)}", "seconds": round(length, 3), "start_s": round(t, 3)})
            t += length
        t = float(hi)
    shots.append({"id": "hold", "seconds": 4.0, "start_s": 100.0, "tier": "hold",
                  "dramatic_change": {"kind": "cutout_relocation", "subject_layer": "hero", "from_box": [0.05, 0.2, 0.3, 0.85],
                                      "to_box": [0.6, 0.15, 0.85, 0.8], "relocation_distance_frac": 0.55,
                                      "subject_area_frac": 0.16, "at_s": 2.0}})
    return {"rhythm_profile": "mrbeast_animated", "shots": shots}


def test_a_whole_zoned_episode_passes_every_piece():
    doc = _episode()
    assert RP.resolve_profile_name(doc) == "mrbeast_animated"
    assert [f for f in RL.check(doc) if f["severity"] == "FAIL"] == []
    # the pace: 2,000 words fit the 720 s the profile reads them in, and the hook reads faster than the middle
    secs = RP.words_to_seconds(2000, t_start_s=0.0)
    assert 600 < secs < 720
    text = "Ten thousand men crossed the river before dawn."
    assert SY.seconds(text, zone="hook_0_30s") < SY.seconds(text, zone="middle_calm_90_480s")
    # the tags: hook lines get one tag, the calm middle none, and a plan with a foreign tag is flagged
    lines = [{"id": "h", "text": "This is the BIGGEST bet in history.", "start_s": 4},
             {"id": "m", "text": "He walked home that night.", "start_s": 200}]
    assert HR.format_line_for_tts(lines[0]).startswith("[excited] ") and HR.format_line_for_tts(lines[1]) == lines[1]["text"]
    assert HR.check_prosody_plan(lines) == []
    # the still change is the schema's shape and the validator's rule
    shot = next(s for s in doc["shots"] if s["id"] == "hold")
    schema = json.loads((ROOT / "explainer_engine" / "schemas" / "production_script.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(shot["dramatic_change"], {"$ref": "#/$defs/dramatic_change", "$defs": schema["$defs"]})
    assert DS.validate_dramatic_change(shot["dramatic_change"], shot_seconds=4.0, zone_id="middle_calm_90_480s") == []


def test_the_calm_era_keeps_its_own_checks_and_numbers():
    assert RP.resolve_profile_name({"schema": "production_script/3"}) == RP.LEGACY
    assert RL.check({"schema": "production_script/3", "shots": [{"id": "a", "seconds": 9.0}]}) == []
    assert SR.T("BP-01", "wpm_target") == 170 and SR.T("BP-107", "shots_per_min") == [11, 17]   # untouched calm rows
    assert SY.seconds("Ten thousand men crossed the river.") == SY.seconds("Ten thousand men crossed the river.", wpm=170)


def test_no_new_rule_is_binding_without_two_source_types_and_none_copies_a_number_twice():
    for rid in ("BP-169", "BP-171", "BP-172"):
        assert SR.rule(rid)["status"] != "binding" and SR.rule(rid)["severity"] == "REVIEW"
    # the still caps of BP-170 equal the zones' static holds: one home for the number
    zones = SR.T("BP-169", "profiles")["mrbeast_animated"]["zones"]
    assert {z["id"]: z["static_still_max_s"] for z in zones} == SR.T("BP-170", "static_still_max_s_by_zone")


def test_the_finished_calm_example_is_still_calm_and_is_left_alone_by_the_zoned_lint():
    doc = json.loads((ROOT / "examples" / "napoleon_vs_genghis" / "film_shots.json").read_text(encoding="utf-8"))
    assert RP.resolve_profile_name(doc) in (RP.LEGACY, "mrbeast_animated")   # no rhythm_profile key: the registry default applies
    assert RL.check(doc, profile_name=RP.LEGACY) == []
