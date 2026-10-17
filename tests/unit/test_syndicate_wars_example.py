"""The committed Syndicate Wars episode files (examples/syndicate_wars_ep1) keep passing the gates that need no media."""

from __future__ import annotations

from pathlib import Path

from explainer_engine.production import script as S
from explainer_engine.production import validate as V
from explainer_engine.research import hypotheses as H
from explainer_engine.rights import ip_check
from explainer_engine.standards import rulebook as R

EX = Path(__file__).resolve().parents[2] / "examples" / "syndicate_wars_ep1"


def test_script_has_no_fail_apart_from_missing_pictures():
    doc = S.load(EX / "production_script.json")
    assert S.schema_errors(doc) == []
    fails = [f for f in V.check_script(doc) if f["severity"] == "FAIL"]
    # the painted pictures are not committed (media); everything else must be clean
    assert all(f["rule"] == "PV-05" and "file" in f["detail"] for f in fails), fails[:3]


def test_every_spoken_number_has_a_claim_and_ratings_are_labelled_opinion():
    import json
    doc = S.load(EX / "production_script.json")
    claims = {c["id"]: c for c in json.loads((EX / "claim_map.json").read_text(encoding="utf-8"))["claims"]}
    for seg in doc["segments"]:
        for line in seg["lines"]:
            for cid in line.get("claims", []):
                assert cid in claims, (seg["id"], cid)
            if any(ch.isdigit() for ch in line["text"]):
                assert line.get("claims"), (seg["id"], line["text"])
    for cid in ("C-44", "C-45", "C-46", "C-47"):
        assert claims[cid]["label"] == "speculation" and "opinion" in claims[cid]["text"].lower()


def test_rulebook_rights_and_hypotheses_pass():
    rules = R.load(EX / "episode_rules.json")
    assert not [f for f in R.check(rules, "final") if f["severity"] == "FAIL"]
    assert not [f for f in ip_check.check(R.load(EX / "rights_manifest.json")) if f["verdict"] == "FAIL"]
    assert not [f for f in H.check(R.load(EX / "story_hypotheses.json")) if f["severity"] == "FAIL"]


def test_no_prompt_names_a_franchise_character_or_actor():
    import re
    doc = S.load(EX / "production_script.json")
    bad = re.compile(r"gta|grand theft|rockstar|take-two|godfather|corleone|vito|peaky|shelby|brando|murphy|yakuza|sega|netflix", re.I)
    pics, _ = S.pictures(doc)
    for pid, p in pics.items():
        assert not bad.search(p.get("prompt", "")), pid
