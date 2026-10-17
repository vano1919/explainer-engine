from pathlib import Path

from explainer_engine.audio import sfx_library

ROOT = Path(__file__).resolve().parents[2] / "assets" / "audio" / "library"


def test_committed_library_is_valid_and_declares_licence_and_review():
    assert sfx_library.validate(ROOT) == []
    items = sfx_library.load_manifest(ROOT)["items"]
    assert {i["category"] for i in items} == {"vocal", "foley", "music"}
    # a machine review is never a human approval
    assert all(i["review"]["human"] in ("not_listened", "approved", "rejected") for i in items)
    generated = [i for i in items if i["source"]["kind"] in ("gemini_tts", "lyria")]
    assert generated and all(i["licence"]["status"] == "generated_terms_unverified" for i in generated)
    assert all(i["source"].get("prompt") for i in generated)
