from pathlib import Path

import pytest

from explainer_engine.audio import sfx_library

ROOT = Path(__file__).resolve().parents[2] / "assets" / "audio" / "library"


def _assert_manifest_metadata():
    items = sfx_library.load_manifest(ROOT)["items"]
    assert {i["category"] for i in items} == {"vocal", "foley", "music"}
    assert all(i["review"]["human"] in ("not_listened", "approved", "rejected") for i in items)
    generated = [i for i in items if i["source"]["kind"] in ("gemini_tts", "lyria")]
    assert generated and all(i["licence"]["status"] == "generated_terms_unverified" for i in generated)
    assert all(i["source"].get("prompt") for i in generated)


def test_sound_library_manifest_metadata_is_valid_without_local_media():
    assert sfx_library.validate(ROOT, check_files=False) == []
    _assert_manifest_metadata()


@pytest.mark.media
def test_local_sound_library_audio_files_match_manifest():
    assert sfx_library.validate(ROOT) == []
