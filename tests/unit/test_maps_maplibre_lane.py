"""Browser-free tests for the G-04c MapLibre lane (render.py driver, fetch_tiles.py, page.html contract).

Playwright and ffmpeg are replaced by fakes; no network, no browser. Needs test_spec.json / front_line.geojson
fixtures next to this file's parent (wave-1 shot) or the tmp_path spec built below.
"""
import json
import re
import subprocess
import sys
import types
import urllib.error
from pathlib import Path

import pytest

if "playwright" not in sys.modules:
    try:
        import playwright.sync_api  # noqa: F401
    except ImportError:  # CI box without the python playwright package
        _m = types.ModuleType("playwright")
        _s = types.ModuleType("playwright.sync_api")
        _s.sync_playwright = lambda: None
        sys.modules["playwright"] = _m
        sys.modules["playwright.sync_api"] = _s

from explainer_engine.maps.maplibre_lane import fetch_tiles as FT
from explainer_engine.maps.maplibre_lane import render as R
from explainer_engine.maps.maplibre_spec import frame_count, schedule

LANE = Path(R.__file__).parent
LINE = {"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {}, "geometry": {
    "type": "LineString", "coordinates": [[2.75, 51.13], [2.885, 50.851], [2.807, 50.534]]}}]}


def _film():
    """An episode film whose map style is the 1917 preset (built from the episode_film fixture)."""
    film = json.loads((Path(__file__).resolve().parents[1] / "fixtures" / "episode_film" / "valid_film.json").read_text("utf-8"))
    film["film_id"] = "test_film_1917"
    film["map"]["style_preset"] = "1917_film"
    film["counter"]["style_preset"] = "1917_film"
    return film


def make_spec(tmp_path, **over):
    spec = {
        "size": [1280, 704], "fps": 24, "seconds": 5.0, "center": [2.85, 50.8], "zoom": 9.5,
        "line_geojson": "line.geojson", "line_t": [0.4, 3.6],
        "counter": {"from": 0, "to": 100000, "t0": 1.0, "t1": 4.0, "label": "Men at the front (estimate)"},
        "date_chip": [{"t": 0.0, "text": "NOV 1914"}, {"t": 2.2, "text": "DEC 1914"}],
        "towns": [{"name": "Ypres", "lonlat": [2.885, 50.851], "t": 0.5}],
        "font": "preset", "film_file": "episode_film.json", "footnote": "Front line illustrative",
    }
    spec.update(over)
    (tmp_path / "episode_film.json").write_text(json.dumps(_film()), encoding="utf-8")
    (tmp_path / "line.geojson").write_text(json.dumps(LINE), encoding="utf-8")
    p = tmp_path / "spec.json"
    p.write_text(json.dumps(spec), encoding="utf-8")
    return p, spec


# ---------------------------------------------------------------- fetch_tiles
def test_lonlat_to_tile_known_values():
    assert FT.lonlat_to_tile(0.0, 0.0, 1) == (1, 1)
    assert FT.lonlat_to_tile(-180.0, 85.0, 3) == (0, 0)
    assert FT.lonlat_to_tile(180.0, -85.0, 3) == (7, 7)  # clamped, never n
    x, y = FT.lonlat_to_tile(2.85, 50.8, 8)
    assert (x, y) == (130, 85)


def test_iter_bbox_tiles_counts_and_bounds():
    tiles = list(FT.iter_bbox_tiles((2.1, 50.6, 3.6, 51.4), 6, 8))
    assert {t[0] for t in tiles} == {6, 7, 8}
    assert len(tiles) == len(set(tiles))
    for z, x, y in tiles:
        assert 0 <= x < 2 ** z and 0 <= y < 2 ** z
    # one tile at z6, more at higher zoom
    assert sum(1 for t in tiles if t[0] == 6) >= 1
    assert sum(1 for t in tiles if t[0] == 8) > sum(1 for t in tiles if t[0] == 6)


def test_sha256_bytes():
    assert FT.sha256_bytes(b"") == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


TILEJSON = json.dumps({"tiles": ["https://tiles.openfreemap.org/planet/20261115_080022_pt/{z}/{x}/{y}.pbf"]}).encode()


class _Resp:
    def __init__(self, data):
        self._d = data

    def read(self):
        return self._d

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_download_tile_uses_cache_without_network(tmp_path, monkeypatch):
    dest = tmp_path / "a" / "1.pbf"
    dest.parent.mkdir()
    dest.write_bytes(b"cached")
    monkeypatch.setattr(FT.urllib.request, "urlopen", lambda *a, **k: pytest.fail("network used"))
    size, digest = FT._download_tile("https://x/1.pbf", dest)
    assert size == 6 and digest == FT.sha256_bytes(b"cached")


