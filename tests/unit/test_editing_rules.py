import shutil
import subprocess

import pytest

from explainer_engine.finish import speed
from explainer_engine.production import assemble, continuity, validate


def shot(i, pic, z0, z1, kind="push", dx=0.0):
    return {"id": f"SH{i:03d}", "picture": pic, "motion": {"kind": kind, "z0": z0, "z1": z1, "dx": dx}}


def test_zoom_continues_on_the_same_picture():
    shots = continuity.chain([shot(1, "a", 1.0, 1.07), shot(2, "a", 1.0, 1.06), shot(3, "b", 1.0, 1.05)])
    assert continuity.findings(shots) == []
    assert shots[1]["render_motion"]["z0"] == pytest.approx(1.07)  # no snap back to 1.0
    assert shots[2]["render_motion"]["z0"] == 1.0  # a new picture starts at its own default view


def test_zoom_past_the_cap_eases_out_not_jumps():
    shots = [shot(1, "a", 1.0, 1.24)] + [shot(2 + k, "a", 1.0, 1.06) for k in range(3)]
    continuity.chain(shots)
    assert continuity.findings(shots) == []
    assert all(s["render_motion"]["z1"] <= continuity.ZMAX for s in shots)


def test_a_snapping_zoom_is_a_fail():
    shots = [shot(1, "a", 1.0, 1.07), shot(2, "a", 1.0, 1.06)]
    for s in shots:
        s["render_motion"] = dict(s["motion"])
    assert [f["rule"] for f in continuity.findings(shots)] == ["ED-02 ZOOM-1"]


def test_chained_motion_box_follows_the_offset():
    m = {"z0": 1.2, "z1": 1.2, "x0": 0.05, "x1": 0.05}
    a = assemble.motion_box(m, 1000, 500, 0.0)
    b = assemble.motion_box(m, 1000, 500, 1.0)
    assert a == b and a[0] > 100


def test_two_music_tracks_together_fail_but_a_crossfade_passes():
    ok = [{"track": "a", "start": 0, "end": 12.5, "gain_db": -21}, {"track": "b", "start": 10, "end": 30, "gain_db": -21}]
    bad = [{"track": "a", "start": 0, "end": 30, "gain_db": -21}, {"track": "b", "start": 10, "end": 30, "gain_db": -21}]
    assert validate.music_findings(ok) == []
    assert [f["rule"] for f in validate.music_findings(bad)] == ["PV-29"]


def test_a_loud_tick_fails():
    f = validate.music_findings([{"track": "clockwork_loop__v1", "start": 0, "end": 9, "gain_db": -20}])
    assert f and f[0]["rule"] == "PV-29"


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="needs ffmpeg")
def test_retime_shortens_by_the_rate(tmp_path):
    src = tmp_path / "s.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=d=4:s=160x90:r=10", "-f", "lavfi", "-i",
                    "sine=f=300:d=4", "-shortest", str(src)], check=True)
    out = speed.retime(src, tmp_path / "o.mp4", 1.15)
    d = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(out)],
                             capture_output=True, text=True).stdout)
    assert d == pytest.approx(4 / 1.15, abs=0.15)
