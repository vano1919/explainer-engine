import hashlib
from pathlib import Path

import pytest

from explainer_engine.audio import build_library, sfx_library

ROOT = Path(__file__).resolve().parents[2] / "assets" / "audio" / "library"
MEDIA_MISSING = any(not (ROOT / i["file"]).exists() for i in sfx_library.load_manifest(ROOT)["items"])


def test_committed_manifest_is_valid_and_declares_licence_and_review():
    assert sfx_library.validate(ROOT, check_files=False) == []
    items = sfx_library.load_manifest(ROOT)["items"]
    assert {i["category"] for i in items} == {"vocal", "foley", "music"}
    assert all(i["review"]["human"] in ("not_listened", "approved", "rejected") for i in items)
    generated = [i for i in items if i["source"]["kind"] in ("gemini_tts", "lyria")]
    assert generated and all(i["licence"]["status"] == "generated_terms_unverified" for i in generated)
    assert all(i["source"].get("prompt") for i in generated)


def test_procedural_sounds_rebuild_byte_identical(tmp_path):
    """The free part of the library is not in git but is reproducible: a rebuild gives the registered bytes."""
    build_library.build(tmp_path)
    want = {i["file"]: i["sha256"] for i in sfx_library.load_manifest(ROOT)["items"] if i["source"]["kind"] == "procedural"}
    assert want
    for rel, sha in want.items():
        assert hashlib.sha256((tmp_path / rel).read_bytes()).hexdigest() == sha, rel


@pytest.mark.media
@pytest.mark.skipif(MEDIA_MISSING, reason="library WAVs are not in git (paid Gemini TTS / Lyria takes): run where the media is")
def test_committed_library_files_are_present_and_unchanged():
    assert sfx_library.validate(ROOT) == []