def test_download_tile_writes_file_and_sends_user_agent(tmp_path, monkeypatch):
    seen = {}

    def fake(req, timeout=None):
        seen["ua"] = req.get_header("User-agent")
        return _Resp(b"tile")

    monkeypatch.setattr(FT.urllib.request, "urlopen", fake)
    dest = tmp_path / "v" / "6" / "1" / "2.pbf"
    size, digest = FT._download_tile("https://x/2.pbf", dest)
    assert dest.read_bytes() == b"tile" and size == 4 and digest == FT.sha256_bytes(b"tile")
    assert seen["ua"] == FT.USER_AGENT


def test_fetch_tiles_manifest_and_dem_404(tmp_path, monkeypatch):
    calls = []

    def fake(req, timeout=None):
        url = req.full_url
        if url == FT.OPENFREEMAP_TILEJSON_URL:
            return _Resp(TILEJSON)
        calls.append(url)
        if "terrarium" in url and url.endswith("/0.png"):
            raise urllib.error.HTTPError(url, 404, "nf", {}, None)
        return _Resp(url.encode())

    monkeypatch.setattr(FT.urllib.request, "urlopen", fake)
    bbox = (2.1, 50.6, 3.6, 51.4)
    m = FT.fetch_tiles(bbox, tmp_path, min_zoom=6, max_zoom=7, dem_max_zoom=6, delay_sec=0)
    assert m["tile_count"] == len(m["tiles"]) == len(calls)
    assert m["dem_max_zoom"] == 6
    kinds = {t["kind"] for t in m["tiles"]}
    assert kinds == {"vector", "dem"}
    assert all(t["z"] <= 6 for t in m["tiles"] if t["kind"] == "dem")
    on_disk = json.loads((tmp_path / "manifest.json").read_text())
    assert on_disk["schema"] == "explainer_engine.offline_tiles.v1" and on_disk["bbox"] == list(bbox)
    for t in m["tiles"]:
        assert (tmp_path / t["path"]).read_bytes() and len(t["sha256"]) == 64


def test_fetch_tiles_vector_http_error_propagates(tmp_path, monkeypatch):
    def fake(req, timeout=None):
        raise urllib.error.HTTPError(req.full_url, 500, "boom", {}, None)

    monkeypatch.setattr(FT.urllib.request, "urlopen", fake)
    with pytest.raises(urllib.error.HTTPError):
        FT.fetch_tiles((2.1, 50.6, 3.6, 51.4), tmp_path, 6, 6, 6, 0, vector_template="https://x/{z}/{x}/{y}.pbf")


