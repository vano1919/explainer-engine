"""The reusable sound library: every sound is stored once, described in ``manifest.json`` and found by tags.

Layout: ``<root>/manifest.json`` and ``<root>/<category>/<id>.wav`` (16-bit mono WAV). Entries carry where they came
from (procedural seed, Gemini TTS prompt, Lyria prompt), what they cost, the licence status and whether a person has
listened. A machine review ("a model heard it") never counts as a human approval (``review.human``).

BP-58: an item is a ``one_shot`` (a sting or impact, 0.1-5 s) or a ``loop`` (a bed of at least 20 s with a verified seam:
no step over ``seam_step_db_max`` at the join, no transient within ``seam_clear_s`` of it); the manifest says which
(``kind``, or PR #9's ``loop`` flag: ``loop: false`` is a one-shot). ``lint`` reports what breaks that (REVIEW, the registry's
severity); the schema itself is owned by the manifest PR.

CLI: ``python -m explainer_engine.audio.sfx_library <root>`` validates the library (exit 1 on any finding) and prints the lint.
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
from explainer_engine.standards import sourced_rules as SR

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schemas" / "sfx_manifest.schema.json"
MAX_PEAK_DBFS = -1.0   # stored sounds never touch full scale
STORE_PEAK_DBFS = -3.0  # sounds are normalised to this peak; the mixer sets the level per event
KINDS = ("one_shot", "loop")  # BP-58


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
        source: dict, licence: dict, machine_review: str = "none", loop: bool | None = None) -> dict:
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
    if loop is not None:
        entry["loop"] = loop
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


def validate(root: Path, *, check_files: bool = True, admissions: Path | str | None = None) -> list[str]:
    """Manifest problems; with ``check_files`` also every file (present, unchanged, readable). The WAVs are not in git, so a
    clean checkout validates the manifest only (``check_files=False``). An ``open_model`` item needs its admission, for its kind
    and model, in ``assets/audio/generator_admission.json`` (or ``admissions``; BP-162, SD-13)."""
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
        if item["source"]["kind"] == "open_model":
            from explainer_engine.audio import generator_gate  # lazy: the gate imports this module
            problems += generator_gate.item_problems(item, path=admissions)
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
    for f in lint(Path(argv[0])):  # BP-58: one-shots and loops (REVIEW)
        print(f"{f['severity']:6} {f['rule']} {f['where']}: {f['detail']}")
    print(f"{len(load_manifest(Path(argv[0]))['items'])} sounds, {len(problems)} finding(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())


# --- BP-58: one-shots and loops ---------------------------------------------------------------------------------------

def kind_of(item: dict) -> str:
    """``kind`` when the manifest says it; else PR #9's ``loop`` flag (false = one_shot); else a music item is a loop."""
    if item.get("kind") in KINDS:
        return item["kind"]
    if "loop" in item:
        return "loop" if item["loop"] else "one_shot"
    return "loop" if item.get("category") == "music" else "one_shot"


def _rms_db(x: np.ndarray) -> float:
    return db(float(np.sqrt(np.mean(x.astype(np.float64) ** 2)))) if len(x) else -120.0


def seam_step_db(samples: np.ndarray, rate: int, window_ms: float = 50.0) -> float:
    """The level step heard when the loop wraps: RMS of its last ``window_ms`` against its first (50 ms: long enough that a
    noise bed's own fluctuation does not read as a step)."""
    h = max(1, int(window_ms / 1000 * rate))
    return abs(_rms_db(samples[:h]) - _rms_db(samples[-h:]))


def transient_near_seam(samples: np.ndarray, rate: int, clear_s: float, rise_db: float = 12.0) -> bool:
    """A 10 ms window within ``clear_s`` of either end that rises ``rise_db`` above the loop's median window level."""
    h = max(1, int(0.01 * rate))
    n = (len(samples) // h) * h
    if n < 3 * h:
        return False
    rms = np.sqrt(np.mean(samples[:n].astype(np.float64).reshape(-1, h) ** 2, axis=1))
    med = db(float(np.median(rms)))
    k = max(1, int(clear_s / 0.01))
    edge = np.concatenate([rms[:k], rms[-k:]])
    return bool(np.any(20 * np.log10(edge + 1e-9) > med + rise_db))


def check_seams(item: dict, samples: np.ndarray, rate: int) -> list[dict]:
    """BP-58 findings for one sound: a loop under ``loop_min_s``, a loop with an audible seam, a one-shot outside ``one_shot_s``."""
    t = SR.rule("BP-58")["thresholds"]
    sev = SR.rule("BP-58").get("severity", "REVIEW")
    out = []

    def add(detail):
        out.append({"rule": "BP-58", "severity": sev, "where": item["id"], "detail": detail})

    seconds = len(samples) / rate
    if kind_of(item) == "loop":
        if seconds < t["loop_min_s"]:
            add(f"loop of {seconds:.1f} s; a bed loop is at least {t['loop_min_s']:g} s (or a crossfaded join)")
        step = seam_step_db(samples, rate)
        if step > t["seam_step_db_max"]:
            add(f"seam steps {step:.2f} dB where the loop wraps (at most {t['seam_step_db_max']:g}): the join clicks")
        if transient_near_seam(samples, rate, t["seam_clear_s"]):
            add(f"a transient within {t['seam_clear_s']:g} s of the seam: the loop point is heard every pass")
    else:
        lo, hi = t["one_shot_s"]
        if not lo <= seconds <= hi:
            add(f"one-shot of {seconds:.2f} s; a sting or impact is {lo:g}-{hi:g} s (a longer sound is a loop or a bed)")
    return out


def lint(root: Path, *, check_files: bool = True) -> list[dict]:
    """BP-58 over the library (REVIEW findings; ``validate`` keeps the hard problems). Missing files are skipped."""
    root = Path(root)
    out = []
    for item in load_manifest(root)["items"]:
        if not check_files:
            continue
        path = root / item["file"]
        if not path.exists():
            continue
        samples, rate = read_wav(path.read_bytes())
        out += check_seams(item, samples, rate)
    return out
