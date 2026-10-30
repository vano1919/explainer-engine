"""The vault (D-73) against a fake Hugging Face: no network, nothing uploaded, nothing deleted."""
import hashlib
import json

from explainer_engine import vault as V

CFG = {"primary": "datasets/me/art", "manifest": "docs/VAULT_MANIFEST.json",
       "critical": ["lora/final/**", "data/*.txt"], "keep": ["**"]}


def blob(data):
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def remote(files, lfs=()):
    """{path: bytes} -> the tree rows Hugging Face returns (LFS files carry the sha256)."""
    rows = []
    for p, d in files.items():
        r = {"type": "file", "path": p, "size": len(d), "oid": blob(d)}
        if p in lfs:
            r["lfs"] = {"oid": hashlib.sha256(d).hexdigest(), "size": len(d)}
        rows.append(r)
    return rows


class FakeHub:
    def __init__(self, files, lfs=(), page=2):
        self.files, self.rows, self.page, self.urls = files, remote(files, lfs), page, []

    def get(self, url, tok):
        self.urls.append(url)
        start = int(url.split("&page=")[1]) if "&page=" in url else 0
        nxt = f"{url.split('&page=')[0]}&page={start + self.page}" if start + self.page < len(self.rows) else None
        return json.dumps(self.rows[start:start + self.page]).encode(), nxt

    def download(self, url, tok, target):
        path = url.split("/resolve/main/", 1)[1]
        target.write_bytes(self.files[path])


FILES = {"lora/final/w.safetensors": b"W" * 50, "lora/final/cfg.yaml": b"rank: 64\n", "lora/old/w250.safetensors": b"O" * 9,
         "data/a.txt": b"a cave", "lora/final/copy.safetensors": b"W" * 50}
LFS = {"lora/final/w.safetensors", "lora/old/w250.safetensors", "lora/final/copy.safetensors"}


def test_remote_files_follows_every_page_and_keeps_hashes():
    hub = FakeHub(FILES, LFS)
    got = V.remote_files("datasets/me/art", tok="", get=hub.get)
    assert set(got) == set(FILES) and len(hub.urls) == 3
    assert got["lora/final/w.safetensors"]["sha256"] == hashlib.sha256(b"W" * 50).hexdigest()
    assert got["data/a.txt"]["sha256"] is None and got["data/a.txt"]["blob"] == blob(b"a cave")


def test_snapshot_marks_critical_and_verify_catches_loss_and_change():
    hub = FakeHub(FILES, LFS)
    m = V.snapshot(CFG, V.remote_files("datasets/me/art", tok="", get=hub.get), now=0)
    crit = {r["path"] for r in m["files"] if r["critical"]}
    assert crit == {"lora/final/w.safetensors", "lora/final/cfg.yaml", "data/a.txt", "lora/final/copy.safetensors"}
    assert m["totals"]["files"] == 5
    with_self = dict(FILES, **{"vault/VAULT_MANIFEST_full_x.json": b"{}"})
    assert V.snapshot(CFG, V.remote_files("datasets/me/art", tok="", get=FakeHub(with_self).get), now=0)["totals"]["files"] == 5
    assert V.verify(m, V.remote_files("datasets/me/art", tok="", get=hub.get)) == []
    later = dict(FILES)
    del later["lora/old/w250.safetensors"]
    later["data/a.txt"] = b"a different cave"
    hub2 = FakeHub(later, LFS)
    bad = V.verify(m, V.remote_files("datasets/me/art", tok="", get=hub2.get))
    assert bad == ["CHANGED data/a.txt", "MISSING lora/old/w250.safetensors"]


def test_check_uploaded_passes_only_when_every_output_is_there_with_the_same_hash(tmp_path):
    out = tmp_path / "output"
    (out / "samples").mkdir(parents=True)
    (out / "w.safetensors").write_bytes(b"W" * 50)
    (out / "samples" / "s.jpg").write_bytes(b"jpg")
    on_hub = {"scene/v1/w.safetensors": b"W" * 50, "scene/v1/samples/s.jpg": b"jpg"}
    files = V.remote_files("datasets/me/art", tok="", get=FakeHub(on_hub, {"scene/v1/w.safetensors"}).get)
    assert V.check_uploaded(out, "scene/v1", files) == []
    (out / "w_000000250.safetensors").write_bytes(b"N" * 7)          # a checkpoint written after the last upload
    (out / "samples" / "s.jpg").write_bytes(b"jpg, rewritten")       # a file that changed after upload
    assert V.check_uploaded(out, "scene/v1", files) == ["DIFFERS ON HF scene/v1/samples/s.jpg",
                                                         "NOT ON HF scene/v1/w_000000250.safetensors"]


