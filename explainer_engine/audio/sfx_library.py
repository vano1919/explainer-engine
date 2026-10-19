"""The reusable sound library: every sound is stored once, described in ``manifest.json`` and found by tags.

Layout: ``<root>/manifest.json`` and ``<root>/<category>/<id>.wav`` (16-bit mono WAV). Entries carry where they came
from (procedural seed, Gemini TTS prompt, Lyria prompt), what they cost, the licence status and whether a person has
listened. A machine review ("a model heard it") never counts as a human approval (``review.human``).

CLI: ``python -m explainer_engine.audio.sfx_library <root>`` validates the library (exit 1 on any finding).
"""

from __future__ import annotations

import hashlib
import io
import json
import sys
import wave
from pathlib import Path

import jsonschema
import numpy as np

from explainer_engine.core.store import write_json_atomic

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schemas" / "sfx_manifest.schema.json"
MAX_PEAK_DBFS = -1.0   # stored sounds never touch full scale
STORE_PEAK_DBFS = -3.0  # sounds are normalised to this peak; the mixer sets the level per event


def db(x: float) -> float:
    return float(20 * np.log10(max(x, 1e-9)))


def read_wav(path_or_bytes) -> tuple[np.ndarray, int]:
    src = io.BytesIO(path_or_bytes) if isinstance(path_or_bytes, bytes) else str(path_or_bytes)
    with wave.open(src) as w:
        if w.getsampwidth() != 2 or w.getnchannels() != 1:
            raise ValueError("library sounds are 16-bit mono WAV")
        return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768, w.getframerate()


def wav_bytes(samples: np.ndarray, rate: int) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes((np.clip(samples, -1, 1) * 32767).astype(np.int16).tobytes())
    return buf.getvalue()


def normalise(samples: np.ndarray, peak_dbfs: float = STORE_PEAK_DBFS) -> np.ndarray:
    peak = float(np.max(np.abs(samples))) if len(samples) else 0.0
    if peak <= 0:
        raise ValueError("silent sound")
    return samples * (10 ** (peak_dbfs / 20) / peak)


def measure(samples: np.ndarray, rate: int) -> dict:
    return {"seconds": round(len(samples) / rate, 3), "sample_rate": rate,
            "peak_dbfs": round(db(float(np.max(np.abs(samples)))), 2),
            "rms_dbfs": round(db(float(np.sqrt(np.mean(samples ** 2)))), 2)}


def load_manifest(root: Path) -> dict:
    path = Path(root) / "manifest.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"version": 1, "items": []}


def add(root: Path, *, name: str, take: int, category: str, tags: list[str], samples: np.ndarray, rate: int,
        source: dict, licence: dict, machine_review: str = "none") -> dict:
    """Store one sound (normalised) and register it. Replaces an entry with the same id."""
    root = Path(root)
    item_id = f"{name}__v{take}"
    samples = normalise(samples)
    data = wav_bytes(samples, rate)
    rel = f"{category}/{item_id}.wav"
    (root / category).mkdir(parents=True, exist_ok=True)
    (root / rel).write_bytes(data)
    stored, _ = read_wav(data)
    entry = {"id": item_id, "file": rel, "category": category, "tags": sorted(set(tags)), **measure(stored, rate),
             "sha256": hashlib.sha256(data).hexdigest(), "source": source, "licence": licence,
             "review": {"machine": machine_review, "human": "not_listened"}}
    manifest = load_manifest(root)
    manifest["items"] = [i for i in manifest["items"] if i["id"] != item_id] + [entry]
    manifest["items"].sort(key=lambda i: i["id"])
    write_json_atomic(root / "manifest.json", manifest)
    return entry


def find(root: Path, *, tags: list[str] | None = None, category: str | None = None, usable: bool = True) -> list[dict]:
    """Entries having ALL the tags. ``usable`` hides human-rejected sounds."""
    out = []
    for item in load_manifest(root)["items"]:
        if category and item["category"] != category:
            continue
        if tags and not set(tags) <= set(item["tags"]):
            continue
        if usable and item["review"]["human"] == "rejected":
            continue
        out.append(item)
    return out


def validate(root: Path, *, check_files: bool = True) -> list[str]:
    """Manifest problems; with ``check_files`` also every file (present, unchanged, readable). The WAVs are not in git, so a
    clean checkout validates the manifest only (``check_files=False``)."""
    root = Path(root)
    problems: list[str] = []
    manifest = load_manifest(root)
    try:
        jsonschema.validate(manifest, json.loads(SCHEMA_PATH.read_text(encoding="utf-8")))
    except jsonschema.ValidationError as exc:
        return [f"manifest: {exc.message}"]
    seen = set()
    for item in manifest["items"]:
        if item["id"] in seen:
            problems.append(f"{item['id']}: duplicate id")
        seen.add(item["id"])
        if not check_files:
            continue
        path = root / item["file"]
        if not item["file"].startswith(item["category"] + "/"):
            problems.append(f"{item['id']}: file is not under its category folder")
        if not path.exists():
            if check_files:
                problems.append(f"{item['id']}: file missing")
            continue
        if not check_files:
            continue
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != item["sha256"]:
            problems.append(f"{item['id']}: file changed since it was registered")
            continue
        samples, rate = read_wav(data)
        m = measure(samples, rate)
        if abs(m["seconds"] - item["seconds"]) > 0.01 or rate != item["sample_rate"]:
            problems.append(f"{item['id']}: duration or sample rate differs from the manifest")
        if m["peak_dbfs"] > MAX_PEAK_DBFS:
            problems.append(f"{item['id']}: peak {m['peak_dbfs']} dBFS is above {MAX_PEAK_DBFS}")
    if check_files:
        for path in root.rglob("*.wav"):
            if path.relative_to(root).as_posix() not in {i["file"] for i in manifest["items"]}:
                problems.append(f"{path.relative_to(root).as_posix()}: not in the manifest")
    return problems


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        print(__doc__)
        return 2
    problems = validate(Path(argv[0]))
    for p in problems:
        print("FAIL", p)
    print(f"{len(load_manifest(Path(argv[0]))['items'])} sounds, {len(problems)} finding(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
