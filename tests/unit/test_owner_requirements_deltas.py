"""The live registry after deltas 2-6 are loaded (explainer_engine/governance/owner_requirements.json, 2026-11-20).

Reads the real registry file: the delta entries are there, none was dropped or renumbered silently, the registry passes its own schema
check, his typed words (OR-Q14, OR-G23) are verbatim with a real cmsg id, and every change that the registry CI forbids (a status flip
or a words edit resting on the decision log or a lead's reading) is only a proposal that waits for his word. $0, stdlib only."""
from __future__ import annotations

import json
import re

from _gov import ROOT
from explainer_engine.governance import owner_requirements as OR

REG = ROOT / "explainer_engine" / "governance" / "owner_requirements.json"

DELTA2 = (["OR-A%d" % i for i in range(16, 24)] + ["OR-E06"] + ["OR-I%d" % i for i in range(44, 50)] + ["OR-P10", "OR-P11", "OR-Q13", "OR-Q14"]
          + ["OR-S%d" % i for i in range(24, 29)] + ["OR-V%d" % i for i in range(63, 67)])
DELTA3 = ["OR-A24", "OR-A25", "OR-A26", "OR-A27", "OR-A28", "OR-A29", "OR-E07", "OR-I50", "OR-P12", "OR-S29", "OR-V67", "OR-V68", "OR-V70"]
DELTA4 = ["OR-I51", "OR-V71"]
PROCESS = ["OR-G21", "OR-G22", "OR-G23"]


def _all():
    data = json.loads(REG.read_text(encoding="utf-8"))
    return data, {e["id"]: e for e in data["requirements"] + data["process_requirements"]}


def test_delta_2_3_4_entries_are_in_the_registry_once():
    data, by = _all()
    ids = [e["id"] for e in data["requirements"] + data["process_requirements"]]
    assert len(ids) == len(set(ids))
    assert [i for i in DELTA2 + DELTA3 + DELTA4 + PROCESS if i not in by] == []
    assert len(DELTA2) == 28 and len(DELTA3) == 13 and len(DELTA4) == 2


def test_the_loaded_registry_passes_its_own_schema_check():
    entries, load_errs = OR.load(ROOT)
    assert load_errs == [] and entries
    assert OR.check_registry(entries, ROOT) == []
    assert OR.report(ROOT)["errors"] == []


def test_the_delta_2_process_entry_was_renumbered_because_g21_is_the_cc1_rule():
    _, by = _all()
    assert "thread" in by["OR-G21"]["words"].lower() and by["OR-G21"]["source"]["kind"] == "chat"
    assert by["OR-G22"]["source"] == {"kind": "decision_log", "ref": "D-59", "detail": by["OR-G22"]["source"]["detail"]}
    assert "OR-G21" in by["OR-G22"]["note"]
    assert not any(e["id"] == "OR-G21" for e in _all()[0]["requirements"])


def test_only_the_process_family_lives_in_process_requirements_and_binds_no_other_layer():
    data, by = _all()
    assert {"OR-G22", "OR-G23"} <= {e["id"] for e in data["process_requirements"]}
    for e in data["process_requirements"]:
        assert e.get("layers") in (None, [], ["L33"]), e["id"]


def test_his_typed_words_are_verbatim_with_the_message_id_read_back_from_the_chat():
    _, by = _all()
    q14 = by["OR-Q14"]
    assert q14["words_verbatim"] is True and q14["source"] == {"kind": "chat", "ref": "cmsg_01Hnu5zB86sjUj5GtTgaUkPWMd8fDv9ExMX3zJq6nwZXau"}
    assert "რბილი რეჟიმი" in q14["words"]
    g23 = by["OR-G23"]
    assert g23["words_verbatim"] is True and g23["kind"] == "process" and g23["status"] == "active"
    assert g23["source"] == {"kind": "chat", "ref": "cmsg_01Hnu5zB86sjUj5GtTgaUkPWCo5ZZjCRJebBnUpvGyyPUn"}
    assert g23["date"] == "2026-11-20T16:25:31Z"
    assert "ზუმინი" in g23["words"] and "ზუმაუთი" in g23["words"] and "გვერდიდან გადატარება" in g23["words"]


