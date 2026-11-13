"""The cheapest known combination, checked before every paid run (D-133; the creator 2026-11-13 07:00 UTC, msg
cmsg_01Hnu5zB86sjUj5GtTgaUkPWK39gkFmq9K2RUuKFaBEx9g: "keep LTX as the generator; update the video generation rules; the rules
that pick the cheapest combination of every paid run must be mandatory, like a PreToolUse hook").

The rules (CH-01..CH-06) live in docs/CLOUD_RUNBOOK.md; their measured basis is ``cheapest.json`` next to this file. Two
places call them, so no path around them exists:
- the PreToolUse Bash hook (``cloud/hooks.modal_refusal`` and ``picture_refusal``) refuses the launch command;
- the worker's own entrypoints (``modal_ltx_jobs.preflight`` and ``::main``) refuse again, for a launch from code.

A rule is waived for one run only by the creator's own message (rule TOP of the project memory: he may break a rule once):
``EE_CHEAPEST_WAIVE=<cmsg id>:CH-01[,CH-03]`` on the command or in the environment, and only while the same message is recorded
for that rule (``python -m explainer_engine.governance ok cheapest_waive CH-03 <cmsg id> "<his words>"``, at most
``WAIVE_MINUTES`` old): an invented id, or a waiver left in the environment from an earlier run, waives nothing. The bake-off is
exempt: it measures the alternatives (CH-06 names its line)."""
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path

BASIS_PATH = Path(__file__).with_name("cheapest.json")
SCENES_DIR = Path(__file__).resolve().parents[1] / "training" / "pods" / "ltx" / "scenes"
WAIVE = re.compile(r"^(cmsg_\w+):((?:CH-\d\d)(?:,CH-\d\d)*)$")
MAX_SCALEDOWN_S = 5
WAIVE_MINUTES = 60   # the record of his word is fresh for one run, like protected_config


def basis(path=BASIS_PATH) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def recorded(message_id: str, rule: str, root=None, now=None) -> bool:
    """True when ``governance ok cheapest_waive <rule> <message_id>`` was recorded at most WAIVE_MINUTES ago."""
    import time
    from explainer_engine.governance import records, root_dir
    path = root_dir(root) / records.FILE
    now = time.time() if now is None else now
    for line in (path.read_text(encoding="utf-8").splitlines() if path.exists() else []):
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if (row.get("action"), row.get("target"), row.get("message_id")) == ("cheapest_waive", rule, message_id) \
                and 0 <= now - float(row.get("at", 0)) <= WAIVE_MINUTES * 60:
            return True
    return False


def waived(cmd: str = "", env=None, root=None, now=None) -> tuple[str | None, set[str]]:
    """The creator's message id and the rules it waives for this run: named on the command or in the environment AND recorded
    for that message (``recorded``). A rule named but not recorded is not waived."""
    env = os.environ if env is None else env
    m = re.search(r"\bEE_CHEAPEST_WAIVE=['\"]?(\S+?)['\"]?(?:\s|$)", cmd or "")
    raw = m.group(1) if m else str(env.get("EE_CHEAPEST_WAIVE") or "")
    w = WAIVE.match(raw)
    if not w:
        return None, set()
    return w.group(1), {r for r in w.group(2).split(",") if recorded(w.group(1), r, root, now)}


def launch_problems(launch: dict) -> list[tuple[str, str]]:
    """CH-01, CH-02 (size), CH-04 on the LTX launch file: [(rule, why)]."""
    out = []
    if (launch.get("runner") or "cli") != "inproc":
        out.append(("CH-01", "the LTX launch must run in process (`runner: inproc`): the CLI runner reloads Gemma and builds the "
                             "transformer twice for every clip (~82 s a clip, ~17 s of it denoising)"))
    nat = launch.get("native") or {}
    if nat.get("use") != [1280, 704] or nat.get("fps") != 24:
        out.append(("CH-02", f"LTX clips are made at 1280x704@24, the model's native size (native.use {nat.get('use')}, "
                             f"fps {nat.get('fps')}); 2K is the free upscale, a smaller size saved only 14-27 % and looks softer"))
    sd = launch.get("scaledown_window_s")
    if not (isinstance(sd, int) and sd <= MAX_SCALEDOWN_S):
        out.append(("CH-04", f"scaledown_window_s {sd}: a container may stay warm at most {MAX_SCALEDOWN_S} s after its job"))
    return out


def scene_for(plan_sha: str, scenes_dir=SCENES_DIR) -> Path | None:
    for p in sorted(Path(scenes_dir).glob("*.json")):
        if hashlib.sha256(p.read_bytes()).hexdigest() == plan_sha:
            return p
    return None


