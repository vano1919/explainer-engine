"""P2 judge worker: the core and the container body rehearsed on CPU with a fake judge and a fake HF (feedback-rehearse-container-body):
normal run, deadline in the middle, a second attempt, a model that does not fit, storage down. Plus the launch file's own arithmetic."""
from __future__ import annotations

import hashlib
import io
import json
import tarfile
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image

from explainer_engine.training.pods.judge import compare, judge_core as J
from explainer_engine.training.pods.judge import modal_judge_jobs as M

TH = {"review_at": 0.3, "retry_at": 0.7}


def _png(path: Path, color=(120, 80, 40), size=(64, 48)):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, color).save(path)


def make_batch(root: Path, n=3, examples=3) -> dict:
    for i in range(examples):
        _png(root / f"examples/E{i}.png")
    _png(root / "anchors/A1.png")
    frames = []
    for i in range(n):
        _png(root / f"frames/F{i:02d}.png", (i * 40 % 255, 10, 10))
        frames.append({"id": f"F{i:02d}", "file": f"frames/F{i:02d}.png", "anchor": "anchors/A1.png"})
    return {"schema": J.SCHEMA_BATCH, "prefix": "tests/P2/x", "frames": frames,
            "style_examples": [{"file": f"examples/E{i}.png"} for i in range(examples)]}


class FakeJudge:
    """Answers YES with probability 0.9 for frame F01 on the hand question, else NO 0.05; counts asks."""

    def __init__(self, log):
        self.log = log

    def ask(self, q, examples, anchor, frame):
        self.log.append((q["ask"][:20], len(examples), anchor is not None))
        hit = "DEFORMED HAND" in q["ask"] and frame.getpixel((0, 0))[0] == 40
        return ("YES\nthe hand has six fingers" if hit else "NO\nlooks fine"), (0.9 if hit else 0.05)


# --- prompts, batch, parsing --------------------------------------------------------------------------------------------------

def test_prompts_are_files_hashed_one_per_defect():
    p = J.load_prompts()
    assert set(p["defects"]) == set(J.DEFECTS) and len(p["prompts_sha"]) == 64
    assert len(p["sha256"]) == 5 and "ANCHOR" in p["defects"]["identity_mismatch"]
    assert all("ANCHOR" not in v for k, v in p["defects"].items() if k != "identity_mismatch")


def test_batch_needs_three_to_five_creator_chosen_examples(tmp_path):
    assert J.batch_problems(make_batch(tmp_path, examples=3), tmp_path) == []
    assert any("style examples" in b for b in J.batch_problems(make_batch(tmp_path, examples=2), tmp_path))
    b = make_batch(tmp_path)
    b["frames"][0]["anchor"] = None
    assert any("anchor" in x for x in J.batch_problems(b, tmp_path))


def test_parse_answer():
    assert J.parse_answer("YES\nsix fingers") == (True, "six fingers")
    assert J.parse_answer("no, fine")[0] is False
    assert J.parse_answer("Maybe")[0] is None


def test_verdict_uses_the_top_probability():
    assert J.verdict({"a": 0.1, "b": 0.2}, 0.3, 0.7) == "PASS"
    assert J.verdict({"a": 0.5}, 0.3, 0.7) == "REVIEW"
    assert J.verdict({"a": 0.1, "b": 0.8}, 0.3, 0.7) == "RETRY"


# --- run ----------------------------------------------------------------------------------------------------------------------

def _models():
    return [{"key": "m_small", "path": "p1"}, {"key": "m_big", "path": "p2"}]


def test_run_saves_every_step_and_writes_atomic_files(tmp_path):
    root, out, log, steps = tmp_path / "in", tmp_path / "out", [], []
    batch = make_batch(root)
    res = J.run(batch, root, out, _models(), lambda m: FakeJudge(log), th=TH, on_step=lambda p, i: steps.append((p.exists(), i["kind"])),
                upload_every=2)
    assert res["end"] == "DONE" and set(res["models"]) == {"m_small", "m_big"}
    assert (out / "m_big" / "F02.json").is_file() and (out / "results.json").is_file()
    assert all(exists for exists, _ in steps)                          # a step is reported only after its file exists
    assert [k for _, k in steps].count("frame") == 6 and steps[-1][1] == "final"
    rec = res["models"]["m_small"]["frames"]["F01"]
    assert rec["verdict"] == "RETRY" and rec["defects"]["deformed_hand"]["flag"] is True
    assert res["models"]["m_small"]["frames"]["F00"]["verdict"] == "PASS"
    assert len(log) == 2 * 3 * 4 and all(n == 3 for _, n, _ in log)    # 2 models x 3 frames x 4 questions, 3 examples each
    assert sum(1 for _, _, a in log if a) == 2 * 3                      # the anchor goes to the identity question only
    assert not list(out.rglob(".*.tmp"))


