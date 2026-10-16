"""The production script (D-43): one JSON file per video that is the script, the voice direction, the picture plan,
the sound plan and the edit. ``schemas/production_script.schema.json`` defines it.

A segment is written whole: its lines, the shots that illustrate them (each with its picture and the picture's
subject, i.e. its prompt) and its sounds. Phrases (``at``) point into the segment's own words, so the plan is checked
against the text before anything is read or painted, and timed from the read afterwards without guessing: words.json
made by ``scribe_words.align`` from ``narration_text`` has exactly one entry per written token, in order.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from explainer_engine.audio.scribe_words import script_tokens

SCHEMA_FILE = Path(__file__).resolve().parents[1] / "schemas" / "production_script.schema.json"
PAUSE_TAGS = ((1.8, "[long pause]"), (1.0, "[pause]"), (0.5, "[short pause]"))


def load(path: Path | str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save(doc: dict, path: Path | str) -> None:
    from explainer_engine.core.store import write_text_atomic
    write_text_atomic(Path(path), json.dumps(doc, indent=1, ensure_ascii=False) + "\n")


def schema_errors(doc: dict) -> list[str]:
    import jsonschema

    schema = json.loads(SCHEMA_FILE.read_text(encoding="utf-8"))
    v = jsonschema.Draft202012Validator(schema)
    return [f"{'/'.join(str(p) for p in e.absolute_path) or '<root>'}: {e.message}" for e in sorted(
        v.iter_errors(doc), key=lambda e: list(map(str, e.absolute_path)))]


def tok(s: str) -> str:
    return re.sub(r"[^a-z0-9']", "", s.lower().replace("’", "'"))


# --- text ------------------------------------------------------------------------------------------------------------

def narration_text(doc: dict) -> str:
    """What is said: one paragraph per segment (the words.json / captions / claim-map text)."""
    return "\n".join(" ".join(line["text"].strip() for line in seg["lines"]) for seg in doc["segments"]) + "\n"


def _emphasise(text: str, word: str) -> str:
    return re.sub(rf"(?<![A-Za-z']){re.escape(word)}(?![A-Za-z'])", word.upper(), text, count=1, flags=re.I)


def tts_line(line: dict) -> str:
    text = line["text"].strip()
    for w in line.get("emphasis", []):
        text = _emphasise(text, w)
    tags = "".join(f"[{t}] " for t in line.get("tags", []))
    pause = next((tag for limit, tag in PAUSE_TAGS if line.get("pause_after", 0) >= limit), "")
    return f"{tags}{text}" + (f" {pause}" if pause else "")


def tts_text(doc: dict) -> str:
    """What the voice gets: delivery tags where the delivery changes, one stressed word in capitals, pause tags."""
    return "\n".join(" ".join(tts_line(line) for line in seg["lines"]) for seg in doc["segments"]) + "\n"


def tts_chunks(doc: dict, max_chars: int = 900) -> list[dict]:
    """The read in chunks of whole segments, at most ``max_chars`` each (one segment longer than that is its own chunk).
    One v4 generation of the whole Day 1 read (2,917 characters) drifted to another-sounding voice after ~3 minutes
    (``audio/voice_check.py``); each chunk is one generation with the same voice and settings, and carries the text
    before and after it so the delivery joins up. The chunks are joined by ``production words`` (several files)."""
    segs = [(seg["id"], " ".join(tts_line(line) for line in seg["lines"])) for seg in doc["segments"]]
    groups, cur = [], []
    for sid, text in segs:
        if cur and sum(len(t) + 1 for _, t in cur) + len(text) > max_chars:
            groups.append(cur)
            cur = []
        cur.append((sid, text))
    if cur:
        groups.append(cur)
    out = []
    for k, g in enumerate(groups):
        out.append({"id": f"T{k + 1:02d}", "segments": [s for s, _ in g], "text": "\n".join(t for _, t in g),
                    "chars": sum(len(t) for _, t in g),
                    "previous_text": groups[k - 1][-1][1] if k else "",
                    "next_text": groups[k + 1][0][1] if k + 1 < len(groups) else ""})
    return out


# --- tokens and phrases ----------------------------------------------------------------------------------------------

def tokens(doc: dict) -> list[dict]:
    """Written tokens of the whole narration (``scribe_words.script_tokens``), each with its segment and line index."""
    toks = script_tokens(narration_text(doc))
    k = 0
    for si, seg in enumerate(doc["segments"]):
        for li, line in enumerate(seg["lines"]):
            n = len(script_tokens(line["text"]))
            for t in toks[k:k + n]:
                t["seg"], t["line"] = si, li
            k += n
    if k != len(toks):
        raise ValueError(f"token count mismatch: lines give {k}, the text {len(toks)}")
    return toks


def find_phrase(toks: list[dict], phrase: str, start: int, stop: int | None = None) -> int | None:
    """First token index in [start, stop) where ``phrase`` begins (case and punctuation ignored); None if absent."""
    want = [tok(p) for p in phrase.split() if tok(p)]
    stop = len(toks) if stop is None else stop
    if not want:
        return None
    for i in range(start, stop - len(want) + 1):
        if all(tok(toks[i + j]["w"].split()[0]) == want[j] for j in range(len(want))):
            return i
    return None


def segment_spans(toks: list[dict], n_segments: int) -> list[tuple[int, int]]:
    spans = []
    for si in range(n_segments):
        idx = [i for i, t in enumerate(toks) if t["seg"] == si]
        spans.append((idx[0], idx[-1] + 1))
    return spans


# --- pictures and shots ----------------------------------------------------------------------------------------------

def shots(doc: dict) -> list[dict]:
    """Every shot in script order with its sequence number (1..N), id (SH001...), segment and picture id."""
    out, n = [], 0
    for seg in doc["segments"]:
        for s in seg["shots"]:
            n += 1
            pic = s["picture"]
            out.append({"seq": n, "id": f"SH{n:03d}", "segment": seg["id"], "light_beat": seg["light_beat"],
                        "picture_id": pic if isinstance(pic, str) else pic["id"], "shot": s})
    return out


def pictures(doc: dict) -> tuple[dict, list[str]]:
    """(id -> picture, problems): library pictures plus every picture defined inline in a shot (defined once, then
    referred to by id). Each picture gets ``first_use`` (shot id) and ``uses`` (shot ids)."""
    out = {k: dict(v, id=k, source="library") for k, v in doc.get("library", {}).items()}
    problems = []
    for sh in shots(doc):
        pic = sh["shot"]["picture"]
        if isinstance(pic, dict):
            if pic["id"] in out:
                problems.append(f"{sh['id']}: picture {pic['id']!r} is defined twice (define once, then refer to it by id)")
                continue
            out[pic["id"]] = dict(pic, source="inline", first_use=sh["id"], uses=[])
        elif pic not in out:
            problems.append(f"{sh['id']}: picture {pic!r} is not defined (inline or in the library) before it is used")
            continue
        out[sh["picture_id"]].setdefault("first_use", sh["id"])
        out[sh["picture_id"]].setdefault("uses", []).append(sh["id"])
    return out, problems


def hero_names(doc: dict) -> dict[str, list[str]]:
    return {h: c["names"] for h, c in doc["cast"].items()}
