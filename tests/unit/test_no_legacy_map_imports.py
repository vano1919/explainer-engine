"""PY-02: no new production use of the legacy map renderer ``explainer_engine/maps/render.py``.

The allowlist is the set of files that import it on the base (7fb0c725). A file outside the list that imports it fails
this test. Adding a file to the list is an owner decision (the handbook's R9 row), not a code fix. Gap recorded, not
changed here: ``edit/archetypes.json`` names ``explainer_engine.maps.render`` as the renderer of the map archetypes, a string
lookup no import scan can see; routing is not changed by this test (PY-02 acceptance: record the gap, ask the owner)."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LEGACY = re.compile(
    r"explainer_engine\.maps\.render\b|explainer_engine\.maps import render\b|from explainer_engine\.maps import .*\brender\b"
)
ALLOWED = {
    "explainer_engine/edit/visual_compensator.py",
    "explainer_engine/maps/laws.py",
    "explainer_engine/overlay/spec.py",
    "explainer_engine/production/map_clip.py",
    "tests/unit/test_bridge_caller.py",
    "tests/unit/test_episode_first_isolation_and_v4_3_fixes.py",
    "tests/unit/test_maps.py",
    "tests/unit/test_preset_render_switch.py",
    "tests/unit/test_sound_cue_policy.py",
}


def find_importers(root: Path) -> set[str]:
    found = set()
    for folder in ("explainer_engine", "tests"):
        for path in (root / folder).rglob("*.py"):
            rel = path.relative_to(root).as_posix()
            if rel in ("explainer_engine/maps/render.py", "tests/unit/test_no_legacy_map_imports.py"):
                continue
            if LEGACY.search(path.read_text(encoding="utf-8", errors="replace")):
                found.add(rel)
    return found


def test_no_new_legacy_map_importer():
    new = find_importers(ROOT) - ALLOWED
    assert not new, f"new importer(s) of the legacy maps renderer, not on the allowlist: {sorted(new)}"


def test_allowlist_has_no_stale_entries():
    gone = ALLOWED - find_importers(ROOT)
    assert not gone, f"allowlist entries that no longer import the renderer (remove them): {sorted(gone)}"


def test_scanner_flags_a_new_importer(tmp_path):
    # the failure demonstration: a scratch file that imports the legacy renderer is reported
    (tmp_path / "explainer_engine" / "production").mkdir(parents=True)
    (tmp_path / "explainer_engine" / "production" / "rogue.py").write_text(
        "from explainer_engine.maps import render as R\n", encoding="utf-8")
    assert find_importers(tmp_path) == {"explainer_engine/production/rogue.py"}
