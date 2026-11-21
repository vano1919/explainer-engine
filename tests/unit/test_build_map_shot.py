"""build_shot's map lane: kind=map is handed to the maplibre lane with the tile dir; the traced 1914 front is sane and its spec is valid."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from explainer_engine.maps import maplibre_spec as MS
from explainer_engine.maps import trace_front_1914 as TR
from explainer_engine.production import build_map_shot as BM

EX = Path(__file__).resolve().parents[2] / "examples" / "maps" / "truce_front_1914"


def test_tiles_are_required(tmp_path, monkeypatch):
    monkeypatch.delenv("EXPLAINER_MAP_TILES", raising=False)
    with pytest.raises(ValueError):
        BM.build(tmp_path / "s.json", tmp_path / "o.mp4")


def test_the_lane_gets_spec_tiles_and_a_workdir(tmp_path, monkeypatch):
    from explainer_engine.maps.maplibre_lane import render
    seen = {}
    monkeypatch.setattr(render, "render_shot", lambda spec, out, tiles, work: seen.update(spec=spec, tiles=tiles, work=work) or {"frames": 3})
    monkeypatch.setattr(BM, "post", lambda base, out, spec, fp=True: {"frames": 3})
    (tmp_path / "s.json").write_text((EX / "spec.json").read_text())
    log = BM.build(tmp_path / "s.json", tmp_path / "o.mp4", tile_dir=tmp_path / "t")
    assert seen["tiles"].endswith("t") and Path(seen["spec"]).name == "s.json" and log["render"] == {"frames": 3}
    assert (tmp_path / "o.render_log.json").exists() and not Path(seen["work"]).exists()      # temp workdir is cleaned


def test_traced_front_is_sane():
    gj = TR.geojson()
    props = gj["features"][0]["properties"]
    coords = gj["features"][0]["geometry"]["coordinates"]
    assert props["fit_rms_km"] < 15 and "no claim" in props["status"]
    assert 2.5 < coords[0][0] < 3.2 and 51.0 < coords[0][1] < 51.4        # Nieuport on the coast
    assert 7.0 < coords[-1][0] < 7.8 and 47.3 < coords[-1][1] < 47.8      # Swiss border
    assert [c[1] for c in coords][0] > [c[1] for c in coords][-1]          # north to south
    assert json.loads((EX / "front.geojson").read_text())["features"][0]["geometry"]["coordinates"] == coords


def test_the_example_map_spec_is_valid_and_uses_a_listed_move():
    spec = json.loads((EX / "spec.json").read_text())
    assert spec["camera"]["move"] in MS.ALLOWED_CAMERA_MOVES
    probs = MS.validate_shot_spec({k: v for k, v in spec.items() if k != "kind"})
    assert probs == [], probs


def _flat_video(path, secs=1.0):
    import subprocess
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"color=c=0xdfdedb:s=320x180:r=24:d={secs}", "-pix_fmt", "yuv420p", str(path)], check=True)


def _frames(path):
    import cv2
    cap = cv2.VideoCapture(str(path)); out = []
    while True:
        ok, f = cap.read()
        if not ok:
            return out
        out.append(f.astype("float32"))


_SPEC = {"size": [320, 180], "fps": 24, "seconds": 1.0, "center": [3.0, 50.0], "zoom": 6.0, "camera": {"move": "zoom_in", "zoom_from": 6.0, "zoom_to": 6.2, "ease": "smoothstep"},
         "arrows": [{"path": [[1.0, 50.0], [5.0, 50.0]], "t": [0.0, 0.8], "width": 8}]}


def test_post_gives_the_film_look_and_animates_the_arrow(tmp_path):
    src = tmp_path / "s.mp4"; _flat_video(src)
    BM.post(src, tmp_path / "a.mp4", dict(_SPEC), film_post=False)
    BM.post(src, tmp_path / "b.mp4", dict(_SPEC), film_post=True)
    plain, film = _frames(tmp_path / "a.mp4"), _frames(tmp_path / "b.mp4")
    assert len(plain) == len(film) == 24
    assert abs(float((plain[0] - plain[-1]).mean())) > 0.5 and (plain[-1] != plain[0]).any()        # the arrow grows: first frame has none, the last has it
    assert float(plain[0].std(axis=(0, 1)).max()) < 1.0 and float(film[0].std(axis=(0, 1)).max()) > 4.0                               # paper, vignette and grain are laid on the flat map
    assert film[0][..., 2].mean() > film[0][..., 0].mean()                                          # warm: red above blue


def test_post_is_a_pure_function_of_the_frame_number(tmp_path):
    src = tmp_path / "s.mp4"; _flat_video(src)
    BM.post(src, tmp_path / "a.mp4", dict(_SPEC)); BM.post(src, tmp_path / "b.mp4", dict(_SPEC))
    a, b = _frames(tmp_path / "a.mp4"), _frames(tmp_path / "b.mp4")
    assert all((x == y).all() for x, y in zip(a, b)) and not (a[0] == a[1]).all()                   # same frames twice, grain differs between frames


def test_a_map_without_camera_or_film_is_refused_not_rendered_static(tmp_path):
    base = json.loads((EX / "spec.json").read_text())
    for drop in ("camera", "film_file"):
        bad = {k: v for k, v in base.items() if k != drop}
        (tmp_path / "s.json").write_text(json.dumps(bad))
        with pytest.raises(BM.MapShotError):
            BM.build(tmp_path / "s.json", tmp_path / "o.mp4", tile_dir=tmp_path)
    with pytest.raises(BM.MapShotError):
        BM.check_spec(dict(base, camera={"move": "orbit"}))
    with pytest.raises(BM.MapShotError):
        BM.check_spec(dict(base, arrows=[{"path": [[1, 1]], "t": [0, 1]}]))
    BM.check_spec(base)
