"""Script data that goes with the five new camera-position pictures (clips lane). Editor-owned fields only (shots*); no word,
no route, no motion item, no handle changes.  Usage: python apply_newangles_fix.py IN_SCRIPT OUT_SCRIPT
S03_SH003: medium_wide@135 -> medium@135 (VL-04: a size step after S03_SH001's medium_wide@135); S04_SH014: medium_wide@90 ->
wide@90 (VL-04: a size step after S04_SH013 and away from S04_SH009's medium_wide@90). S04_SH010, S04_SH012, S05_SH009: the
script already asks for the over-the-shoulder composition; only the pictures change (nothing to edit here)."""
import hashlib
import json
import sys

d = json.load(open(sys.argv[1], encoding="utf-8"))
S = {s["shot_id"]: s for s in d["shots"]}

e = S["S03_SH003"]
e["camera_spec"]["shot_size"] = "medium"
e["screen_composition"] = {"foreground": "the dark edge of the trench wall",
                           "midground": "Friedrich, seen from the chest up, singing, with two soldiers singing at his shoulders",
                           "background": "the candle tree small and soft on the parapet",
                           "screen_direction_notes": "Friedrich looks a little to screen left"}
e["image_prompt"]["start_frame_prompt"] = ("Flanders, Christmas 1914, a frozen winter world. Friedrich and two Saxon soldiers in field-grey caps and "
                                           "greatcoats, seen from the chest up, singing in a trench at night, breath visible, a small candle-lit fir tree "
                                           "soft on the parapet behind them, night, candle glow on the faces.")
e = S["S04_SH014"]
e["camera_spec"]["shot_size"] = "wide"
e["screen_composition"] = {"foreground": "frost on the ground",
                           "midground": "Thomas and Friedrich, two small full-length figures, shaking hands side-on in the empty field",
                           "background": "wire stakes and fog",
                           "screen_direction_notes": "Thomas left, Friedrich right"}
e["image_prompt"]["start_frame_prompt"] = ("Flanders, Christmas 1914, a frozen winter world. Seen from a distance, a young British private on the left and a "
                                           "broad Saxon soldier on the right, two small full-length figures shaking hands side-on in an empty frozen field, "
                                           "frost in the foreground, wire stakes and fog behind, low golden winter morning sun, frost haze.")
txt = json.dumps(d, indent=1, ensure_ascii=False) + "\n"
open(sys.argv[2], "w", encoding="utf-8").write(txt)
print(hashlib.sha256(txt.encode("utf-8")).hexdigest())