def spec_problems(launch: dict, spec: dict, scenes_dir=SCENES_DIR) -> list[tuple[str, str]]:
    """CH-02 (each clip's size) and CH-03 (one container per scene) on a ``::main`` job spec."""
    out = []
    nat = launch.get("native") or {}
    for s in [spec] + list(spec.get("chain") or []):
        w, h, fps = s.get("width", spec.get("width")), s.get("height", spec.get("height")), s.get("fps", spec.get("fps"))
        if [w, h] != nat.get("use") or fps != nat.get("fps"):
            out.append(("CH-02", f"{s.get('shot_id')}: {w}x{h}@{fps}, not the native {nat.get('use')}@{nat.get('fps')}"))
    scene = scene_for(str(spec.get("plan_sha256") or ""), scenes_dir)
    if scene is None:
        out.append(("CH-03", "the spec names no committed scene file (training/pods/ltx/scenes/): an LTX launch is one scene, "
                             "made by `scene_run job`, so its shots share one container and one model load"))
    else:
        want = [s["shot_id"] for s in json.loads(scene.read_text(encoding="utf-8"))["shots"]]
        have = [spec.get("shot_id")] + [c.get("shot_id") for c in spec.get("chain") or []]
        if have != want:
            out.append(("CH-03", f"the spec makes {have}, the scene {scene.name} has {want}: every shot of a scene goes in one "
                                 "container (a launch per clip pays the start-up and the model load again)"))
    return out


def picture_problems(scene: dict) -> list[tuple[str, str]]:
    """CH-05 on a scene's paid picture batch."""
    pics = scene.get("pictures") or {}
    if pics.get("tier") != "batch":
        return [("CH-05", f"paid pictures go only through the Gemini API batch tier (half price), not `{pics.get('tier')}`; "
                          "the free chat picture tool comes first (D-131)")]
    return []


def problems_text(found: list[tuple[str, str]], cmd: str = "", env=None) -> str | None:
    """The refusal for the rules not waived, or None. A waiver needs the creator's message id."""
    who, rules = waived(cmd, env)
    left = [(r, why) for r, why in found if r not in rules]
    if not left:
        return None
    return ("the cheapest-run rules (D-133, docs/CLOUD_RUNBOOK.md) refuse this paid run: "
            + "; ".join(f"{r}: {why}" for r, why in left)
            + ". Waive one rule for this run only with the creator's word: record it (`python -m explainer_engine.governance ok "
              "cheapest_waive <CH-xx> <his cmsg id> \"<his words>\"`), then EE_CHEAPEST_WAIVE=<his cmsg id>:<CH-xx>")


def ltx_refusal(entry: str, cmd: str, env=None, launch=None, scenes_dir=SCENES_DIR) -> str | None:
    """The hook's check of a paid LTX worker command (``smoke``, ``main``, ``stage``)."""
    if entry not in ("smoke", "main"):
        return None
    if launch is None:
        from explainer_engine.training.pods.ltx import modal_ltx_jobs as L
        launch = L.load_launch()
    found = launch_problems(launch)
    if entry == "main":
        m = re.search(r"--job[=\s]+['\"]?(\S+?)['\"]?(?:\s|$)", cmd)
        try:
            spec = json.loads(Path(m.group(1)).read_text(encoding="utf-8")) if m else None
        except (OSError, ValueError):
            spec = None
        if not isinstance(spec, dict) or not all(isinstance(c, dict) for c in spec.get("chain") or []):
            found.append(("CH-03", "the hook could not read the --job spec, so it cannot check the scene's one container"))
        else:
            found += spec_problems(launch, spec, scenes_dir)
    return problems_text(found, cmd, env)


PICTURES_CMD = re.compile(r"\bexplainer_engine\.training\.pods\.ltx\.scene_pictures\s+submit\s+['\"]?(\S+?)['\"]?(?:\s|$)")


def picture_refusal(cmd: str, env=None) -> str | None:
    """The hook's check of a paid picture batch (``scene_pictures submit <scene>``)."""
    m = PICTURES_CMD.search(cmd or "")
    if not m:
        return None
    try:
        scene = json.loads(Path(m.group(1)).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return problems_text([("CH-05", f"the hook could not read the scene {m.group(1)} to check the picture tier")], cmd, env)
    return problems_text(picture_problems(scene), cmd, env)


def generator_refusal(path: str, entry: str, cmd: str = "", env=None) -> str | None:
    """CH-06: the video generator is the self-hosted LTX-2.5 distilled (D-132, D-133). A paid rung of another video worker
    (the Wan worker) is refused; the bake-off, which measures the alternatives, has its own line and is not checked here."""
    if path.endswith("training/pods/wan/modal_wan_jobs.py") and entry not in ("check", "weights"):
        return problems_text([("CH-06", "the video generator is LTX-2.5 distilled on Modal (measured $0.0115 a generated second, "
                                        "with sound); Wan A14B measured $0.022 without sound")], cmd, env)
    return None
