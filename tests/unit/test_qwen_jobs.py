"""The generic Qwen jobs runner and its Modal launcher (the stone-age run sa_v3, creator 2026-11-07 14:42-15:08 UTC)."""
import sys
from pathlib import Path

import pytest

from explainer_engine.blender import stoneage_qwen_jobs as J
from explainer_engine.blender import stoneage_test_layouts as S

P15 = Path(__file__).resolve().parents[2] / "explainer_engine" / "training" / "pods" / "p15"
sys.path.insert(0, str(P15))
import modal_qwen_jobs as MJ  # noqa: E402
import qwen_jobs as QJ  # noqa: E402

INPUTS = {f"sa_{s}_flat3{x}.png": "x" for s in S.SCENES for x in ("", "_side", "_low", "_codes", "_magenta")}


def test_the_run_has_every_test_and_refs_resolve_in_order():
    doc = J.jobs(INPUTS)
    assert QJ.check_jobs(doc) == []
    w07, w10 = ({j["name"] for j in g["jobs"]} for g in doc["groups"])
    assert [g["lora_weight"] for g in doc["groups"]] == [0.7, 1.0]
    assert {f"{s}_wide_w07" for s in S.SCENES} <= w07 and {f"{s}_wide_w10" for s in S.SCENES} <= w10
    assert {f"{s}_{k}_w10" for s in S.SCENES for k in ("codes", "magenta", "plainedit")} <= w10   # 15:08-15:29 UTC: code test at LoRA 1.0
    assert {f"{s}_{a}_w07" for s in S.SCENES for a in S.ANGLES[s]} <= w07
    b = J.asset_jobs()                                            # 15:12 UTC: the Qwen-first assets run on their own, first
    assert QJ.check_jobs(b) == [] and b["out"].endswith("out_v3b") and b["inputs"] == {}
    names = {j["name"] for j in b["groups"][0]["jobs"]}
    assert {f"env_{s}_{v}" for s in S.SCENES for v in ("front", "left", "right", "back")} | {f"char_{w}" for w in J.PEOPLE} == names
    assert not any("block" in r for g in doc["groups"] for j in g["jobs"] for r in j["refs"])   # 15:05 UTC: only flat3


def test_angles_put_the_new_still_first_and_the_master_second():
    doc = J.jobs(INPUTS)
    j = next(j for j in doc["groups"][0]["jobs"] if j["name"] == "cave_side_w07")
    assert j["refs"] == ["in:sa_cave_flat3_side.png", "out:cave_wide_w07"]
    assert "Image 2 is the master scene" in j["prompt"]


def test_check_refuses_a_ref_made_later_or_an_unpinned_input_or_a_dict_prompt():
    doc = {"inputs": {}, "groups": [{"lora_weight": 0.7, "jobs": [
        {"name": "a", "prompt": "p", "refs": ["out:b"], "size": [1280, 720]},
        {"name": "b", "prompt": {"qwen": "p"}, "refs": ["in:x.png"], "size": [1280, 721]}]}]}
    bad = " ".join(QJ.check_jobs(doc))
    assert "out:b is not made before it" in bad and "not pinned" in bad and "non-empty str" in bad and "divisible" in bad


def test_code_prompt_removes_by_code_and_the_plain_twin_removes_the_same_things():
    """15:29 UTC: a code only proves itself when an edit follows it (the same removal in codes and in plain words)."""
    p = J.code_prompt("ice")
    assert "B1 is the big woolly mammoth" in p and "paint no codes or letters" in p and "Remove B2 and C2 completely" in p
    for sc, (a, b) in J.REMOVE.items():
        codes = J.CODES[sc]
        assert a in codes and b in codes and f"Remove {codes[a]} and {codes[b]}" in J.code_prompt(sc)
        plain = J.code_prompt(sc, plain=True)
        assert J._words_of(sc, a) in plain and J._words_of(sc, b) in plain and not any(c in plain for c in codes.values())


def test_launcher_timeout_from_cap_and_expected_outputs():
    assert MJ.TIMEOUT_S == MJ.cost_timeout(MJ.CAP_USD) and MJ.TIMEOUT_S * MJ.USD_PER_H / 3600 < MJ.CAP_USD
    doc = J.jobs(INPUTS)
    exp = MJ.expected_outputs(doc)
    assert len(exp) == sum(len(g["jobs"]) for g in doc["groups"]) and MJ.expected_outputs(doc, smoke=True) == ["qwen/smoke.json"]
    with pytest.raises(ValueError):
        MJ.check_timeout(MJ.TIMEOUT_S + 600, MJ.CAP_USD)


