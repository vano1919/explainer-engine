"""The texts of the Gemini Task route (GC-20..GC-27): spec acceptance 1-6 of A1_GEMINI_TEXTS_SPEC.md, by reading the files."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from explainer_engine import docs_lint
from explainer_engine.standards import sourced_rules

ROOT = Path(__file__).resolve().parents[2]
TEXTS = ROOT / "explainer_engine" / "gemini_task" / "texts"
MANIFEST = json.loads((TEXTS / "manifest.json").read_text(encoding="utf-8"))
PRESETS = json.loads((ROOT / "config" / "visual_style_presets.json").read_text(encoding="utf-8"))
PRESET = PRESETS["presets"][PRESETS["default_style_profile"]]

PLACEHOLDER = re.compile(r"\{\{([^{}]+)\}\}")
MESSAGE = re.compile(r"=====BEGIN MESSAGE=====\n(.*?)\n=====END MESSAGE=====", re.S)
CLAUSE = re.compile(r"=====BEGIN CLAUSE (\w+)=====\n(.*?)\n=====END CLAUSE=====", re.S)

# Fixed sentences of every PICTURES message (A1b handoff, acceptance 3).
PICTURE_SENTENCES = (
    "direct image generation tool",
    "Never draw a picture, card, placeholder or grid with Python or any other code",
    "word for word",
    "Attach the references exactly as listed",
    "No text, letters, numbers or writing-like marks in any picture",
    "If the daily limit comes, stop",
    "BATCH REPORT",
)
READ_ALOUD_WORDS = 320  # two minutes at about 160 words a minute


def _text(rel: str) -> str:
    return (TEXTS / rel).read_text(encoding="utf-8")


def _files(kind: str | None = None) -> list[dict]:
    return [f for f in MANIFEST["files"] if kind is None or f["kind"] == kind]


def _messages() -> list[tuple[str, dict, str]]:
    out = []
    for f in _files("message"):
        blocks = MESSAGE.findall(_text(f["path"]))
        assert len(blocks) == 1, f"{f['path']}: exactly one MESSAGE block"
        out.append((f["message"], f, blocks[0]))
    return out


def test_manifest_lists_every_file_and_every_file_exists() -> None:
    listed = {f["path"] for f in MANIFEST["files"]}
    on_disk = {str(p.relative_to(TEXTS)).replace("\\", "/") for sub in ("drive_pack", "messages") for p in (TEXTS / sub).glob("*.md")}
    assert listed == on_disk
    assert {f["message"] for f in _files("message")} == {
        "T0", "P0", "P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8", "P9", "P10"}


def test_every_placeholder_is_declared_with_a_source() -> None:  # acceptance 2
    declared = MANIFEST["placeholders"]
    bp = MANIFEST["bp_placeholders"]
    for f in MANIFEST["files"]:
        for raw in PLACEHOLDER.findall(_text(f["path"])):
            name = raw.split("|")[0]
            if name.startswith("bp:"):
                assert name[3:] in bp, f"{f['path']}: {{{{{raw}}}}} is not declared in bp_placeholders"
            else:
                assert name in declared, f"{f['path']}: {{{{{raw}}}}} is not declared in placeholders"
    for name, entry in declared.items():
        assert entry["source"].strip() and entry["origin"], name
    for key, entry in bp.items():
        assert entry["source"].strip(), key
        rule, _, field = key.partition(".")
        assert sourced_rules.T(rule, field) is not None  # the registry still has the number


def test_percent_placeholder_is_declared_for_the_narrator_share() -> None:
    entry = MANIFEST["bp_placeholders"]["BP-105.nominal_narrator_share"]
    assert "percent" in entry["format"]
    for rel in ("drive_pack/03_SCRIPT_RULES.md", "messages/P2_CHECK_SCRIPT.md"):
        assert "{{bp:BP-105.nominal_narrator_share}}" not in _text(rel)  # never shown as 0.7
        assert "{{bp:BP-105.nominal_narrator_share|percent}}" in _text(rel)


def test_no_never_word_in_any_message_or_clause() -> None:  # acceptance 1
    pattern = re.compile(r"\b(" + "|".join(re.escape(w) for w in PRESET["never_words"]) + r")\b", re.I)
    blocks = [(n, b) for n, _, b in _messages()]
    for f in _files("clauses"):
        blocks += [(f"clause {name}", body) for name, body in CLAUSE.findall(_text(f["path"]))]
    assert blocks
    for name, body in blocks:
        assert not pattern.findall(body), f"{name} holds a never-word"


def test_pictures_messages_carry_the_fixed_sentences_and_checks_make_no_picture() -> None:  # acceptance 3
    seen = set()
    for key, f, body in _messages():
        seen.add(f["task"])
        if f["task"] == "PICTURES":
            for sentence in PICTURE_SENTENCES:
                assert sentence in body, f"{key} misses: {sentence}"
            assert "{{era_line}}" in body, f"{key} misses the era line (GC-22)"
            assert body.startswith("PICTURES |"), key
        else:
            assert "Make no picture." in body, key
            assert body.startswith("CHECK |"), key
    assert seen == {"PICTURES", "CHECK"}


def test_cited_rule_ids_exist_in_their_canonical_documents() -> None:  # acceptance 4
    defs = docs_lint.definitions()
    other_docs = "\n".join(p.read_text(encoding="utf-8") for p in docs_lint.DOCS.glob("*.md"))
    prefixes = set(docs_lint.HOMES) | {"YT"}
    cite = re.compile(r"\b(" + "|".join(sorted(prefixes, key=len, reverse=True)) + r")-(\d{2,3})\b")
    for f in MANIFEST["files"]:
        for prefix, num in sorted(set(cite.findall(_text(f["path"])))):
            ident = f"{prefix}-{num}"
            if prefix in docs_lint.HOMES:
                assert ident in defs, f"{f['path']} cites {ident}, which no document defines"
            else:  # YT-01 is the short form of YT-01-HOOK in docs/STORY_ENGINE.md
                assert re.search(rf"\b{ident}\b", other_docs), f"{f['path']} cites {ident}"


def test_no_secret_no_keyed_link_english_only_one_topic_per_file() -> None:  # acceptance 5
    secret = re.compile(r"AIza[0-9A-Za-z_-]{20,}|sk-[A-Za-z0-9]{20,}|api[_-]?key\s*[:=]\s*\S+|resourcekey|usp=sharing|[?&]key=", re.I)
    for f in MANIFEST["files"]:
        text = _text(f["path"])
        assert not secret.search(text), f["path"]
        assert not re.search(r"[Ⴀ-ჿ]", text), f"{f['path']} holds Georgian text"
        if f["kind"] == "drive_pack":
            assert len(re.findall(r"^# ", text, flags=re.M)) == 1, f"{f['path']}: one topic, one H1"
    # every file of the pack is named by the start file
    start = _text("drive_pack/00_START_HERE.md")
    for f in _files("drive_pack")[1:]:
        assert Path(f["path"]).name in start


def test_every_message_can_be_read_aloud_in_two_minutes() -> None:  # acceptance 6
    for key, _, body in _messages():
        fixed = PLACEHOLDER.sub("", body)
        words = len(fixed.split())
        assert words <= READ_ALOUD_WORDS, f"{key}: {words} fixed words"


def test_files_and_state_page_lists_the_whole_drive_tree() -> None:
    text = _text("drive_pack/08_FILES_AND_STATE.md")
    for item in ("rules/", "claim_map.md", "short_story.md", "script.md", "shot_queue.json", "t0_probe.md",
                 "<stage>_round<n>.md", "<stage>_reply<n>.md", "batch_log.md", "redo_list.md", "refs/"):
        assert item in text, item
    # a file a message writes to Drive is on this page, under its generic name
    for key, _, body in _messages():
        for path in re.findall(r"\{\{drive_root\}\}/episodes/\{\{episode_id\}\}/([\w./{}]+)", body):
            generic = path.rstrip(".").replace("{{stage}}", "<stage>").replace("{{round}}", "<n>")
            generic = generic.replace("{{reply_round}}", "<n>").split("/")[-1]
            generic = re.sub(r"^(short_story|script|video_script)_", "<stage>_", generic)
            assert generic in text, f"{key}: {path}"


def test_preset_style_sentence_is_era_neutral_and_the_era_line_has_a_shape() -> None:  # GC-22
    sentence = PRESET["style_sentence"].lower()
    for word in ("lantern", "shaggy fur", "clay pots", "rough stone", "woven cloth"):
        assert word not in sentence, word
    shape = PRESET["era_line_shape"]
    assert "<era>" in shape and "<list>" in shape and "<materials>" in shape
    never = re.compile(r"\b(" + "|".join(re.escape(w) for w in PRESET["never_words"]) + r")\b", re.I)
    assert not never.search(shape)


def test_the_gc_rows_20_to_27_exist_and_the_pack_cites_only_those() -> None:
    defs = docs_lint.definitions()
    for n in range(20, 28):
        assert defs.get(f"GC-{n}") == ["GEMINI_CONSISTENCY_RULES.md"], n
    for f in MANIFEST["files"]:
        for n in re.findall(r"\bGC-(\d\d)\b", _text(f["path"])):
            assert f"GC-{n}" in defs, f"{f['path']}: GC-{n}"
    assert "GC-26" in _text("drive_pack/07_REVIEW_PROTOCOL.md")  # the review record is GC-26


def test_numbers_are_a_frame_within_ten_percent_not_a_template() -> None:
    """The creator, 2026-11-12 18:18 UTC: words per second is one orientation with a +-10 % band; phrase length follows the story."""
    protocol = _text("drive_pack/07_REVIEW_PROTOCOL.md")
    assert "## Numbers are a frame" in protocol and "within 10 %" in protocol
    script = _text("drive_pack/03_SCRIPT_RULES.md")
    assert "no sentence over" not in script and "within 10 % of the frame" in script
    assert MANIFEST["bp_placeholders"]["BP-06.hard_max_words"]["rule"] == "BP-06"  # the registry number stays the frame
    assert "TODO(" not in script and "TODO(" not in _text("drive_pack/05_STYLE.md")
    assert MANIFEST["open_todos"] == []
