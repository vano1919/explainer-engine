"""The sound library's catalog (LIB-01..LIB-08, docs/SOUND_LIBRARY.md): one searchable view over ``manifest.json`` (the library's
single source of truth, ``audio/sfx_library``) with every item's classification, licence and technical facts, so a sound is
found by what it is (category, genre, scene, era, mood, material, distance, usage) instead of by its file name.

* ``migrate``: gives every older item (W1's CC0 takes, the ElevenLabs beds, the procedural placeholders, the Gemini TTS
  vocals) a ``catalog`` block inferred from its tags (``inferred: true``) and the licence fields of LIB-04, without touching
  its file. Hand-classified items (the 2026-11-13 import) are left as they are.
* ``requalify``: re-runs the technical QC (``audio/asset_qc``) on every working copy (and its original when present).
* ``build_index``: writes ``<root>/catalog.sqlite`` (derived, gitignored): table ``assets`` with one column per required
  field and table ``facets`` (asset_id, dimension, value) for the multi-valued dimensions.
* ``search``: filters on any dimension, the licence status and the QC status; ``preview``: an audition folder (MP3 excerpts,
  a spectrogram per sound and an ``index.html`` with players) for the sounds a search returns; ``duplicates``: exact
  (sha256 of the original or the working copy) and near-duplicate (spectral fingerprint) pairs; ``credits``: the
  description's credit lines for the items an episode used.

CLI::

    python -m explainer_engine.audio.catalog migrate|requalify|index|report  [--root assets/audio/library]
    python -m explainer_engine.audio.catalog search --category ambience --era bronze_age --mood tense --usage background_layer
    python -m explainer_engine.audio.catalog preview --genre battlefield --out assets/audio/previews/battle
    python -m explainer_engine.audio.catalog duplicates
    python -m explainer_engine.audio.catalog credits <stems_report.json|cue_sheet.json>
"""
from __future__ import annotations

import argparse
import html
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import numpy as np

from explainer_engine.audio import sfx_library as L
from explainer_engine.audio import sources as S
from explainer_engine.core.store import write_json_atomic, write_text_atomic

ROOT = Path(__file__).resolve().parents[2] / "assets" / "audio" / "library"
TAXONOMY_PATH = Path(__file__).resolve().parents[2] / "assets" / "audio" / "taxonomy.json"
MULTI = ("genres", "scene_types", "historical_era", "environment", "materials", "action_tags", "mood", "usage")
COLUMNS = ("asset_id", "title", "original_filename", "local_path", "source_name", "source_url", "creator", "license_type",
           "license_url", "attribution_required", "attribution_text", "commercial_use_allowed", "modification_allowed",
           "redistribution_allowed", "ai_processing_allowed", "downloaded_at", "sha256", "duration_seconds", "format",
           "sample_rate", "channels", "bit_depth", "sound_category", "sound_subcategory", "genres", "scene_types",
           "historical_era", "environment", "materials", "action_tags", "mood", "intensity", "distance", "perspective",
           "intended_usage", "loopable", "kind", "technical_quality_status", "licensing_status", "human_review", "tags")


def taxonomy() -> dict:
    return json.loads(TAXONOMY_PATH.read_text(encoding="utf-8"))


# --- inference for older items (no hand classification yet) -----------------------------------------------------------

_TAG_CATEGORY = [({"music"}, "music"), ({"vocal", "yawn", "laugh", "gasp", "sigh"}, "human"),
                 ({"rain", "wind", "thunder", "fire", "river", "water", "waves", "rumble", "eruption", "ash"}, "natural_elements"),
                 ({"birds", "crickets", "horse"}, "animals"), ({"sword", "bow", "arrow", "spear"}, "weapons"),
                 ({"footstep", "armour", "clink", "cloth", "step"}, "foley"), ({"impact", "thud", "boom", "hit"}, "impacts"),
                 ({"swish", "whoosh", "transition"}, "transitions"), ({"ambience", "bed"}, "ambience"),
                 ({"pop", "tick", "bell", "ui", "click", "glow"}, "interface")]
