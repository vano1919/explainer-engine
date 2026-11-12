"""production_script/4 carries the rhythm fields (BP-169, BP-170; WP-R6)."""

import pytest


def test_schema_4_accepts_the_rhythm_fields_and_rejects_a_small_change():
    import json
    from pathlib import Path

    import jsonschema
    schema = json.loads((Path(__file__).resolve().parents[2] / "explainer_engine" / "schemas" / "production_script.schema.json")
                        .read_text(encoding="utf-8"))
    assert "production_script/4" in schema["properties"]["schema"]["enum"]
    assert schema["properties"]["voice"]["properties"]["pace_wpm"]["items"]["maximum"] == 250
    assert schema["properties"]["episode"]["properties"]["rhythm_profile"]["enum"] == ["mrbeast_animated", "calm_docudrama"]
    shot = schema["properties"]["segments"]["items"]["properties"]["shots"]["items"]["properties"]["dramatic_change"]
    assert shot == {"$ref": "#/$defs/dramatic_change"}
    dc = {"$ref": "#/$defs/dramatic_change", "$defs": schema["$defs"]}
    good = {"kind": "cutout_relocation", "subject_layer": "hero", "from_box": [0.05, 0.2, 0.3, 0.85],
            "to_box": [0.6, 0.15, 0.85, 0.8], "relocation_distance_frac": 0.5, "subject_area_frac": 0.1, "at_s": 2.0}
    jsonschema.validate(good, dc)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(dict(good, subject_area_frac=0.02), dc)