def test_camera_moves_entry_names_the_four_moves_and_forbids_rotation_and_stays_unmapped():
    _, by = _all()
    g23 = by["OR-G23"]
    for token in ("truck_l", "truck_r", "zoom_in", "zoom_out", "truck_zoom_in", "truck_zoom_out", "camera_move", "camera_why", "orbit"):
        assert token in g23["measures"], token
    assert g23["check"] == {"kind": "unmapped"}
    assert "proposal" in g23["note"]


def test_amendments_the_registry_allows_are_recorded_as_fields():
    _, by = _all()
    assert by["OR-Q01"]["amended_by"] == "OR-Q14" and by["OR-Q02"]["amended_by"] == "OR-Q14"
    assert by["OR-I18"]["amended_by"] == "OR-I51"
    assert by["OR-S16"]["amended_by"] == ["OR-V67", "OR-V68"]
    assert [x["ref"] for x in by["OR-C05"]["evidence_added"]] == ["D-124", "D-131"]
    assert by["OR-Q14"]["amends"] == ["OR-Q01", "OR-Q02"] and by["OR-I51"]["amends"] == ["OR-I18"]
    for aid in ("OR-Q01", "OR-Q02", "OR-I18", "OR-S16"):
        assert by[aid]["status"] == "active"


def test_changes_the_ci_forbids_stay_proposals_until_he_says_so():
    _, by = _all()
    for rid, key in (("OR-A11", "status"), ("OR-S06", "status"), ("OR-P10", "status"), ("OR-S13", "words")):
        e = by[rid]
        prop = e["proposed_amendment"]
        assert prop["applied"] is False and key in prop["change"] and "waits for his word" in prop["why_not_applied"]
        if key == "status":
            assert e.get("status") not in ("superseded", "resolved")
    assert by["OR-A11"]["status"] == "active" and "superseded_by" not in by["OR-A11"]
    assert by["OR-S13"]["words"].startswith("The mix 10/30/60 is approximate")


def test_decision_log_sources_name_only_decision_ids_and_keep_the_detail():
    _, by = _all()
    for rid in DELTA2 + DELTA3 + DELTA4 + ["OR-G22"]:
        src = by[rid]["source"]
        if src["kind"] == "decision_log":
            assert re.fullmatch(r"D-\d+(, D-\d+)*", src["ref"]), rid
    assert by["OR-A21"]["source"]["ref"] == "D-62, D-68" and "detail" in by["OR-A21"]["source"]


def test_a_delta_entry_that_arrives_superseded_names_a_live_entry_that_is_not_older():
    """OR-P12 comes in already superseded (his confirmed supersession); its successor must exist, be active and not be older."""
    _, by = _all()
    p12 = by["OR-P12"]
    assert p12["status"] == "superseded" and p12["superseded_by"] == "OR-P09" and by["OR-P09"]["status"] == "active"
    assert by["OR-P09"]["date"] >= p12["date"]


def test_the_client_candidates_of_delta_5_are_not_loaded():
    _, by = _all()
    assert not [i for i in by if i.startswith("CAND-")]


def test_the_registry_stays_unsigned():
    data, _ = _all()
    assert not any(k in data for k in ("signed", "signature", "signed_by", "owner_signature"))


def test_c04_is_resolved_per_shot_after_his_typed_confirmation():
    _, by = _all()
    c04 = by["OR-C04"]
    assert c04["status"] == "resolved" and c04["resolved_by"] == "cmsg_01Hnu5zB86sjUj5GtTgaUkPWJMmGE4iwH1R4hiLiKzwfVW"
    assert "per shot" in c04["resolution"]["answer"] and c04["resolution"]["words_verbatim"] is False
    assert "OR-C04" not in OR.report(ROOT)["open_conflicts"]
    assert OR.check_registry(OR.load(ROOT)[0], ROOT) == []