def test_main_refuses_without_yes_and_never_touches_network(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(FT.urllib.request, "urlopen", lambda *a, **k: pytest.fail("network used"))
    assert FT.main(["--tile-dir", str(tmp_path / "t")]) == 2
    assert "--yes" in capsys.readouterr().err
    assert not (tmp_path / "t").exists()


def test_main_with_yes_calls_fetch(tmp_path, monkeypatch, capsys):
    got = {}
    monkeypatch.setattr(FT, "fetch_tiles", lambda **kw: got.update(kw) or {"tile_count": 3})
    assert FT.main(["--tile-dir", str(tmp_path), "--yes", "--min-zoom", "7", "--max-zoom", "9"]) == 0
    assert got["bbox"] == (2.1, 50.6, 3.6, 51.4) and got["min_zoom"] == 7 and got["max_zoom"] == 9
    assert "3 tiles" in capsys.readouterr().out


def test_parse_args_requires_tile_dir():
    with pytest.raises(SystemExit):
        FT.parse_args([])


def test_vector_urls_carry_the_planet_version_from_tilejson(tmp_path, monkeypatch):
    """The bare planet/{z}/{x}/{y}.pbf path answers 200 with 0 bytes (checked live 2026-11-20); the version is required."""
    urls = []

    def fake(req, timeout=None):
        if req.full_url == FT.OPENFREEMAP_TILEJSON_URL:
            return _Resp(TILEJSON)
        urls.append(req.full_url)
        return _Resp(b"x")

    monkeypatch.setattr(FT.urllib.request, "urlopen", fake)
    m = FT.fetch_tiles((2.1, 50.6, 3.6, 51.4), tmp_path, 6, 6, 5, 0)
    vec = [u for u in urls if "openfreemap" in u]
    assert vec and all(re.search(r"/planet/\d{8}_\d{6}\w*/6/\d+/\d+\.pbf$", u) for u in vec)
    assert re.search(r"/planet/\d{8}_", m["sources"]["vector"])


def test_resolve_vector_template_rejects_bad_tilejson(monkeypatch):
    monkeypatch.setattr(FT.urllib.request, "urlopen", lambda *a, **k: _Resp(b'{"tiles": []}'))
    with pytest.raises(ValueError):
        FT.resolve_vector_template()


# ---------------------------------------------------------------- render helpers
def test_projection_center_and_zoom_scale():
    x, y = R._lonlat_to_pixel(2.85, 50.8, (2.85, 50.8), 9.5, (1280, 704))
    assert (round(x, 6), round(y, 6)) == (640.0, 352.0)
    x1, _ = R._lonlat_to_pixel(2.95, 50.8, (2.85, 50.8), 9.0, (1280, 704))
    x2, _ = R._lonlat_to_pixel(2.95, 50.8, (2.85, 50.8), 10.0, (1280, 704))
    assert (x2 - 640) == pytest.approx(2 * (x1 - 640))
    # east is right, north is up
    xe, _ = R._lonlat_to_pixel(2.95, 50.8, (2.85, 50.8), 9.5, (1280, 704))
    _, yn = R._lonlat_to_pixel(2.85, 50.9, (2.85, 50.8), 9.5, (1280, 704))
    assert xe > 640 and yn < 352


def test_projection_matches_web_mercator_512():
    # 1 degree of longitude at zoom z spans 512*2^z/360 px
    x, _ = R._lonlat_to_pixel(1.0, 0.0, (0.0, 0.0), 3.0, (100, 100))
    assert x - 50 == pytest.approx(512 * 8 / 360)


@pytest.mark.parametrize("geo,n", [
    (LINE, 3),
    (LINE["features"][0], 3),
    (LINE["features"][0]["geometry"], 3),
    ({"type": "MultiLineString", "coordinates": [[[0, 0], [1, 1]], [[5, 5], [6, 6]]]}, 2),
    ({"type": "Point", "coordinates": [0, 0]}, 0),
    ({}, 0),
])
def test_extract_line_coords(geo, n):
    assert len(R._extract_line_coords(geo)) == n


def test_extract_line_coords_skips_short_first_feature():
    fc = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "geometry": {"type": "LineString", "coordinates": [[0, 0]]}},
        LINE["features"][0]]}
    assert len(R._extract_line_coords(fc)) == 3


def test_avoid_boxes_cover_line_towns_footnote(tmp_path):
    _, spec = make_spec(tmp_path)
    coords = R._extract_line_coords(LINE)
    boxes = R._build_avoid_boxes(spec, coords, (1280, 704))
    assert len(boxes) == 2 + 1 + 1  # line bbox, line end, one town, footnote
    assert boxes[-1] == (960.0, 660.0, 1280.0, 704.0)
    nobox = R._build_avoid_boxes({**spec, "towns": [], "footnote": ""}, [], (1280, 704))
    assert nobox == []


def test_resolve_line_geojson_relative_to_spec(tmp_path):
    p, spec = make_spec(tmp_path)
    assert R._resolve_line_geojson(p, spec) == LINE


def test_validate_hud_palette_passes():
    R._validate_hud_palette(R.load_style_preset("1917_film"))


def test_hud_palette_failure_raises(monkeypatch):
    monkeypatch.setattr(R, "check_palette", lambda *a, **k: ["bad pair"])
    with pytest.raises(ValueError, match="bad pair"):
        R._validate_hud_palette(R.load_style_preset("1917_film"))


def test_counter_slot_for_wave1_shot_is_free_of_line_and_towns(tmp_path):
    from explainer_engine.maps.hud_layout import boxes_overlap
    _, spec = make_spec(tmp_path)
    boxes = R._build_avoid_boxes(spec, R._extract_line_coords(LINE), (1280, 704))
    from explainer_engine.maps.hud_layout import place_counter
    box = place_counter((1280, 704), R.DEFAULT_COUNTER_SIZE, boxes)
    assert not any(boxes_overlap(box, b) for b in boxes)


# ---------------------------------------------------------------- render_shot with fakes
class _FakePage:
    def __init__(self, log):
        self.log = log

    def goto(self, url, wait_until=None):
        self.log["goto"] = url

    def evaluate(self, js, arg=None):
        if "initScene" in js:
            self.log["boot"] = arg
        elif "setFrame" in js:
            self.log.setdefault("frames", []).append(arg)

    def screenshot(self, path, type=None):
        Path(path).write_bytes(b"png")


