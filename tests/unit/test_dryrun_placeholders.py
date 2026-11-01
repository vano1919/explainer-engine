"""Audit 2026-11-01 (#7): a pod never starts on a pin that was never filled; the check reads the script and the job files it names."""
from pathlib import Path

from explainer_engine.cloud import dryrun as D

RUNPOD = Path(__file__).resolve().parents[2] / "explainer_engine" / "cloud" / "runpod.py"
P12 = Path(__file__).resolve().parents[2] / "explainer_engine" / "training" / "pods" / "p12"


def test_a_placeholder_in_the_script_text_is_refused():
    assert D.placeholder_problems("echo ok\n") == []
    probs = D.placeholder_problems('printf %s PLACEHOLDER_SHA_P12B_PY "$JOB/p12b.py"')
    assert len(probs) == 1 and "PLACEHOLDER_SHA_P12B_PY" in probs[0]


def test_a_placeholder_in_a_job_file_the_script_names_is_refused_and_an_unnamed_file_is_not(tmp_path):
    (tmp_path / "job.json").write_text('{"sha256": "PLACEHOLDER_SHA", "voice_id": "PLACEHOLDER"}', encoding="utf-8")
    (tmp_path / "other.json").write_text('{"x": "PLACEHOLDER"}', encoding="utf-8")
    (tmp_path / "clean.py").write_text("x = 1\n", encoding="utf-8")
    script = "fetch job.json clean.py\n"
    probs = D.placeholder_problems(script, tmp_path)
    assert [p.split(":")[0] for p in probs] == ["job.json", "job.json"] and all("PLACEHOLDER" in p for p in probs)
    (tmp_path / "job.json").write_text('{"sha256": "ab"}', encoding="utf-8")
    assert D.placeholder_problems(script, tmp_path) == []


def test_runpod_create_asks_for_it_before_any_money():
    t = RUNPOD.read_text(encoding="utf-8")
    assert "dryrun.placeholder_problems(script, Path(script_file).parent)" in t and 'f"placeholder: {w}"' in t


def test_the_p12_pod_is_refused_until_its_pins_are_filled():
    """True today: p12b.json is filled (clay, keyframes, AV takes: WP-1e, 2026-11-01), the three script sha lines of p12b.sh are
    the last pins, set once the code is final. When this fails the pins are filled and it is deleted with the xfail of test_p12b_pod_script."""
    script = (P12 / "p12b.sh").read_text(encoding="utf-8")
    probs = D.placeholder_problems(script, P12)
    assert any(p.startswith("script: PLACEHOLDER_SHA_P12B_PY") for p in probs)
    assert not any(p.startswith("p12b.json:") for p in probs), probs


# audit 2026-11-01 #15: the weight repos are in p12b.json, not in the script text; a gated repo needs a proof of access
import json
import sys
import types


def test_the_repos_of_the_job_files_are_part_of_the_dry_run_and_the_weights_of_rp02(tmp_path):
    (tmp_path / "job.json").write_text(json.dumps({
        "base": {"repo": "Qwen/Qwen-Image-2.1", "revision": "a"},
        "style": {"hf": "me/art", "path": "x.safetensors"},
        "ltx": {"repo": "Lightricks/LTX-2.5", "revision": "b", "files": ["f"], "keyframes": {"repo": "me/art", "paths": {"s": "p"}},
                "layout": {"repo": "Lightricks/Layout", "revision": "c", "file": "l"}, "av": {"repo": "me/art", "takes": {"a": {"path": "w"}}}},
        "refs": {"repo": "me/refs", "repo_type": "dataset"}}), encoding="utf-8")
    (tmp_path / "unnamed.json").write_text(json.dumps({"x": {"repo": "no/body"}}), encoding="utf-8")
    got = dict(D.all_repo_ids("run job.json\nhf_hub_download('me/art', 'f', repo_type='dataset')\n", tmp_path))
    assert got == {"Qwen/Qwen-Image-2.1": "model", "Lightricks/LTX-2.5": "model", "Lightricks/Layout": "model",
                   "me/art": "dataset", "me/refs": "dataset"}
    seen = []
    rec = D.run("run job.json\n", exists=lambda rid, kind: (seen.append((rid, kind)) or (rid != "Lightricks/Layout", "gone")), folder=tmp_path,
                offline=False)
    assert ("Lightricks/Layout", "model") in seen and not rec["ok"] and any("Lightricks/Layout" in p for p in rec["problems"])


def test_the_real_p12_job_files_name_the_qwen_and_ltx_weights():
    got = dict(D.all_repo_ids((P12 / "p12b.sh").read_text(encoding="utf-8"), P12))
    assert {k for k, v in got.items() if v == "model"} == {
        "Qwen/Qwen-Image-2.1", "akhaliq/Qwen-Image-2.1-Multiple-Angles-LoRA", "Lightricks/LTX-2.5",
        "Lightricks/LTX-2.5-22b-IC-LoRA-Layout-To-Render"}
    assert got["vano1919/tmr-artifacts"] == "dataset"


def _fake_hub(monkeypatch, *, gated, auth_raises):
    hub, err = types.ModuleType("huggingface_hub"), types.ModuleType("huggingface_hub.errors")

    class Gated(Exception):
        pass

    class NotFound(Exception):
        pass

    class Api:
        def __init__(self, token=None):
            self.token = token

        def repo_info(self, rid, repo_type=None):
            return types.SimpleNamespace(gated="manual" if gated else False)

        def auth_check(self, rid, repo_type=None, token=None):
            if auth_raises:
                raise Gated("403")

    hub.HfApi, err.GatedRepoError, err.RepositoryNotFoundError = Api, Gated, NotFound
    monkeypatch.setitem(sys.modules, "huggingface_hub", hub)
    monkeypatch.setitem(sys.modules, "huggingface_hub.errors", err)


def test_a_gated_repo_passes_only_when_this_token_may_download_it(monkeypatch):
    _fake_hub(monkeypatch, gated=True, auth_raises=True)
    ok, note = D.hf_exists("Lightricks/LTX-2.5", "model")
    assert ok is False and "not been granted access" in note
    _fake_hub(monkeypatch, gated=True, auth_raises=False)
    assert D.hf_exists("Lightricks/LTX-2.5", "model") == (True, "gated: access proved with this token")
    _fake_hub(monkeypatch, gated=False, auth_raises=True)                      # not gated: no auth probe is needed
    assert D.hf_exists("Qwen/Qwen-Image-2.1", "model") == (True, "")
