"""The Drive rules pack export (build item 1; spec section 4, acceptance 2 and 5).

Writes the nine pack files ``rules/00..08`` of ``texts/drive_pack/`` into the local mirror of the Drive tree
(``<episode>/planning/gemini_task/drive/``), with every placeholder filled from its one home (the preset, the registry,
the config, the episode's era line), the operator notes stripped, and these refusals: an undeclared or unfilled
placeholder, a secret or keyed link, Georgian text, a file that is not exactly one topic (one ``#`` title). It also puts
the main style picture and every approved reference into ``episodes/<id>/refs/`` and lists it all in
``pack_manifest.json`` (file, sha256, bytes). The PC session uploads the folder as it is; nothing here touches Drive.
"""
from __future__ import annotations

import hashlib
import re
import shutil
from pathlib import Path

from explainer_engine.core.errors import ContractError
from explainer_engine.core.store import write_text_atomic
from explainer_engine.gemini_task import ep as EP
from explainer_engine.gemini_task import texts as TX

H1 = re.compile(r"^# \S", re.M)


def _bullets(items) -> str:
    return "\n".join(f"- {x}" for x in items)


def style_pack_table() -> str:
    rows = ["| Type | Shot | Anchor file on Drive | sha256 | Status |", "|---|---|---|---|---|"]
    main = EP.config()["main_style"]
    rows.append(f"| main | style anchors, hero portraits and full bodies, places | `{main['drive_name']}` | "
                f"`{main['sha256'][:16]}` | approved |")
    for a in EP.config()["style_pack"]["types"]:
        sha = f"`{a['sha256'][:16]}`" if a.get("sha256") else "-"
        rows.append(f"| {a['type']} | {a['label']} | `{a['drive_name']}` | {sha} | {a.get('status', 'candidate')} |")
    rows.append("")
    rows.append("Only an anchor whose status is approved is ever attached; until then its shots wait.")
    return "\n".join(rows)


def values(root: Path, lk: dict, era: str, version: str, date: str, commit: str) -> dict:
    return {"drive_root": EP.config()["drive_root"], "pack_version": version, "pack_date": date, "repo_commit": commit,
            "style_preset_id": lk["id"], "style_sentence": lk["style_sentence"], "face_sentence": lk["face_sentence"],
            "style_reference_clause": lk["style_reference_clause"], "never_words": _bullets(lk["never_words"]),
            "always_list": _bullets(lk.get("always") or []), "negative": lk.get("negative") or "-",
            "identity_rule": lk.get("identity_rule") or "-", "era_rule": lk.get("era_rule") or "-",
            "pictures_per_day": lk.get("pictures_per_day") or "25", "era_line": era,
            "style_pack_table": style_pack_table()}


def pack_files() -> list[dict]:
    return [f for f in TX.manifest()["files"] if f["kind"] == "drive_pack"]


def _render_all(root: Path, version: str, date: str, commit: str) -> dict[str, str]:
    man, _ = EP.load(root)
    lk = EP.look(man)
    era = EP.era_line(man, lk)
    vals = values(root, lk, era, version, date, commit)
    out = {}
    for f in pack_files():
        name = Path(f["path"]).name
        text = TX.fill(TX.pack_file(name), vals, where=name)
        TX.clean_gate(text, name)
        if len(H1.findall(text)) != 1:
            raise ContractError(f"{name}: one topic per file means one '# ' title, found {len(H1.findall(text))}")
        out[name] = text
    return out


def current_version(root: Path) -> str | None:
    """The pack version of the last export of this episode (what T0 and P0 must quote)."""
    doc = EP.read_json(EP.drive_dir(root) / "pack_manifest.json")
    return doc.get("pack_version") if doc else None


def export(root: Path) -> dict:
    root = Path(root)
    man, _ = EP.load(root)
    date = EP.now()[:10]
    commit = EP.commit()
    body = _render_all(root, "{pending}", date, commit)
    digest = hashlib.sha256("".join(body[k] for k in sorted(body) if not k.startswith("00_")).encode()).hexdigest()[:8]
    version = f"{date}.{commit[:8]}.{digest}"
    body = _render_all(root, version, date, commit)
    drive = EP.drive_dir(root)
    files = []
    for name, text in body.items():
        p = drive / "rules" / name
        p.parent.mkdir(parents=True, exist_ok=True)
        write_text_atomic(p, text)
        files.append({"path": f"rules/{name}", "sha256": hashlib.sha256(text.encode()).hexdigest(), "bytes": len(text.encode())})
    files += copy_refs(root, man["episode_id"])
    doc = {"schema": "gemini_drive_pack/1", "episode_id": man["episode_id"], "pack_version": version, "exported_at": EP.now(),
           "repo_commit": commit, "drive_root": EP.config()["drive_root"], "files": files,
           "upload": f"copy this folder's contents into Drive {EP.config()['drive_root']}/ as they are (rules/ and episodes/)"}
    EP.save_json(drive / "pack_manifest.json", doc)
    return doc


def copy_refs(root: Path, episode_id: str) -> list[dict]:
    """The main style picture, the approved style anchors and the approved references into ``episodes/<id>/refs/``."""
    from explainer_engine.gemini_task import queue as QU
    dst = EP.drive_dir(root) / "episodes" / episode_id / "refs"
    out = []

    def put(src: Path, name: str, sha: str | None):
        if not src.is_file():
            raise ContractError(f"{src} is missing")
        got = EP.sha256_file(src)
        if sha and got != sha:
            raise ContractError(f"{src} is not the approved picture (sha256 {got[:12]} vs {sha[:12]})")
        dst.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst / name)
        out.append({"path": f"episodes/{episode_id}/refs/{name}", "sha256": got, "bytes": (dst / name).stat().st_size})
    main = EP.config()["main_style"]
    put(EP.REPO / main["file"], main["drive_name"], main["sha256"])
    for a in QU.anchors():
        if a.get("status") == "approved" and a.get("file"):
            put(EP.REPO / a["file"] if not Path(a["file"]).is_absolute() else Path(a["file"]), a["drive_name"], a.get("sha256"))
    for rid, r in sorted(QU.references_state(root).items()):
        put(Path(root) / r["file"], Path(QU.ref_target(rid)).name, r.get("sha256"))
    return out