_MODERN = {"city", "street", "traffic", "garage", "motel", "highway", "warehouse", "factory", "office", "courthouse",
           "parking", "electric", "battery", "industrial", "workshop", "pool", "clock"}


def infer_catalog(item: dict) -> dict:
    tags = set(item.get("tags", []))
    cat = next((c for keys, c in _TAG_CATEGORY if keys & tags), "foley")
    kind = L.kind_of(item)
    era = ["modern"] if tags & _MODERN else ["any"]
    return {"title": item["id"].rsplit("__", 1)[0].replace("_", " "), "bst": "music" if cat == "music" else
            ("speech" if cat == "human" else ("soundscapes" if kind == "loop" and cat in ("ambience", "natural_elements")
                                              else "sound_effects")),
            "sound_category": cat, "subcategory": sorted(tags)[0] if tags else "", "genres": ["modern"] if era == ["modern"] else [],
            "scene_types": [], "historical_era": era, "environment": [], "materials": [], "action_tags": [],
            "mood": [], "distance": "medium", "space": "interior" if {"indoor", "interior", "hall"} & tags else "exterior",
            "usage": ["background_layer"] if kind == "loop" else ["synced_foley"], "loopable": kind == "loop", "inferred": True}


def _legacy_licence(item: dict) -> dict:
    lic = dict(item.get("licence") or {})
    if lic.get("type"):
        return lic
    origin = (item.get("source") or {}).get("kind")
    status = lic.get("status")
    typ = {"cc0": "cc0", "own_procedural": "own_procedural", "generated_terms_unverified": "generated_unverified"}.get(status)
    if typ is None:
        typ = "elevenlabs_output" if origin == "elevenlabs" else ("cc0" if status == "cc0" else "unknown")
    spec = S.LICENCES[typ]
    creator = {"procedural": "own (numpy)", "elevenlabs": "ElevenLabs (generated)", "gemini_tts": "Gemini TTS (generated)",
               "lyria": "Lyria (generated)"}.get(origin, "see note")
    lic.update({"type": typ, "url": spec["url"], "source_url": lic.get("source_url", ""), "creator": creator,
                "attribution_required": bool(spec["attribution"]), "attribution_text": lic.get("attribution"),
                "commercial_use": spec["commercial"], "modification": spec["modification"],
                "redistribution": spec["redistribution"], "ai_processing": spec.get("ai_processing", True),
                "read_on": (item.get("source") or {}).get("generated", ""), "production": S.verdict(typ)})
    return lic


def migrate(root: Path = ROOT) -> dict:
    m = L.load_manifest(root)
    changed = 0
    for item in m["items"]:
        before = json.dumps(item, sort_keys=True)
        item.setdefault("catalog", infer_catalog(item))
        item["licence"] = _legacy_licence(item)
        if json.dumps(item, sort_keys=True) != before:
            changed += 1
    write_json_atomic(Path(root) / "manifest.json", m)
    return {"items": len(m["items"]), "changed": changed}


def requalify(root: Path = ROOT) -> dict:
    """Re-run the technical QC on every working copy present (and its original, when the originals store has it)."""
    from explainer_engine.audio import asset_qc as Q
    from explainer_engine.audio import free_import as F
    root = Path(root)
    m = L.load_manifest(root)
    out = {"PASS": 0, "REVIEW": 0, "FAIL": 0, "missing": 0}
    for item in m["items"]:
        wav = root / item["file"]
        if not wav.is_file():
            out["missing"] += 1
            continue
        y, rate = L.read_wav(wav.read_bytes())
        orig_path = root.parent / item["original"]["path"] if item.get("original") else None
        if orig_path is not None and orig_path.is_file():
            probe, x = Q.probe(orig_path), F.decode(orig_path)
        else:
            probe, x = {"ok": True, "codec": "pcm_s16le"}, y
        raw = Q.measure(x, rate if x is y else F.RATE)
        qc = Q.check(probe, raw, kind=L.kind_of(item), stored=y, rate=rate, item_id=item["id"])
        if (item.get("source") or {}).get("kind") == "procedural":
            qc["findings"].append({"status": "REVIEW", "detail": "procedural placeholder: never shippable (stems.Sounds)"})
            qc["status"] = "REVIEW" if qc["status"] == "PASS" else qc["status"]
        item["qc"] = dict(qc, measured=raw)
        out[qc["status"]] += 1
    write_json_atomic(root / "manifest.json", m)
    return out


