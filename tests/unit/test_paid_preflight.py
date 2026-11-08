"""D-121 / AS-14: no paid Modal run on a rule FAIL. The c3 prompt that was paid on 2026-11-07 fails here (time labels, story names,
a frozen settle, two camera moves, no 'single continuous shot', the phone not kept); the Gemini-review rewrite passes. Both Modal
launchers run the preflight before the go gate and before .remote()."""
import ast
import json
from pathlib import Path

import pytest

from explainer_engine.production import paid_preflight as PF

C3_PROMPT = ("Hand-drawn 2D cartoon animation with bold black ink outlines and flat bright colours; snappy cartoon timing. "
             "A dark cave hall lit only by dim embers. The camera pushes in slowly toward Marcus. In the first three seconds he lifts "
             "the phone higher and its screen switches on with a small cold glow. Then a wide beam of cold white light bursts from the "
             "phone and floods the whole hall, the gold painted towers on the back wall flare, long shadows swing across the "
             "stalactites. The three hunters stagger, one after another drop to their knees and press their foreheads to the floor, "
             "spears clattering down. Ura stands completely still, the drum lowered, his antlers lit white. In the last two seconds "
             "the camera stops and holds: Marcus stands in the steady white light with the phone out, eyes wide, the hunters kneeling. "
             "We hear a faint crackle of embers, a click and a rising electronic hum, a gust of wind, gasps, spears clattering on stone, "
             "bodies sinking to the floor, then a steady low hum.")
V3_PROMPT = ("Hand-drawn 2D cartoon animation with bold black ink outlines and flat bright colours; snappy cartoon timing. "
             "A single continuous unbroken shot in a dark cave hall lit by dim embers. The young man in the grey hoodie keeps the "
             "glowing phone raised in his right hand as its screen flares and a wide beam of cold white light floods the hall; the "
             "three fur-clad hunters stagger, drop to their knees and press their foreheads to the stone floor while their chests rise "
             "and fall. The tall shaman in the antlered deer-skull mask leans back, his robe stirring, his antlers lit white, and "
             "everyone stays in frame. The camera pushes in slowly and ends on a medium shot of the young man in the steady white light. "
             "We hear: crackling embers, a rising electric hum, wooden spears clattering on stone.")


def job(prompt, **kw):
    return {"id": "c3b", "prompt": prompt, "frames": 185, "fps": 24, "held_props": ["phone"], **kw}


def test_the_paid_c3_prompt_fails():
    bad = "\n".join(PF.ltx({"names": ["Marcus", "Ura"], "jobs": [job(C3_PROMPT, frames=361)]}))
    for rule in ("KP-59", "KP-22", "KP-55", "KP-62", "KP-61", "KP-11", "KP-49"):
        assert rule in bad, rule


def test_the_review_rewrite_passes():
    assert PF.ltx({"names": ["Marcus", "Ura"], "jobs": [job(V3_PROMPT)]}) == []


def test_a_jobs_file_without_names_fails():
    assert "KP-22" in PF.ltx({"jobs": [job(V3_PROMPT)]})[0]


def test_dropping_the_held_prop_fails_unless_planned():
    p = V3_PROMPT.replace("keeps the glowing phone raised in his right hand as its screen flares and",
                          "lowers the phone and")
    assert any("KP-60" in b for b in PF.ltx({"names": ["Marcus"], "jobs": [job(p)]}))
    assert not any("KP-60" in b and "lowers" in b for b in PF.ltx({"names": ["Marcus"], "jobs": [job(p, prop_change=True)]}))


def test_refuse_raises_and_qwen_side_uses_scene_reuse(tmp_path):
    f = tmp_path / "j.json"
    f.write_text(json.dumps({"names": ["Marcus"], "jobs": [job(C3_PROMPT)]}))
    with pytest.raises(SystemExit):
        PF.refuse("ltx", f)
    q = {"registry": {"m": "M: man 1.75 m, oval face."}, "inputs": {},
         "groups": [{"lora_weight": 1.0, "jobs": [{"name": "a", "prompt": "xworld style. Scene: x. M: man 1.75 m, oval face.",
                                                   "refs": []}]}]}
    assert any("HI-01" in b for b in PF.qwen(q))
    q["groups"][0]["jobs"][0]["in_shot"] = ["m"]
    assert PF.qwen(q) == []


@pytest.mark.parametrize("name", ["modal_ltx_jobs_v1.py", "modal_qwen_jobs_v15.py"])
def test_launchers_run_the_preflight_before_the_go_gate(name):
    src = (Path(__file__).resolve().parents[2] / "explainer_engine/training/pods/p15" / name).read_text()
    tree = ast.parse(src)
    entry = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name in ("main", "smoke")]
    assert len(entry) == 2
    for fn in entry:
        calls = [c.func.id for c in ast.walk(fn) if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)]
        assert calls.index("preflight") < calls.index("go_gate"), fn.name


LEGACY_LAUNCHERS = [
    "modal_qwen_jobs.py",
    "modal_qwen_jobs_v3.py",
    "modal_qwen_jobs_v5.py",
    "modal_qwen_jobs_v6.py",
    "modal_qwen_jobs_v8.py",
    "modal_qwen_jobs_v9.py",
    "modal_qwen_jobs_v10.py",
    "modal_qwen_jobs_v11.py",
    "modal_qwen_jobs_v12.py",
    "modal_qwen_jobs_v13.py",
    "modal_sa_test.py",
]


@pytest.mark.parametrize("name", LEGACY_LAUNCHERS)
def test_superseded_paid_launchers_refuse_before_any_remote_call(name):
    src = (Path(__file__).resolve().parents[2] / "explainer_engine/training/pods/p15" / name).read_text()
    tree = ast.parse(src)
    for entry_name in ("smoke", "main"):
        entry = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == entry_name)
        first = entry.body[0]
        assert isinstance(first, ast.Expr)
        assert isinstance(first.value, ast.Call)
        assert isinstance(first.value.func, ast.Name)
        assert first.value.func.id == "retired_launcher"