def test_check_uploaded_refuses_an_empty_output(tmp_path):
    (tmp_path / "out").mkdir()
    assert V.check_uploaded(tmp_path / "out", "x", {}) == [f"EMPTY {tmp_path / 'out'}"]


def test_pull_copies_critical_files_checks_hashes_and_reuses_twins(tmp_path):
    hub = FakeHub(FILES, LFS)
    m = V.snapshot(CFG, V.remote_files("datasets/me/art", tok="", get=hub.get), now=0)
    downloads = []

    def dl(url, tok, target):
        downloads.append(url)
        hub.download(url, tok, target)

    done, bad = V.pull(m, tmp_path / "vault", download=dl, tok="", log=lambda *_: None)
    assert (done, bad) == (4, [])
    assert (tmp_path / "vault/lora/final/w.safetensors").read_bytes() == b"W" * 50
    assert not (tmp_path / "vault/lora/old").exists()                    # not critical: only with --all
    assert len(downloads) == 3                                            # the twin copy came from disk
    downloads.clear()
    assert V.pull(m, tmp_path / "vault", download=dl, tok="", log=lambda *_: None) == (4, [])
    assert downloads == []                                                # a second run re-checks, downloads nothing


def test_pull_never_swaps_in_a_file_whose_hash_is_wrong(tmp_path):
    hub = FakeHub(FILES, LFS)
    m = V.snapshot(CFG, V.remote_files("datasets/me/art", tok="", get=hub.get), now=0)
    (tmp_path / "v/data").mkdir(parents=True)
    (tmp_path / "v/data/a.txt").write_bytes(b"the good old copy?")

    def corrupt(url, tok, target):
        target.write_bytes(b"truncated")

    done, bad = V.pull(m, tmp_path / "v", only="data/*", download=corrupt, tok="", log=lambda *_: None)
    assert bad == ["HASH data/a.txt"] and done == 0
    assert (tmp_path / "v/data/a.txt").read_bytes() == b"the good old copy?"   # nothing overwritten


def test_lint_pod_script_wants_the_vault_check_on_training_pods():
    train = "python run.py config.yaml\nhf upload me/art output scene/v1\n"
    assert V.lint_pod_script(train)[0].startswith("VT-01")
    assert V.lint_pod_script(train + "python -m explainer_engine.vault check-uploaded output --to scene/v1 || true\n")[0] \
        .startswith("VT-02")
    assert V.lint_pod_script(train + "python -m explainer_engine.vault check-uploaded output --to scene/v1\n") == []
    assert V.lint_pod_script("ffmpeg -i a.mp4 b.mp4\n") == []           # no weights, nothing to prove


def test_the_config_names_the_approved_style_lora_as_critical():
    cfg = V.config()
    assert cfg["primary"] == "datasets/vano1919/tmr-artifacts"
    assert V.is_critical("lora_plan_2026-10-22/wldnk_style_v1.0/wldnk_style_v1.0.safetensors", cfg)
    assert V.is_critical("scene_lora_2026-10-24/train_v1/output/x.safetensors", cfg)
    assert not V.is_critical("episode1/final/video.mp4", cfg)


def test_the_live_xworld_lora_and_datasets_are_critical():
    cfg = V.config()
    assert V.is_critical("lora_plan_2026-10-26/train_xworld_v2/output/xworld_v2_000003000.safetensors", cfg)
    assert V.is_critical("lora_plan_2026-10-26/train_xworld_v2/code/vault_x.py", cfg)
    assert V.is_critical("lora_plan_2026-10-26/train_xworld_v1/output/xworld_v1.safetensors", cfg)
    assert V.is_critical("lora_plan_2026-10-26/dataset_xworld_v1/manifest.json", cfg)
    assert V.is_critical("lora_plan_2026-10-26/dataset_xworld_v2/img_0001.png", cfg)
    assert V.is_critical("lora_plan_2026-10-26/caption_xworld_v1/captions_reviewed.jsonl", cfg)