# --- the index -----------------------------------------------------------------------------------------------------------

def row_of(item: dict) -> dict:
    c = item.get("catalog") or infer_catalog(item)
    lic = item.get("licence") or {}
    o = item.get("original") or {}
    src = item.get("source") or {}
    qc = (item.get("qc") or {}).get("status") or "NOT_RUN"
    return {"asset_id": item["id"], "title": c.get("title") or item["id"], "original_filename": o.get("filename"),
            "local_path": item["file"], "source_name": (src.get("prompt") or "").split(" ", 1)[0] if src.get("kind") == "third_party"
            else src.get("kind"), "source_url": lic.get("source_url"), "creator": lic.get("creator"),
            "license_type": lic.get("type"), "license_url": lic.get("url"), "attribution_required": lic.get("attribution_required"),
            "attribution_text": lic.get("attribution_text") or lic.get("attribution"),
            "commercial_use_allowed": lic.get("commercial_use"), "modification_allowed": lic.get("modification"),
            "redistribution_allowed": lic.get("redistribution"), "ai_processing_allowed": lic.get("ai_processing"),
            "downloaded_at": o.get("downloaded_at") or src.get("generated"), "sha256": o.get("sha256") or item["sha256"],
            "duration_seconds": item["seconds"], "format": o.get("format") or "wav", "sample_rate": o.get("sample_rate") or item["sample_rate"],
            "channels": o.get("channels") or 1, "bit_depth": o.get("bit_depth") or 16, "sound_category": c.get("sound_category"),
            "sound_subcategory": c.get("subcategory"), **{k: c.get(k) or [] for k in MULTI if k != "usage"},
            "intensity": c.get("intensity"), "distance": c.get("distance"), "perspective": c.get("space"),
            "intended_usage": c.get("usage") or [], "loopable": bool(c.get("loopable", L.kind_of(item) == "loop")),
            "kind": L.kind_of(item), "technical_quality_status": qc, "licensing_status": L.production_status(item),
            "human_review": (item.get("review") or {}).get("human"), "tags": item.get("tags", [])}


def build_index(root: Path = ROOT, path: Path | None = None) -> Path:
    root = Path(root)
    path = Path(path) if path else root / "catalog.sqlite"
    tmp = path.with_suffix(".part")
    tmp.unlink(missing_ok=True)
    db = sqlite3.connect(tmp)
    db.execute(f"CREATE TABLE assets ({', '.join(c + ' TEXT' for c in COLUMNS)}, PRIMARY KEY (asset_id))")
    db.execute("CREATE TABLE facets (asset_id TEXT, dimension TEXT, value TEXT)")
    for item in L.load_manifest(root)["items"]:
        r = row_of(item)
        db.execute(f"INSERT INTO assets VALUES ({', '.join('?' * len(COLUMNS))})",
                   [json.dumps(r[c]) if isinstance(r[c], (list, bool)) or r[c] is None else str(r[c]) for c in COLUMNS])
        for dim in MULTI + ("tags",):
            key = "intended_usage" if dim == "usage" else dim
            for v in r[key]:
                db.execute("INSERT INTO facets VALUES (?, ?, ?)", (r["asset_id"], dim, str(v)))
        for dim in ("sound_category", "distance", "perspective", "kind", "licensing_status", "technical_quality_status"):
            db.execute("INSERT INTO facets VALUES (?, ?, ?)", (r["asset_id"], dim, str(r[dim])))
    db.execute("CREATE INDEX f_dim ON facets (dimension, value)")
    db.commit()
    db.close()
    tmp.replace(path)
    return path


FILTERS = {"category": "sound_category", "genre": "genres", "scene": "scene_types", "era": "historical_era",
           "mood": "mood", "material": "materials", "distance": "distance", "usage": "usage", "environment": "environment",
           "space": "perspective", "kind": "kind", "licence": "licensing_status", "qc": "technical_quality_status",
           "tag": "tags", "action": "action_tags"}
