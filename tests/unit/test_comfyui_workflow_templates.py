"""Unit tests for TODO-10: ComfyUI API workflow JSON templates validation."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS_DIR = ROOT / "workflows" / "comfyui"

EXPECTED_TEMPLATES = {
    "qwen_keyframe_multiangle.json": {"QwenMultiangleCameraNode", "TextEncodeQwenImageEditPlus", "KSampler"},
    "wan22_fun_inp_flf2v.json": {"WanImageToVideo", "WanFunInpaintToVideo", "KSampler", "SaveVideo"},
    "wan22_fun_control.json": {"Wan22FunControlToVideo", "WanCameraEmbedding", "KSampler", "SaveVideo"},
    "depthflow_25d_motion.json": {"DepthAnythingV2Preprocessor", "DepthflowPresetDolly", "DepthflowScene", "SaveVideo"},
}


def test_all_four_comfyui_workflow_templates_exist_and_validate_graph_links() -> None:
    for filename, expected_classes in EXPECTED_TEMPLATES.items():
        path = WORKFLOWS_DIR / filename
        assert path.exists(), f"Missing ComfyUI workflow template: {path}"
        doc = json.loads(path.read_text(encoding="utf-8"))
        node_ids = {k for k in doc if k != "_meta"}
        found_classes = set()

        for nid in node_ids:
            node = doc[nid]
            assert "class_type" in node and "inputs" in node, f"{filename} node {nid} missing class_type/inputs"
            found_classes.add(node["class_type"])
            for inp_name, inp_val in node["inputs"].items():
                if isinstance(inp_val, list):
                    assert len(inp_val) == 2, f"{filename} node {nid}.{inp_name} link must be [node_id, output_idx]"
                    src_node_id, out_idx = inp_val
                    assert str(src_node_id) in node_ids, (
                        f"{filename} node {nid}.{inp_name} references non-existent node {src_node_id!r}"
                    )
                    assert isinstance(out_idx, int) and out_idx >= 0

        assert expected_classes <= found_classes, f"{filename} missing expected classes: {expected_classes - found_classes}"
