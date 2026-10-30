import json
import shutil

import numpy as np
import pytest

from explainer_engine.audio import build_library, foley, sfx_library


def test_every_generator_is_finite_deterministic_and_not_silent():
    for name, (_tags, fn, seeds) in foley.BUILD.items():
        a, b = fn(seeds[0]), fn(seeds[0])
        assert np.array_equal(a, b), name
        assert np.isfinite(a).all() and np.max(np.abs(a)) > 0.05, name
        assert 0.05 < len(a) / foley.SR < 5, name


def test_built_library_validates_and_is_found_by_tags(tmp_path):
    n = build_library.build(tmp_path)
    assert n == sum(len(s) for _t, _f, s in foley.BUILD.values())
    assert sfx_library.validate(tmp_path) == []
    steps = sfx_library.find(tmp_path, tags=["footstep", "snow"])
    assert len(steps) == 3 and all(i["peak_dbfs"] <= -2.9 for i in steps)
    assert not sfx_library.find(tmp_path, tags=["footstep", "lava"])


def test_rebuild_is_byte_identical(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    build_library.build(a)
    build_library.build(b)
    assert (a / "manifest.json").read_bytes() == (b / "manifest.json").read_bytes()


@pytest.mark.parametrize("damage", ["edit_file", "delete_file", "extra_file", "bad_manifest", "loud"])
def test_validate_catches_damage(tmp_path, damage):
    build_library.build(tmp_path)
    first = sfx_library.load_manifest(tmp_path)["items"][0]
    path = tmp_path / first["file"]
    if damage == "edit_file":
        path.write_bytes(path.read_bytes()[:-200])
    elif damage == "delete_file":
        path.unlink()
    elif damage == "extra_file":
        shutil.copy(path, tmp_path / "foley" / "stray.wav")
    elif damage == "bad_manifest":
        manifest = json.loads((tmp_path / "manifest.json").read_text())
        del manifest["items"][0]["licence"]
        (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    else:
        samples, rate = sfx_library.read_wav(path)
        path.write_bytes(sfx_library.wav_bytes(samples / np.max(np.abs(samples)) * 0.99, rate))
        manifest = json.loads((tmp_path / "manifest.json").read_text())
        import hashlib
        manifest["items"][0]["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    assert sfx_library.validate(tmp_path)


def test_rejected_sounds_are_hidden(tmp_path):
    build_library.build(tmp_path)
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    manifest["items"][0]["review"]["human"] = "rejected"
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    gone = manifest["items"][0]["id"]
    assert gone not in {i["id"] for i in sfx_library.find(tmp_path)}
    assert gone in {i["id"] for i in sfx_library.find(tmp_path, usable=False)}


def test_elevenlabs_take_with_kind_and_credits_validates(tmp_path):
    """D-52: an ElevenLabs bed is recorded with its source kind, credits, generation id and BP-58 kind; a wrong kind fails."""
    rate = 48000
    t = np.arange(rate * 20) / rate
    bed = 0.2 * np.sin(2 * np.pi * 110 * t)
    sfx_library.add(tmp_path, name="amb_test_bed", take=1, category="foley", tags=["ambience"], samples=bed, rate=rate,
                    source={"kind": "elevenlabs", "model": "eleven_text_to_sound_v2", "prompt": "room tone",
                            "cost_credits": 99.0, "generation_id": "abc"},
                    licence={"status": "generated_terms_unverified", "note": "ElevenLabs Creator plan"})
    m = sfx_library.load_manifest(tmp_path)
    m["items"][0].update(loop=True, kind="loop", intended_seconds=20.0)
    (tmp_path / "manifest.json").write_text(json.dumps(m))
    assert sfx_library.validate(tmp_path) == []
    assert sfx_library.kind_of(m["items"][0]) == "loop"
    m["items"][0]["kind"] = "bed"
    (tmp_path / "manifest.json").write_text(json.dumps(m))
    assert sfx_library.validate(tmp_path)


def test_manifest_accepts_the_p4_optional_fields(tmp_path):
    """P4 (BP-123, BP-162): a motif owner, a beat grid and an open-model source with its admission id are optional and typed."""
    rate = 48000
    t = np.arange(rate * 20) / rate
    sfx_library.add(tmp_path, name="theme_test", take=1, category="music", tags=["music"], samples=0.2 * np.sin(2 * np.pi * 110 * t),
                    rate=rate, source={"kind": "open_model", "model": "some-open-model", "seed": 7, "admission": "adm-001"},
                    licence={"status": "generated_terms_unverified", "note": "open model"})
    m = sfx_library.load_manifest(tmp_path)
    m["items"][0].update(motif_of="napoleon", beat_grid={"bpm": 120.0, "offset_s": 0.0, "source": "declared"})
    (tmp_path / "manifest.json").write_text(json.dumps(m))
    assert sfx_library.validate(tmp_path) == []
    m["items"][0]["beat_grid"]["source"] = "guessed"
    (tmp_path / "manifest.json").write_text(json.dumps(m))
    assert sfx_library.validate(tmp_path)