COLUMN_FILTERS = {"source": "source_name", "licence_type": "license_type"}    # one value per item: matched on the column


def search(root: Path = ROOT, *, playable_only: bool = False, **filters) -> list[dict]:
    """Assets matching ALL the given filters (each a value or a list of acceptable values). ``era`` also accepts items made
    for ``any`` era. ``playable_only``: licence verified and QC not FAIL (what the engine may pick)."""
    path = Path(root) / "catalog.sqlite"
    if not path.is_file():
        build_index(root)
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    where, args = [], []
    for k, v in filters.items():
        if v in (None, "", []):
            continue
        vals = [v] if isinstance(v, str) else list(v)
        if k in COLUMN_FILTERS:
            where.append(f"{COLUMN_FILTERS[k]} IN ({', '.join('?' * len(vals))})")
            args += vals
            continue
        dim = FILTERS[k]
        if k == "era":
            vals = vals + ["any"]
        where.append(f"asset_id IN (SELECT asset_id FROM facets WHERE dimension = ? AND value IN ({', '.join('?' * len(vals))}))")
        args += [dim] + vals
    if playable_only:
        where.append("licensing_status = '\"verified\"' OR licensing_status = 'verified'")
    sql = "SELECT * FROM assets" + (" WHERE " + " AND ".join(f"({w})" for w in where) if where else "") + " ORDER BY asset_id"
    rows = [dict(r) for r in db.execute(sql, args)]
    db.close()
    for r in rows:
        for c in COLUMNS:
            v = r[c]
            if isinstance(v, str) and v[:1] in "[tfn" and v in ("true", "false", "null") or (isinstance(v, str) and v[:1] == "["):
                r[c] = json.loads(v)
    if playable_only:
        rows = [r for r in rows if r["technical_quality_status"] != "FAIL"]
    return rows


# --- audition --------------------------------------------------------------------------------------------------------------