class _FakeContext:
    def __init__(self, log):
        self.log = log

    def route(self, pattern, fn):
        self.log["route"] = fn

    def new_page(self):
        return _FakePage(self.log)


class _FakeBrowser:
    def __init__(self, log):
        self.log = log

    def new_context(self, **kw):
        self.log["ctx"] = kw
        return _FakeContext(self.log)

    def close(self):
        self.log["closed"] = True


class _FakePW:
    def __init__(self, log):
        self.chromium = types.SimpleNamespace(launch=lambda **kw: (log.update(launch=kw) or _FakeBrowser(log)))

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _fake_lane(tmp_path, monkeypatch, vendor=True):
    lane = tmp_path / "lane"
    (lane / "vendor").mkdir(parents=True)
    (lane / "page.html").write_text("<html></html>")
    if vendor:
        (lane / "vendor" / "maplibre-gl.js").write_text("//")
        (lane / "vendor" / "maplibre-gl.css").write_text("/**/")
    monkeypatch.setattr(R, "__file__", str(lane / "render.py"))
    return lane


def _run(tmp_path, monkeypatch, **spec_over):
    p, spec = make_spec(tmp_path, **spec_over)
    tiles = tmp_path / "tiles"
    (tiles / "vector").mkdir(parents=True)
    log = {}
    run = {}
    _fake_lane(tmp_path, monkeypatch)
    monkeypatch.setattr(R, "sync_playwright", lambda: _FakePW(log))
    monkeypatch.setattr(R.subprocess, "run", lambda cmd, **kw: run.update(cmd=cmd, kw=kw) or subprocess.CompletedProcess(cmd, 0))
    out = R.render_shot(str(p), str(tmp_path / "o" / "x.mp4"), str(tiles), str(tmp_path / "work"))
    return out, spec, log, run


def test_render_shot_frames_and_return_value(tmp_path, monkeypatch):
    out, spec, log, run = _run(tmp_path, monkeypatch)
    assert out["frames"] == frame_count(spec) == 120
    assert out["seconds"] == pytest.approx(5.0)
    assert out["mp4"] == str((tmp_path / "o" / "x.mp4").resolve())
    assert log["frames"] == list(range(120))
    assert len(list((tmp_path / "work" / "frames").glob("frame_*.png"))) == 120
    assert log["closed"] is True


def test_render_shot_boot_payload_matches_schedule(tmp_path, monkeypatch):
    out, spec, log, _ = _run(tmp_path, monkeypatch)
    boot = log["boot"]
    assert len(boot["frames"]) == 120
    assert boot["frames"][0]["line_u"] == 0.0 and boot["frames"][0]["counter"] == 0
    assert boot["frames"][119] == schedule(spec, 119)
    assert boot["spec"]["font"] == "preset"  # the font comes from the film preset, not from the spec
    assert boot["preset"]["name"] == "1917_film" and "Liberation Serif" in boot["preset"]["font"]
    assert boot["vectorTileUrl"].endswith("/vector/{z}/{x}/{y}.pbf") and boot["vectorTileUrl"].startswith("file://")
    assert boot["demTileUrl"] is None and boot["style"] is None
    cb = boot["hudLayout"]["counter_box"]
    assert cb[0] >= 48 and cb[1] >= 48


def test_render_shot_offline_and_blocks_network(tmp_path, monkeypatch):
    _, _, log, _ = _run(tmp_path, monkeypatch)
    assert log["ctx"]["offline"] is True and log["ctx"]["viewport"] == {"width": 1280, "height": 704}
    seen = []
    route = types.SimpleNamespace(request=types.SimpleNamespace(url="https://tiles.openfreemap.org/x"),
                                  abort=lambda r: seen.append(("abort", r)), continue_=lambda: seen.append(("ok",)))
    log["route"](route)
    route.request.url = "file:///tmp/a"
    log["route"](route)
    assert seen == [("abort", "blockedbyclient"), ("ok",)]


def test_render_shot_ffmpeg_command(tmp_path, monkeypatch):
    _, _, _, run = _run(tmp_path, monkeypatch)
    cmd = run["cmd"]
    assert cmd[0] == "ffmpeg" and "libx264" in cmd and "yuv420p" in cmd
    assert cmd[cmd.index("-framerate") + 1] == "24"
    assert cmd[-1].endswith("x.mp4") and run["kw"]["check"] is True


