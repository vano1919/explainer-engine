"""PreToolUse hook for the ElevenLabs connector (OR-11, D-46): a paid generation runs only through the rulebook gate.

Wired in ``.claude/settings.json`` (matcher ``mcp__ElevenLabs__creative_.*``). Claude Code passes the call as JSON on stdin
(``tool_name``, ``tool_input``); the hook answers ``permissionDecision: deny`` with a reason, or nothing (normal flow).

* Pictures and video never go through ElevenLabs: they are painted by Gemini on the batch tier (``production/paint.py``).
* ``estimate_only`` calls and read-only tools always pass.
* A paid audio generation (speech, sound effect, music) needs ``generations_count`` 1 (the connector's default is 4, four
  times the credits; EL-10) and the active episode's rulebook ``paid_assets`` checkpoint to pass.
* The active episode is named in ``.claude/active_episode.json``: ``{"episode": "<folder with episode_rules.json>"}``. An
  ``"override": "<the creator's reason>"`` lets a paid call through without the gate (voice auditions before a rulebook
  exists); it never lifts the picture rule or the one-take rule, and every override is logged to ``jobs/gate_overrides.jsonl``.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

PICTURE_TOOLS = {"creative_generate_image", "creative_generate_video", "creative_edit_image"}
PICTURE_NODES = {"image-generation", "video-generation", "image-transform", "avatar", "dubbing-video"}
PAID_TOOLS = {"creative_generate_speech", "creative_generate_in_flow", "creative_run_flow_nodes", "creative_design_voice"}
ONE_TAKE = {"creative_generate_speech", "creative_generate_in_flow"}


def decide(tool_name: str, tool_input: dict, root: Path) -> str | None:
    """The reason to deny the call, or None to let it through."""
    tool = tool_name.split("__")[-1]
    node = tool_input.get("node_type", "")
    if tool in PICTURE_TOOLS or node in PICTURE_NODES:
        return ("D-46: pictures and video are painted by Gemini on the batch tier (python -m explainer_engine.production.paint), "
                "never through ElevenLabs")
    if tool not in PAID_TOOLS or tool_input.get("estimate_only"):
        return None
    if tool in ONE_TAKE and tool_input.get("generations_count") != 1:
        return "EL-10: pass generations_count 1 (the default 4 charges four takes); estimate_only first"
    cfg_path = root / ".claude" / "active_episode.json"
    if not cfg_path.exists():
        return ("OR-11: no active episode: write .claude/active_episode.json {\"episode\": \"<folder>\"} so the rulebook's "
                "paid_assets gate can run (or an \"override\" with the creator's reason)")
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    if (cfg.get("override") or "").strip():
        log = root / "jobs" / "gate_overrides.jsonl"
        log.parent.mkdir(parents=True, exist_ok=True)
        with log.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"time": time.strftime("%Y-%m-%dT%H:%M:%S"), "tool": tool_name,
                                "override": cfg["override"], "episode": cfg.get("episode")}) + "\n")
        return None
    folder = root / cfg.get("episode", "")
    rules = folder / "episode_rules.json"
    if not rules.exists():
        return f"OR-10: {rules} does not exist"
    from explainer_engine.standards import rulebook as R
    fails = [f for f in R.gate(rules, "paid_assets", folder / "production_script.json") if f["severity"] == "FAIL"]
    if fails:
        return "OR-11: the rulebook's paid_assets checkpoint fails: " + "; ".join(
            f"{f['rule']} {f['where']}: {f['detail']}" for f in fails[:3]) + (f" (+{len(fails) - 3} more)" if len(fails) > 3 else "")
    return None


def main() -> int:
    event = json.loads(sys.stdin.read() or "{}")
    root = Path(event.get("cwd") or ".")
    while not (root / ".claude").is_dir() and root.parent != root:
        root = root.parent
    try:
        reason = decide(event.get("tool_name", ""), event.get("tool_input") or {}, root)
    except Exception as exc:  # a broken rulebook must stop money, not wave it through
        reason = f"the gate could not run ({type(exc).__name__}: {exc}); fix it before a paid call"
    if reason:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                                 "permissionDecisionReason": reason}}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
