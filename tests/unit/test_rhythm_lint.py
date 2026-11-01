"""The multi-zone rhythm lint (BP-169, BP-170; WP-R8)."""

import json
import subprocess
import sys
from pathlib import Path

from explainer_engine.scripting import rhythm_lint as RL

ROOT = Path(__file__).resolve().parents[2]
GOOD_CHANGE = {"kind": "cutout_relocation", "subject_layer": "hero", "from_box": [0.05, 0.2, 0.3, 0.85],
               "to_box": [0.6, 0.15, 0.85, 0.8], "relocation_distance_frac": 0.55, "subject_area_frac": 0.16, "at_s": 1.5}


def _episode(seconds_by_zone):
    """A 720 s episode: each zone is filled with shots of the given length."""
    zones = [("hook", 0, 30), ("early", 30, 90), ("middle", 90, 480), ("late", 480, 660), ("climax", 660, 720)]
    shots = []
    for (_, lo, hi), length in zip(zones, seconds_by_zone):
        n = round((hi - lo) / length)
        shots += [{"id": f"s{len(shots) + i}", "seconds": (hi - lo) / n} for i in range(n)]
    return {"rhythm_profile": "mrbeast_animated", "shots": shots}


def test_a_script_cut_to_the_profile_has_no_findings():
    doc = _episode([2.1, 2.5, 3.5, 2.4, 2.0])
    assert RL.check(doc) == []
    s = RL.summary(doc)
    assert s["profile"] == "mrbeast_animated" and 26 <= s["zones"]["hook_0_30s"]["per_min"] <= 32


def test_calm_cuts_in_the_hook_and_in_the_climax_are_flagged_in_their_zones():
    doc = _episode([4.5, 4.5, 4.5, 4.5, 4.5])
    found = RL.check(doc)
    where = {(f["rule"], f["where"]) for f in found}
    assert ("RL-01", "hook_0_30s") in where and ("RL-01", "climax_660_720s") in where
    assert ("RL-01", "middle_calm_90_480s") in where                    # 13.3 a minute is under the middle's 14
    assert all(f["severity"] == "REVIEW" for f in found if f["rule"] in {"RL-01", "RL-02", "RL-03"})


def test_the_calm_era_is_not_judged_here():
    doc = _episode([4.5] * 5)
    doc["rhythm_profile"] = "calm_docudrama"
    assert RL.check(doc) == []
    assert RL.check({"schema": "production_script/3", "shots": doc["shots"]}) == []


def test_a_held_still_without_a_dramatic_change_fails_and_with_one_passes():
    base = _episode([2.1, 2.5, 3.5, 2.4, 2.0])
    still = {"id": "hold1", "seconds": 4.0, "start_s": 200.0, "tier": "hold"}
    bad = dict(base, shots=base["shots"][:10] + [still])
    found = [f for f in RL.check(bad) if f["rule"] == "RL-04"]
    assert found and found[0]["severity"] == "FAIL" and found[0]["where"] == "hold1"
    ok = dict(base, shots=base["shots"][:10] + [dict(still, dramatic_change=dict(GOOD_CHANGE, at_s=2.0))])
    assert [f for f in RL.check(ok) if f["rule"] == "RL-04"] == []


def test_the_cli_exits_1_on_a_fail(tmp_path):
    doc = _episode([2.1, 2.5, 3.5, 2.4, 2.0])
    doc["shots"].append({"id": "h", "seconds": 4.5, "tier": "hold"})
    p = tmp_path / "shots.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    out = subprocess.run([sys.executable, "-m", "explainer_engine.scripting.rhythm_lint", str(p)], cwd=ROOT,
                         capture_output=True, text=True)
    assert out.returncode == 1 and "RL-04" in out.stdout
