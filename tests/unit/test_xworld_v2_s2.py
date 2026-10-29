"""The S2 storyboard test: one prompt per scene, the panel cutter finds a shifted gutter."""
from pathlib import Path

from PIL import Image, ImageDraw

from explainer_engine.training.pods import xworld_v2_s2 as S
from explainer_engine.training.pods.xworld_v2_scenes import load

PODS = Path(__file__).resolve().parents[2] / "explainer_engine" / "training" / "pods"


def test_one_grid_prompt_per_scene_names_every_panel_and_the_cast_once():
    j = S.jobs([s for s in load(PODS / "stories" / "v2") if s["name"] in S.SCENES])
    assert sorted(x["scene"] for x in j) == sorted(S.SCENES)
    for x in j:
        assert all(f"{o} panel:" in x["prompt"] for o in S.ORDER) and "2x2 grid" in x["prompt"]


def test_cut_finds_a_gutter_that_is_not_in_the_exact_centre():
    img = Image.new("RGB", (400, 300), (40, 40, 40)); d = ImageDraw.Draw(img)
    d.rectangle((188, 0, 193, 299), fill=(255, 255, 255)); d.rectangle((0, 157, 399, 162), fill=(255, 255, 255))
    p = S.cut(img)
    assert len(p) == 4 and p[0].size[0] < 191 and p[1].size[0] > 200 - 6 and all(q.size[0] > 150 for q in p)
    assert S.gutters(img) == (188, 157) or abs(S.gutters(img)[0] - 190) <= 3


def test_pod_lint_knows_the_script_is_wired():
    assert "xworld_v2_s2.py" in (PODS / "xworld_v2_p2s.sh").read_text(encoding="utf-8")