def test_deadline_in_the_middle_stops_cleanly_and_keeps_what_exists(tmp_path):
    root, out, log = tmp_path / "in", tmp_path / "out", []
    batch = make_batch(root, n=4)
    clock = iter(range(100))
    res = J.run(batch, root, out, _models(), lambda m: FakeJudge(log), th=TH, deadline=2.5, now=lambda: next(clock))
    assert res["end"] == "CAPPED" and res["models"]["m_small"]["state"] == "CAPPED"
    assert "m_big" not in res["models"]                                  # no second model after a stop
    done = sorted(p.name for p in (out / "m_small").glob("F*.json"))
    assert done == ["F00.json", "F01.json", "F02.json"]                  # the deadline (2.5) lets three asks through, then stops
    assert (out / "results.json").is_file()


def test_a_model_that_does_not_fit_ends_the_run_without_retry(tmp_path):
    root, out, log, loads = tmp_path / "in", tmp_path / "out", [], []

    def load(m):
        loads.append(m["key"])
        if m["key"] == "m_big":
            raise RuntimeError("CUDA out of memory")
        return FakeJudge(log)

    res = J.run(make_batch(root), root, out, _models(), load, th=TH, vram=lambda: {"max_allocated_gib": 79.1})
    assert res["end"] == "MODEL_FAILED" and loads == ["m_small", "m_big"]
    big = res["models"]["m_big"]
    assert big["state"] == "LOAD_FAILED" and "out of memory" in big["error"] and big["vram"]["max_allocated_gib"] == 79.1
    assert (out / "m_big" / "model.json").is_file() and (out / "m_small" / "F00.json").is_file()


def test_second_attempt_of_a_run_key_is_refused(tmp_path):
    commits = []
    assert J.claim_attempt(tmp_path, "run1_main", commit=lambda: commits.append(1)) is None
    err = J.claim_attempt(tmp_path, "run1_main")
    assert err and "second attempt" in err and commits == [1]
    assert J.claim_attempt(tmp_path, "run1_smoke") is None               # another kind of the same run is its own key


# --- the container body -------------------------------------------------------------------------------------------------------

class FakeApi:
    def __init__(self, down=False):
        self.files, self.commits, self.down = {}, [], down

    def create_commit(self, repo_id, repo_type, operations, commit_message):
        if self.down:
            raise ConnectionError("hub unreachable")
        self.commits.append(len(operations))
        for op in operations:
            data = Path(op.path_or_fileobj).read_bytes()
            self.files[op.path_in_repo] = hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()

    def get_paths_info(self, repo, paths, repo_type):
        return [SimpleNamespace(blob_id=self.files[p]) for p in paths if p in self.files]


@pytest.fixture
def world(tmp_path):
    launch = json.loads(json.dumps(M.LAUNCH))
    vol = tmp_path / "vol"
    for k, m in launch["models"].items():             # tiny staged "weights": same file names, pinned sizes and ids replaced
        m["files"] = {}
        root = vol / m["dir"]
        root.mkdir(parents=True)
        (root / "config.json").write_text(k)
        m["files"]["config.json"] = {"size": len(k), "id": hashlib.sha1(b"blob %d\0" % len(k) + k.encode()).hexdigest(), "kind": "git_blob"}
    src = tmp_path / "src"
    batch = make_batch(src)
    (src / "batch.json").write_text(json.dumps(batch))
    tar = tmp_path / "b.tar.gz"
    with tarfile.open(tar, "w:gz") as tf:
        for p in src.rglob("*"):
            tf.add(p, p.relative_to(src))
    sha = M._sha(tar)
    spec = {"kind": "main", "run_id": "abc_def", "batch_path": f"code/judge/batch-{sha}.tar.gz", "batch_sha": sha}
    return SimpleNamespace(launch=launch, vol=vol, spec=spec, tar=tar, work=tmp_path / "work", log=[])


def _body(w, api, spec=None, **kw):
    return M.body(spec or w.spec, w.launch, timeout_s=600, vol_root=w.vol, work=w.work, api=api, download=lambda name, dest: w.tar,
                  load_judge=lambda m: FakeJudge(w.log), vram=lambda: {"max_allocated_gib": 1.0}, free=lambda j: None,
                  baked=w.vol / "none.json", op_cls=SimpleNamespace, **kw)


def test_body_normal_run_uploads_and_reads_back(world):
    api = FakeApi()
    res = _body(world, api)
    assert res["state"] == "DONE" and set(res["models"]) == {"qwen3vl_8b", "qwen3vl_30b_a3b"}
    prefix = f"{world.launch['hf_out']}/abc_def/main/"
    assert prefix + "results.json" in api.files and prefix + "qwen3vl_30b_a3b/F02.json" in api.files
    assert prefix + "modal_record.json" in api.files
    assert res["models"]["qwen3vl_8b"]["vram_peak"]["max_allocated_gib"] == 1.0


