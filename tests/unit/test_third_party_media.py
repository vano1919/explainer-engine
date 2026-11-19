"""PC-10 (D-139, MA-17): the third-party media gate reads what the runner's G8 logged."""
import json

from explainer_engine.qa import publish_check as PC

LIB = {"version": 1, "items": [
    {"id": "mix", "source": {"kind": "third_party"}, "licence": {"type": "mixkit_sfx_free", "commercial_use": True, "status": "licensed"}},
    {"id": "cc0", "source": {"kind": "third_party"}, "licence": {"type": "cc0", "commercial_use": True, "status": "cc0"}},
    {"id": "bbc", "source": {"kind": "third_party"}, "licence": {"type": "bbc_remarc", "commercial_use": False, "status": "licensed"}},
    {"id": "gen", "source": {"kind": "generated"}, "licence": {"type": "generated_unverified", "commercial_use": None,
                                                              "status": "generated_terms_unverified"}},
    {"id": "song", "source": {"kind": "third_party"}, "licence": {"type": "cc_by_4", "commercial_use": True, "status": "licensed",
                                                                 "attribution_required": True, "attribution_text": "Silent Night by MacLeod"}},
]}


def _ep(tmp_path, used, *, report=True):
    ep = tmp_path / "ep"
    (ep / "audio").mkdir(parents=True)
    mp = tmp_path / "manifest.json"
    mp.write_text(json.dumps(LIB))
    if report:
        (ep / "audio" / "stems_report.json").write_text(json.dumps({"sounds_used": [{"class": "c", "id": i, "status": "library"} for i in used]}))
    return ep, mp


def _by(found, sev):
    return {f["where"] for f in found if f["severity"] == sev}


def test_a_bbc_sound_in_the_log_fails_and_mixkit_or_cc0_passes(tmp_path):
    ep, mp = _ep(tmp_path, ["mix", "cc0", "bbc"])
    found = PC.third_party_findings(ep, "", mp)
    assert _by(found, "FAIL") == {"bbc"}
    ep2, mp2 = _ep(tmp_path / "b", ["mix", "cc0"])
    assert not _by(PC.third_party_findings(ep2, "", mp2), "FAIL")


def test_a_missing_sound_log_fails(tmp_path):
    ep, mp = _ep(tmp_path, [], report=False)
    assert _by(PC.third_party_findings(ep, "", mp), "FAIL") == {"audio/stems_report.json"}


def test_unverified_generated_audio_and_a_missing_cc_by_credit_are_review_and_a_known_credit_passes(tmp_path):
    ep, mp = _ep(tmp_path, ["gen", "song", "ghost"])
    review = _by(PC.third_party_findings(ep, "no credit here", mp), "REVIEW")
    assert {"gen", "song", "ghost"} <= review
    assert "song" not in _by(PC.third_party_findings(ep, "Music: Silent Night by MacLeod", mp), "REVIEW")


def test_media_classes_without_a_provenance_record_are_listed_by_name_never_passed(tmp_path):
    ep, mp = _ep(tmp_path, ["mix"])
    PC.third_party_findings(ep, "", mp)
    rec = json.loads((ep / "qa" / "third_party_media.json").read_text())
    assert set(rec["classes_without_record"]) == set(PC.UNRECORDED_CLASSES)
    assert all(i["status"] == "REVIEW" for i in rec["items"] if i["id"] is None)
    assert rec["unresolved_reviews"]["count"] == len(PC.UNRECORDED_CLASSES)
    assert {i["id"]: i["status"] for i in rec["items"] if i["id"]} == {"mix": "PASS"}


def test_a_do_not_monetise_marker_fails_and_check_wires_pc10(tmp_path):
    ep, mp = _ep(tmp_path, ["mix"])
    (ep / "render" / "pass1").mkdir(parents=True)
    (ep / "render" / "pass1" / "DO_NOT_MONETISE_CONTAINS_BBC_REMARC.txt").write_text("x")
    assert "render/pass1/DO_NOT_MONETISE_CONTAINS_BBC_REMARC.txt" in _by(PC.third_party_findings(ep, "", mp), "FAIL")
    import inspect
    assert "third_party_findings" in inspect.getsource(PC.check)