def preview(rows: list[dict], out: Path, root: Path = ROOT, seconds: float = 12.0) -> Path:
    """An audition folder: ``<id>.mp3`` (the first ``seconds``), ``<id>.png`` (spectrogram) and ``index.html`` with a player,
    the facts and the licence per sound. Open index.html in a browser (or the HF folder) to listen before choosing."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    cards = []
    for r in rows:
        wav = Path(root) / r["local_path"]
        if not wav.is_file():
            continue
        mp3, png = out / f"{r['asset_id']}.mp3", out / f"{r['asset_id']}.png"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(wav), "-t", str(seconds), "-af", "afade=t=out:st=%g:d=0.5"
                        % max(0.0, min(seconds, float(r["duration_seconds"])) - 0.5), "-b:a", "128k", str(mp3)], check=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(wav), "-lavfi",
                        "showspectrumpic=s=640x160:legend=0:scale=log:color=magma", str(png)], check=True)
        facts = " · ".join(str(x) for x in (r["sound_category"], r["kind"], f"{float(r['duration_seconds']):.1f} s",
                                            ", ".join(r["mood"] or []), r["distance"], ", ".join(r["historical_era"] or [])))
        cards.append(f"<section><h3>{html.escape(r['title'])} <small>{r['asset_id']}</small></h3>"
                     f"<audio controls preload=none src=\"{mp3.name}\"></audio><img src=\"{png.name}\" alt=\"\">"
                     f"<p>{html.escape(facts)}</p><p class=lic>{html.escape(str(r['license_type']))} · "
                     f"{html.escape(str(r['licensing_status']))} · QC {r['technical_quality_status']} · "
                     f"{html.escape(str(r['creator']))}</p></section>")
    page = ("<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width'><title>Sound audition</title>"
            "<style>body{font:15px system-ui;margin:16px;background:#111;color:#eee}section{margin:0 0 22px}img{width:100%;"
            "max-width:640px;display:block}audio{width:100%;max-width:640px}small,.lic{color:#999}</style>"
            f"<h1>Sound audition ({len(cards)})</h1>" + "".join(cards))
    write_text_atomic(out / "index.html", page)
    return out / "index.html"


def duplicates(root: Path = ROOT, near: bool = True) -> dict:
    from explainer_engine.audio import asset_qc as Q
    items = L.load_manifest(root)["items"]
    by: dict[str, list[str]] = {}
    for i in items:
        for h in {i["sha256"], (i.get("original") or {}).get("sha256")} - {None}:
            by.setdefault(h, []).append(i["id"])
    exact = [sorted(set(v)) for v in by.values() if len(set(v)) > 1]
    pairs = []
    if near:
        prints = {}
        for i in items:
            wav = Path(root) / i["file"]
            if wav.is_file() and (i.get("source") or {}).get("kind") != "procedural":
                x, rate = L.read_wav(wav.read_bytes())
                prints[i["id"]] = Q.fingerprint(x[: rate * 30], rate)
        pairs = Q.near_duplicates(prints)
    return {"exact": exact, "near": pairs}


def credits(ids: list[str], root: Path = ROOT) -> list[str]:
    """The credit lines for the items an episode used: every licence that asks for attribution, once per item."""
    items = {i["id"]: i for i in L.load_manifest(root)["items"]}
    lines = []
    for iid in sorted(set(ids)):
        lic = (items.get(iid) or {}).get("licence") or {}
        text = lic.get("attribution_text") or lic.get("attribution")
        if lic.get("attribution_required") and text and text not in lines:
            lines.append(text)
    return lines


def report(root: Path = ROOT) -> dict:
    rows = [row_of(i) for i in L.load_manifest(root)["items"]]

    def count(key):
        out: dict = {}
        for r in rows:
            out[str(r[key])] = out.get(str(r[key]), 0) + 1
        return dict(sorted(out.items()))
    return {"items": len(rows), "by_source": count("source_name"), "by_licence": count("license_type"),
            "by_licensing_status": count("licensing_status"), "by_category": count("sound_category"),
            "by_qc": count("technical_quality_status"), "by_kind": count("kind"),
            "classified_by_hand": sum(1 for i in L.load_manifest(root)["items"] if not (i.get("catalog") or {}).get("inferred"))}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="catalog", description=__doc__.splitlines()[0])
    ap.add_argument("cmd", choices=["migrate", "requalify", "index", "search", "preview", "duplicates", "credits", "report"])
    ap.add_argument("what", nargs="?")
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--out", default="assets/audio/previews/search")
    ap.add_argument("--playable", action="store_true")
    for k in list(FILTERS) + list(COLUMN_FILTERS):
        ap.add_argument(f"--{k.replace('_', '-')}", dest=k, action="append")
    a = ap.parse_args(argv)
    root = Path(a.root)
    filt = {k: getattr(a, k) for k in list(FILTERS) + list(COLUMN_FILTERS) if getattr(a, k)}
    if a.cmd == "migrate":
        print(json.dumps(migrate(root)))
    elif a.cmd == "requalify":
        print(json.dumps(requalify(root)))
    elif a.cmd == "index":
        print(build_index(root))
    elif a.cmd in ("search", "preview"):
        build_index(root)
        rows = search(root, playable_only=a.playable, **filt)
        for r in rows:
            print(f"{r['asset_id']:34} {r['sound_category'] or '':18} {r['kind']:8} {float(r['duration_seconds']):7.1f}s "
                  f"{','.join(r['mood'] or [])[:24]:24} {r['licensing_status']:10} QC {r['technical_quality_status']}")
        print(f"{len(rows)} sound(s)")
        if a.cmd == "preview":
            print(preview(rows, Path(a.out), root))
    elif a.cmd == "duplicates":
        print(json.dumps(duplicates(root), indent=1))
    elif a.cmd == "credits":
        doc = json.loads(Path(a.what).read_text(encoding="utf-8"))
        ids = [u.get("id") or u.get("asset_id") for u in doc.get("sounds_used", []) + doc.get("cues", []) + doc.get("rows", [])]
        print("\n".join(credits([i for i in ids if i], root)))
    else:
        print(json.dumps(report(root), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
