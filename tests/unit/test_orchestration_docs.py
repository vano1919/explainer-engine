"""ICW-01 RW-10 (D-96): the orchestration rules name the Blender render pod and its frame-recovery proof."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ORCH = (ROOT / "docs" / "ORCHESTRATION.md").read_text(encoding="utf-8")


def _row(rid):
    return next(l for l in ORCH.splitlines() if l.startswith(f"| {rid} |"))


def test_or21_lists_the_blender_render_pod_script():
    assert "training/pods/blender_render.py" in _row("OR-21")


def test_or23_plan_template_carries_the_blender_fields():
    row = _row("OR-23")
    for item in ("render profile", "repeats", "resolution tier", "s/frame", "BP-175"):
        assert item in row, item


def test_or33_requires_the_frame_protocol_for_a_render_pod():
    row = _row("OR-33")
    for item in ("RENDERED", "DURABLY_STORED", "COMMITTED", "check-uploaded"):
        assert item in row, item
