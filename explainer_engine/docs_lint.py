
"""Documentation lint (decision D-23): one canonical home per ID, links resolve, fixtures parse. stdlib only.

Run: ``python -m explainer_engine.docs_lint`` (exit 1 on findings). ``docs/PLAN_2026-10-15.md`` is history: it is
checked for nothing and cited by nothing as a definition.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
HISTORY = {"PLAN_2026-10-15.md"}
# ID prefix -> the one document that defines it (as table rows starting with "| ID |")
HOMES = {
    "D": "DECISIONS_AND_OPEN_QUESTIONS.md",
    "SE": "MARKET_RESEARCH.md",
    "V": "MARKET_RESEARCH.md",
    "P": "VIDEO_PARAMETER_SPEC.md",
    "R": "RISK_REGISTER.md",
    "Q": "QA_SPECIFICATION.md",
    "RR": "RIGHTS_AND_FAIR_USE.md",
    "UR": "UNIVERSAL_RULE_BASE.md",
    # the rule families added since D-23 (audit 2026-10-19 H4: branches reused PV-32..36 and OR-10 for different rules)
    "PV": "PRODUCTION_SCRIPT.md",
    "PP": "PRODUCTION_SCRIPT.md",
    "CS": "PRODUCTION_SCRIPT.md",  # scene continuity of the painted pictures (D-69)
    "PC": "QA_SPECIFICATION.md",
    "ED": "EDITING.md",
    "OR": "ORCHESTRATION.md",
    "UD": "DECISIONS_AND_OPEN_QUESTIONS.md",  # the Blueprint gates that wait for the creator (OR-28)
    "SR": "ORCHESTRATION.md",
    "SH": "ORCHESTRATION.md",
    "ST": "STORY_ENGINE.md",
    "SS": "STORY_ENGINE.md",
    "DW": "STORY_ENGINE.md",
    "MO": "STORY_ENGINE.md",
    "AL": "STORY_ENGINE.md",
    "PF": "STORY_ENGINE.md",
    "VC": "STORY_ENGINE.md",
    "VB": "STORY_ENGINE.md",
    "ES": "EPISODE_STANDARDS.md",
    "TN": "THUMBNAIL_RULES.md",
    "BP": "SOURCED_RULES.md",
    "ZI": "SCRIPT_ENGINE.md",  # the script engine v1: zero improvisation (2026-10-24)
    "KP": "SHOT_PROMPTS.md",  # prompts of animated shots: keyframe, next pose, cut, video (2026-10-24)
    "KG": "KEYFRAME_GATE.md",
    "LY": "KEYFRAME_GATE.md",  # shot layout from real sizes and the camera (2026-10-24)  # keyframe gate: picture checks, cause log, LoRA/base pairing (2026-10-24)
    "AC": "ASSET_COMPOSE.md",  # shots composed from reusable assets (2026-10-25)
    "LV": "SCENE_REUSE_RULES.md",  # one place, one picture (D-120, 2026-11-07)
    "RF": "SCENE_REUSE_RULES.md",
    "HI": "SCENE_REUSE_RULES.md",
    "DL": "SCENE_REUSE_RULES.md",
    "AS": "SCENE_REUSE_RULES.md",  # cut assembly gate (D-121, 2026-11-07)
    "LX": "SCENE_REUSE_RULES.md",  # LTX clips in the edit (systemic/next-video 217737d, merged 2026-11-12)
    "CT": "SHOT_CONTINUITY.md",  # continuity cards of the shots of one scene (D-75, 2026-10-25)
    "LT": "LORA_TRAINING.md",  # LoRA training control (D-72, 2026-10-23)  # the sourced production rules (registry standards/sourced_rules.json, 2026-10-19)
    "BP": "SOURCED_RULES.md",  # the sourced production rules (registry standards/sourced_rules.json, 2026-10-19)
    "WB": "WORLD_BIBLE.md",  # the World Bible and the asset library (D-70 stage C, 2026-10-22)
    "RG": "STORY_ENGINE.md",  # the AI register (Blueprint P3, 2026-10-30)
    "VP": "SCRIPT_ENGINE.md",  # the variant planner checks (Blueprint P3, 2026-10-30)
    "CR": "CLOUD_RUNBOOK.md",  # how a pod ends: the three stop paths, the pod wrapper, the watchdog (P1a, 2026-10-29)
    "RP": "CLOUD_RUNBOOK.md",  # when a paid pod is worth starting: batching, card choice, retries, the bill (P1c, 2026-10-30)
    "SD": "AUDIO_SYSTEM.md",  # the sound director checks (Blueprint P4, 2026-10-30)
    "CN": "CONTRACTS.md",  # the data contracts, the episode lifecycle and the shot cache (Blueprint P2, 2026-10-29)
    "CMP": "COMPENSATOR.md",  # the visual compensator: maps, HUD, tableaux, the eight map laws (Blueprint P5, 2026-10-30)
    "SA": "SCENE_ASSETS.md",  # the drawn scene assets and the J5 2.5D assembly (D-116, ICW-11, 2026-11-06)
    "LJ": "LTX_JOBS.md",  # the LTX generations of the J2/J4 routes (ltx_job/1, D-116, guide step 3, 2026-11-06)
    "EP": "EPISODE_FIRST.md",  # one folder, one id, one look per episode (v4.3, D-131, 2026-11-12)
    "RT": "EPISODE_FIRST.md",  # the shot route and the visual mix by duration (v4.3, D-131, 2026-11-12)
    "SP": "EPISODE_FIRST.md",  # the episode's sound plan and the one stem renderer (v4.3 P7, 2026-11-12)
    "RN": "EPISODE_FIRST.md",  # the one episode runner: stages, records, timing, chunked assembly (v4.3 P8, 2026-11-12)
    "GC": "GEMINI_CONSISTENCY_RULES.md",  # pictures through the Gemini chat: turn packs, intake, masters (v4.3, D-131)
    "LIB": "SOUND_LIBRARY.md",  # the professional sound library: sources, licences, catalog, QC, search (2026-11-13, D-134)
    "VT": "VAULT.md",  # the vault: nothing we made is lost (D-73, 2026-10-24)  # the sourced production rules (registry standards/sourced_rules.json, 2026-10-19)
}
_PREFIX = "|".join(sorted(HOMES, key=len, reverse=True))
ID = re.compile(rf"\b({_PREFIX})-([TE]?\d{{2,3}})\b")
ROW = re.compile(rf"^\|\s*\**({_PREFIX})-([TE]?\d{{2,3}})\**\s*\|")
LINK = re.compile(r"\[[^\]]+\]\(([^)#\s]+)(?:#[^)]*)?\)")
HEX = re.compile(r"#[0-9A-Fa-f]{6}\b")


def _docs() -> list[Path]:
    return sorted(p for p in DOCS.glob("*.md") if p.name not in HISTORY)


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def definitions() -> dict[str, list[str]]:
    """ID -> the documents that define it (a table row starting with the ID)."""
    found: dict[str, list[str]] = {}
    for path in _docs():
        for line in _text(path).splitlines():
            match = ROW.match(line)
            if match:
                found.setdefault(f"{match.group(1)}-{match.group(2)}", []).append(path.name)
    return found


def _expand_ranges(text: str) -> set[str]:
    """IDs cited in text, including both ends of 'P-50 to P-56'."""
    return {f"{m.group(1)}-{m.group(2)}" for m in ID.finditer(text)}


def check() -> list[dict]:
    findings: list[dict] = []

    def add(check_id: str, detail: str) -> None:
        findings.append({"check": check_id, "detail": detail})

    defs = definitions()
    for ident, homes in defs.items():
        prefix = ident.split("-")[0]
        if homes != [HOMES[prefix]]:
            add("canonical_home", f"{ident} defined in {homes}, expected only {HOMES[prefix]}")
    for path in _docs():
        text = _text(path)
        for ident in sorted(_expand_ranges(text)):
            if ident not in defs:
                add("undefined_id", f"{path.name} cites {ident}, which no document defines")
        for target in LINK.findall(text):
            if re.match(r"[a-z]+://", target) or target.startswith("mailto:"):
                continue
            if not (path.parent / target).resolve().exists():
                add("broken_link", f"{path.name} links to {target}, which does not exist")
        for match in HEX.finditer(text):
            add("hex_in_docs", f"{path.name} contains {match.group(0)}; colours live only in palette.json")
        for block in re.findall(r"```json\n(.*?)```", text, flags=re.S):
            if "..." in block or "|" in block:
                continue  # a shape sketch, not a fixture
            try:
                json.loads(block)
            except ValueError as exc:
                add("bad_json", f"{path.name}: a json block does not parse ({exc})")
    index = _text(DOCS / "INDEX.md")
    for path in _docs():
        if path.name != "INDEX.md" and path.name not in index:
            add("not_indexed", f"{path.name} is not listed in docs/INDEX.md")
    return findings


if __name__ == "__main__":
    problems = check()
    for p in problems:
        print("FAIL", p["check"], p["detail"])
    print(f"{len(problems)} finding(s)")
    raise SystemExit(1 if problems else 0)
