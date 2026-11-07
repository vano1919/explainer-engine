"""OR-37: the Modal run guard (cost-derived timeout, in-container deadline, strict success, ladder order, app id stop)."""
import json
import sys
import time
from pathlib import Path

import pytest

from explainer_engine.cloud import modal_run as MR

P15 = Path(__file__).resolve().parents[2] / "explainer_engine" / "training" / "pods" / "p15"
sys.path.insert(0, str(P15))
import modal_sa_test as M  # noqa: E402


def test_timeout_comes_from_the_cap_and_a_hand_set_one_is_refused():
    assert M.cost_timeout(1.0, 2.5) <= 20.5 * 60
    assert M.TIMEOUT_S == M.cost_timeout(M.CAP_USD)
    assert M.SMOKE_TIMEOUT_S == M.cost_timeout(M.SMOKE_CAP_USD)
    assert M.TIMEOUT_S * M.USD_PER_H / 3600 < M.CAP_USD
    with pytest.raises(ValueError):
        M.check_timeout(25 * 60, 1.0)   # the 25-minute plan of 2026-11-07 cost $1.04


def test_deadline_guard_fires_inside_the_container():
    hit = []
    t = M.deadline_guard(0.2, lambda: hit.append(1))
    time.sleep(0.6)
    assert hit == [1]
    t.cancel()


def test_done_only_when_every_expected_output_exists(tmp_path):
    from PIL import Image
    (tmp_path / "qwen").mkdir()
    for n in ("a", "b"):
        Image.new("RGB", (4, 4)).save(tmp_path / "qwen" / f"{n}.png")
    ok = M.verdict(tmp_path, ["qwen/a.png", "qwen/b.png"])
    assert ok == {"state": "DONE", "n_ok": 2, "n_expected": 2}
    part = M.verdict(tmp_path, ["qwen/a.png", "qwen/b.png", "qwen/c.png"])
    assert part["state"] == "FAILED" and part["n_ok"] == 2
    (tmp_path / "qwen" / "b.png").write_bytes(b"")
    assert M.verdict(tmp_path, ["qwen/b.png"])["state"] == "FAILED"


def test_ladder_never_skips_and_stops_at_red():
    assert MR.next_rung([]) == "L0"
    assert MR.next_rung(["L0", "L1"]) == "L2"
    assert MR.next_rung(["L0", "L1"], red="L2") is None
    assert MR.next_rung(list(MR.LADDER)) is None


def test_app_id_and_stop_by_id_not_by_name():
    assert MR.parse_app_id("Created objects. app ap-fT41nd6uVkOnqfLblAl2vw running") == "ap-fT41nd6uVkOnqfLblAl2vw"
    assert MR.parse_app_id("nothing") is None
    rows = json.dumps([{"App ID": "ap-AAAAAAAAAAAA", "Description": "ee-sa-test", "State": "ephemeral"},
                       {"App ID": "ap-BBBBBBBBBBBB", "Description": "ee-sa-test", "State": "stopped"},
                       {"App ID": "ap-CCCCCCCCCCCC", "Description": "other", "State": "ephemeral"}])
    assert MR.stop_target(rows, "ee-sa-test") == ["ap-AAAAAAAAAAAA"]


def test_sa_prompts_are_strings_and_the_runner_unwraps_the_dict():
    """2026-11-07: sa_prompts.json holds {qwen, words, ltx} per name; the dict went to the pipeline as 3 prompts ("Expected 1 got 3")."""
    src = (P15 / "sa_test_qwen.py").read_text(encoding="utf-8")
    assert 'v["qwen"] if isinstance(v, dict)' in src and "isinstance(v, str)" in src
    raw = {"a": {"qwen": "xworld style, one two", "words": 4, "ltx": "x"}, "b": "plain"}
    prompts = {k: (v["qwen"] if isinstance(v, dict) else v) for k, v in raw.items()}
    assert all(isinstance(v, str) for v in prompts.values())


def test_style_strength_trial_names_both_weights():
    """creator 2026-11-07 14:42 UTC: every frame once at 0.7 and once at 1.0; each weight gets its own file name."""
    assert M.WEIGHTS == (0.7, 1.0)
    assert [M.wtag(w) for w in M.WEIGHTS] == ["_w07", "_w10"]
    runner = (Path(M.__file__).parent / "sa_test_qwen.py").read_text()
    assert "--lora-weight" in runner and 'weight=a.lora_weight' in runner