def test_magenta_variant_forbids_only_the_magenta_codes():
    """15:10 UTC: codes in one unique font and colour; the negative drops the general text ban and forbids only those."""
    doc = J.jobs(INPUTS)
    j = next(j for j in doc["groups"][1]["jobs"] if j["name"] == "cave_magenta_w10")
    assert "magenta" in j["negative"] and "text" not in j["negative"] and "lettering" not in j["negative"]
    assert "remove every magenta code" in j["prompt"]


class _FakeApi:
    def __init__(self, fail_times, headers=None):
        self.fail, self.calls, self.committed, self.headers = fail_times, 0, [], headers or {}

    def create_commit(self, repo_id, repo_type, operations, commit_message):
        self.calls += 1
        if self.calls <= self.fail:
            err = RuntimeError("429 Client Error: Too Many Requests, rate limit")
            err.response = type("R", (), {"headers": self.headers})()
            raise err
        self.committed += [o.path_in_repo for o in operations]


def test_uploader_batches_one_commit_and_never_drops_a_file_under_429(tmp_path, monkeypatch):
    """HF limit (2026-11-07 15:33 UTC): one commit per tick with all new files; 429 is retried with backoff and Retry-After; the final
    flush retries a bounded number of times; a file that could not go stays unseen and goes with the next tick."""
    import types
    hub = types.ModuleType("huggingface_hub")   # CI has no huggingface_hub: the op is a plain record
    hub.CommitOperationAdd = lambda path_in_repo, path_or_fileobj: types.SimpleNamespace(path_in_repo=path_in_repo)
    monkeypatch.setitem(sys.modules, "huggingface_hub", hub)
    (tmp_path / "qwen").mkdir()
    for n in "abc":
        (tmp_path / "qwen" / f"{n}.png").write_bytes(b"x")
    waits, seen = [], set()
    api = _FakeApi(fail_times=3, headers={"Retry-After": "40"})
    n = len([f for f in tmp_path.rglob("*") if f.is_file()])
    assert MJ._upload_batch(api, tmp_path, seen, sleep=waits.append, final=True) == n >= 3
    assert api.calls == 4 and len(api.committed) == n and waits[0] >= 40 and waits == sorted(waits)
    assert MJ._upload_batch(api, tmp_path, seen, sleep=waits.append) == 0        # nothing new: no commit at all
    assert api.calls == 4
    (tmp_path / "qwen" / "d.png").write_bytes(b"y")
    stuck = _FakeApi(fail_times=99)
    assert MJ._upload_batch(stuck, tmp_path, seen, sleep=lambda s: None) == 0 and stuck.calls == 2   # a tick tries twice, then waits for the next
    assert MJ._upload_batch(api, tmp_path, seen, sleep=waits.append) == 1 and api.committed[-1].endswith("qwen/d.png")


def test_chain_prompts_name_only_visible_codes_and_the_twin_uses_words():
    """Test D (15:29-15:31 UTC): heroes move and the view changes by code, codes stay along the chain, a last pass strips them;
    the plain twin says the same in words. A move that names a code out of frame is refused."""
    from explainer_engine.blender import stoneage_qwen_jobs as QJ
    import re
    for sc in QJ.S.SCENES:
        pr = QJ.chain_prompts(sc)
        assert re.search(r"\b[ABC]\d\b", pr["c1"]) and not re.search(r"\b[ABC]\d\b", pr["p1"] + pr["p2"])
        assert "Image 2 is the painted master" in pr["c1"] and "Keep every magenta code" in pr["c2"] and "Remove every magenta code" in pr["c3"]
    jobs = QJ.chain_jobs({"x": "0"})["groups"][0]
    assert jobs["lora_weight"] == 1.0
    by = {j["name"]: j for j in jobs["jobs"]}
    assert by["cave_d2_codes"]["refs"][0] == "out:cave_d1_codes" and by["cave_d3_strip"]["negative"] == QJ.MAGENTA_NEGATIVE
    assert "magenta" not in by["cave_d1_codes"]["negative"] and by["cave_d1_plain"]["refs"][0].startswith("in:sa_cave_flat3_side")
    QJ.MOVES["ice"] = ("A1 runs over and stands beside C1.", "B1 walks away.")
    try:
        QJ.chain_prompts("ice")
        raise AssertionError("an out-of-frame code was accepted")
    except ValueError as e:
        assert "C1" in str(e)