def test_body_smoke_is_one_frame_one_model(world):
    res = _body(world, FakeApi(), dict(world.spec, kind="smoke"))
    assert res["state"] == "DONE" and list(res["models"]) == ["qwen3vl_8b"] and len(world.log) == 4


def test_body_second_attempt_is_refused_and_pays_nothing(world):
    assert _body(world, FakeApi())["state"] == "DONE"
    n = len(world.log)
    again = _body(world, FakeApi())
    assert again["state"] == "FAILED" and "second attempt" in again["error"] and len(world.log) == n


def test_body_storage_down_is_a_failure_with_the_files_still_on_disk(world):
    res = _body(world, FakeApi(down=True))
    assert res["state"] == "FAILED" and any("final upload failed" in p for p in res["problems"])
    assert (world.work / "out" / "results.json").is_file()


def test_body_refuses_unstaged_weights_and_a_wrong_batch_hash(world):
    (world.vol / world.launch["models"]["qwen3vl_8b"]["dir"] / "config.json").unlink()
    assert "not staged" in _body(world, FakeApi())["error"]
    (world.vol / world.launch["models"]["qwen3vl_8b"]["dir"] / "config.json").write_text("qwen3vl_8b")
    bad = _body(world, FakeApi(), dict(world.spec, batch_sha="0" * 64, run_id="other"))
    assert bad["state"] == "FAILED" and "nothing was run" in bad["error"]


def test_body_deadline_gives_capped_failed_state_with_partial_upload(world):
    clock = iter(range(0, 100000, 200))
    api = FakeApi()
    res = _body(world, api, now=lambda: next(clock))
    assert res["state"] == "FAILED" and res["end"] == "CAPPED"
    assert any(k.endswith("modal_record.json") for k in api.files)


# --- the launch file's own numbers --------------------------------------------------------------------------------------------

def test_launch_file_is_consistent_with_the_price_table_and_the_80_percent_rule():
    L = M.LAUNCH
    assert M.launch_problems(L) == []
    c = L["caps"]
    assert c["smoke_usd"] + c["run_usd"] <= 0.8 * c["ledger_line_usd"] + 1e-9 and c["ledger_line_usd"] == 1.2
    t_smoke, t_run = M.timeouts(L)
    assert (t_smoke + c["cold_start_s"]) * M.stated_rate(L) / 3600 <= c["smoke_usd"]
    assert (t_run + c["cold_start_s"]) * M.stated_rate(L) / 3600 <= c["run_usd"]
    assert L["gpu"] == "A100-80GB" and L["scaledown_window_s"] <= 5


def test_every_model_is_pinned_by_full_revision_and_every_file_has_a_hash():
    for k, m in M.LAUNCH["models"].items():
        assert len(m["revision"]) == 40
        assert all(len(v["id"]) in (40, 64) and v["size"] > 0 for v in m["files"].values())
        assert any(f.endswith(".safetensors") for f in m["files"]) and "config.json" in m["files"]


def test_30b_weights_fit_a100_80gb_by_estimate():
    est = M.LAUNCH["vram_estimate_gib"]["qwen3vl_30b_a3b"]["weights"]
    assert 50 < est < 80 * 0.8      # under 80 % of the card before activations; measured at L3/L4, this is the estimate


def test_the_launch_is_not_the_protected_ltx_launch():
    assert M.LAUNCH_PATH.name == "launch_a100.json" and M.LAUNCH_PATH.parent.name == "judge"


# --- compare ------------------------------------------------------------------------------------------------------------------

def test_compare_table_counts_against_the_owners_labels(tmp_path):
    root, out = tmp_path / "in", tmp_path / "out"
    res = J.run(make_batch(root), root, out, _models(), lambda m: FakeJudge([]), th=TH)
    t = compare.table(res, {"F00": "PASS", "F01": "FAIL", "F02": "PASS"})
    hand = t["models"]["m_small"]["defects"]["deformed_hand"]
    assert hand["flagged_on_owner_FAIL"] == "1/1" and hand["flagged_on_owner_PASS"] == "0/2"
    assert t["agreement"]["deformed_hand"]["same_flag"] == "3/3"
    assert "deformed_hand" in compare.markdown(t)


def test_pack_batch_is_reproducible_and_sha_named(tmp_path):
    from explainer_engine.training.pods.judge import pack_batch
    src = tmp_path / "src"
    batch = make_batch(src)
    (src / "batch.json").write_text(json.dumps(batch))
    a, sha = pack_batch.pack(src, tmp_path / "o1")
    b, sha2 = pack_batch.pack(src, tmp_path / "o2")
    assert sha == sha2 and a.name == f"batch-{sha}.tar.gz" and M._sha(a) == sha
    (src / "batch.json").write_text(json.dumps(dict(batch, style_examples=batch["style_examples"][:1])))
    with pytest.raises(SystemExit):
        pack_batch.pack(src, tmp_path / "o3")
