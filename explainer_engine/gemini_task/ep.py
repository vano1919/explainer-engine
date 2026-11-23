"""Shared inputs of the Gemini Task route: the config, the episode, its look and era line, the work folder."""
from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

from explainer_engine.core.errors import ContractError
from explainer_engine.core.store import write_json_atomic
from explainer_engine.imagegen import turn_pack as TP

REPO = Path(__file__).resolve().parents[2]
CONFIG = REPO / "config" / "gemini_task.json"
ERA_LINE = re.compile(r"^The world is [^:]+: the only light sources are [^,].*, and everything is made of [^.]+\.$")


@lru_cache(maxsize=1)
def config() -> dict:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def commit() -> str:
    try:
        return subprocess.run(["git", "-C", str(REPO), "rev-parse", "--short=12", "HEAD"], capture_output=True, text=True,
                              timeout=10, check=True).stdout.strip() or "unknown"
    except Exception:  # noqa: BLE001 - a copy of the repo without git still exports
        return "unknown"


def load(root: Path) -> tuple[dict, dict]:
    """(episode.json, production script 4.0.0) of an episode folder (EP-01)."""
    return TP.load(Path(root))


def preset_id(man: dict) -> str:
    """The episode's look: ``look.preset`` or ``look.id`` when it names a preset, else the default profile (manifest)."""
    doc = json.loads(TP.PRESETS.read_text(encoding="utf-8"))
    look = man.get("look") or {}
    for k in ("preset", "id"):
        if look.get(k) in (doc.get("presets") or {}):
            return look[k]
    return doc["default_style_profile"]


def look(man: dict) -> dict:
    """The preset's sentences and lists, held to the same gates as the chat route (GC-03, GC-11, GC-18)."""
    pid = preset_id(man)
    pre = TP.preset(pid)
    out = dict(pre, id=pid)
    TP.look_of({"look": {"preset": pid}})   # GC-11 round-face words, GC-18 never-words in the look itself
    for k in ("style_sentence", "face_sentence", "style_reference_clause", "never_words"):
        if not pre.get(k):
            raise ContractError(f"style preset {pid}: {k} is missing")
    if re.search(r"\blantern\b", pre["style_sentence"], re.I):
        raise ContractError(f"style preset {pid}: the style sentence names a lantern (GC-22)")
    return out


def era_line(man: dict, lk: dict) -> str:
    """The episode's one era sentence (GC-22, preset ``era_line_shape``), held to its shape and the never-words."""
    line = str(man.get("era_line") or "").strip()
    if not line:
        raise ContractError(f"episode.json of {man.get('episode_id')} has no era_line (GC-22): "
                            f"write one sentence of the shape {lk.get('era_line_shape')!r}")
    if not ERA_LINE.match(line):
        raise ContractError(f"era_line {line!r} does not follow the shape {lk.get('era_line_shape')!r} (GC-22)")
    hits = TP.never_hits(lk, line)
    if hits:
        raise ContractError(f"era_line uses never-words {hits} (GC-18)")
    if re.search(r"\blantern\b", line, re.I):
        raise ContractError("era_line names a lantern (preset era_rule)")
    return line


def work(root: Path) -> Path:
    """The route's files inside the episode: ``planning/gemini_task/``."""
    return Path(root) / "planning" / "gemini_task"


def drive_dir(root: Path) -> Path:
    """The local mirror of the Drive tree (08_FILES_AND_STATE.md) that the PC session uploads."""
    return work(root) / "drive"


def read_json(path: Path, default=None):
    path = Path(path)
    if not path.is_file():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, doc) -> Path:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    return write_json_atomic(Path(path), doc)


def sha256_file(path: Path) -> str:
    return TP.sha256(Path(path))