def test_render_shot_uses_stripped_style_json_when_present(tmp_path, monkeypatch):
    p, spec = make_spec(tmp_path)
    tiles = tmp_path / "tiles"
    (tiles / "vector").mkdir(parents=True)
    (tiles / "dem").mkdir()
    (tiles / "style.json").write_text(json.dumps({"version": 8, "sources": {}, "layers": [
        {"id": "bg", "type": "background"}, {"id": "lab", "type": "symbol"}]}))
    log = {}
    _fake_lane(tmp_path, monkeypatch)
    monkeypatch.setattr(R, "sync_playwright", lambda: _FakePW(log))
    monkeypatch.setattr(R.subprocess, "run", lambda cmd, **kw: subprocess.CompletedProcess(cmd, 0))
    R.render_shot(str(p), str(tmp_path / "x.mp4"), str(tiles), str(tmp_path / "w"))
    assert [l["id"] for l in log["boot"]["style"]["layers"]] == ["bg"]
    assert log["boot"]["demTileUrl"].endswith("/dem/{z}/{x}/{y}.png")


def test_render_shot_missing_tile_dir(tmp_path, monkeypatch):
    p, _ = make_spec(tmp_path)
    _fake_lane(tmp_path, monkeypatch)
    with pytest.raises(FileNotFoundError):
        R.render_shot(str(p), str(tmp_path / "x.mp4"), str(tmp_path / "nope"), str(tmp_path / "w"))


def test_render_shot_invalid_spec_raises_before_any_browser(tmp_path, monkeypatch):
    from explainer_engine.maps.maplibre_spec import ShotSpecError
    p = tmp_path / "bad.json"
    p.write_text("{}")
    monkeypatch.setattr(R, "sync_playwright", lambda: pytest.fail("browser started"))
    with pytest.raises(ShotSpecError):
        R.render_shot(str(p), str(tmp_path / "x.mp4"), str(tmp_path), str(tmp_path / "w"))


def test_render_shot_does_not_wipe_other_files_in_work_dir(tmp_path, monkeypatch):
    keep = tmp_path / "work" / "keep.txt"
    keep.parent.mkdir()
    keep.write_text("x")
    _run(tmp_path, monkeypatch)
    assert keep.exists()


def test_render_shot_fractional_fps_is_not_rounded_in_ffmpeg(tmp_path, monkeypatch):
    """23.976 fps: frames come from fps*seconds, the ffmpeg input rate must not be rounded to 24."""
    _, _, _, run = _run(tmp_path, monkeypatch, fps=23.976, seconds=1.0)
    assert run["cmd"][run["cmd"].index("-framerate") + 1] != "24"


def test_date_box_stays_inside_frame_for_every_counter_corner(tmp_path):
    """The date chip sits under the counter; a bottom corner would push it off-frame."""
    from explainer_engine.maps.hud_layout import place_counter
    for prefer in (("bottom_left",), ("bottom_right",)):
        box = place_counter((1280, 704), R.DEFAULT_COUNTER_SIZE, [], prefer=prefer)
        assert box[3] + 44.0 <= 704 - 0, f"date chip off-frame for {prefer}: counter bottom {box[3]}"


# ---------------------------------------------------------------- page.html contract (static)
def test_page_exposes_api_and_labels_off():
    html = (LANE / "page.html").read_text(encoding="utf-8")
    assert "window.initScene" in html and "window.setFrame" in html
    assert 'type !== "symbol"' in html
    assert 'type: "symbol"' not in html and "text-field" not in html
    assert "preserveDrawingBuffer: true" in html and "fadeDuration: 0" in html
    assert "OKABE" not in html  # colours live in the style presets, the page has none of its own
    neutral = (LANE / "styles" / "neutral.json").read_text(encoding="utf-8")
    assert "#d55e00" in neutral and "#0072b2" in neutral
    assert "https://" not in html.replace("https://www.w3.org", "")  # nothing fetched from the net


def test_page_vendor_refs_are_only_maplibre():
    html = (LANE / "page.html").read_text(encoding="utf-8")
    assert sorted(re.findall(r'(?:src|href)="\./(vendor/[^"]+)"', html)) == ["vendor/maplibre-gl.css", "vendor/maplibre-gl.js"]


def test_render_shot_names_missing_vendor_files(tmp_path, monkeypatch):
    p, _ = make_spec(tmp_path)
    _fake_lane(tmp_path, monkeypatch, vendor=False)
    (tmp_path / "t").mkdir()
    with pytest.raises(FileNotFoundError, match="maplibre-gl"):
        R.render_shot(str(p), str(tmp_path / "x.mp4"), str(tmp_path / "t"), str(tmp_path / "w"))
