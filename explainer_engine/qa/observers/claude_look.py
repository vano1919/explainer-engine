"""Claude look observer (OB-1): the session builds the sheet, opens it, answers the shot card's questions, ``record`` writes them.

Free: no model call here. ``request`` writes the contact sheet (a clip: 8 frames in one tile; a picture: the picture itself), one
full frame and the question list (the shot card's ``acceptance_questions`` of this kind plus the F1..F19 checklist of the vendored
``v-director-cinematic`` failure-modes). The session opens the files, and ``record`` takes its answers file::

    {"answers": {"<question>": <bool|text>}, "defects": [{"code": "F7", "where": "t=2.6-4.0s", "severity": "major", "note": "..."}],
     "note": "..."}

A defect code outside F1..F19 / TECH-* / TXT-* or one without an action in ``retry_router.R_ACTIONS`` is refused.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from explainer_engine.qa import observe as OB
from explainer_engine.qa import retry_router as RR
from explainer_engine.qa import status as ST

CHECKLIST = {  # F-code -> the question the session asks of a clip or a picture (vocabulary: v-director-cinematic failure-modes.md)
    "F1": "Is the face/hair/wardrobe of every person the same person as the reference and stays so to the last frame?",
    "F2": "Does anything move that the shot card says moves (not a slideshow)?",
    "F3": "Any warping or morphing of faces, hands, cloth or props?",
    "F4": "Does the described action happen, as a body mechanic?",
    "F5": "Does the clip end in the stated end state?",
    "F6": "Does the camera do only the one move the card names?",
    "F8": "Any object, costume or building that does not exist in 1914?",
    "F9": "Any extra person or object that appears or disappears?",
    "F10": "Hands, limbs, eyes, teeth right?",
    "F11": "Any text, logo or watermark?",
    "F12": "One key light, same side and colour throughout?",
    "F15": "Does the mouth/voice match, and does the clip speak only its one line?",
    "F19": "Does every prop that must persist stay in the frame?",
}


def card_questions(root: Path, shot: str, kind: str, cards_rel: str = "story/shot_cards_60s.json") -> list[str]:
    p = Path(root) / cards_rel
    if not p.is_file():
        return []
    doc = json.loads(p.read_text(encoding="utf-8"))
    for card in doc.get("cards", []):
        for sh in card.get("shots", []):
            if sh["shot_id"] == shot:
                return [q.split(":", 1)[1].strip() for q in sh.get("acceptance_questions", []) if q.startswith(kind + ":")]
    return []


def sheet(src: Path, kind: str, out_dir: Path, shot: str, frames: int = 8) -> list[str]:
    """Write the contact sheet and one full (middle) frame; returns their paths. Needs ffmpeg for a clip."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    if kind == "image":
        return [str(src)]
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(src)],
                               capture_output=True, text=True, check=True).stdout.strip() or 0)
    sheet_p, full_p = out_dir / f"{shot}_sheet.jpg", out_dir / f"{shot}_mid.jpg"
    fps = max(frames / max(dur, 0.1), 0.1)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-vf",
                    f"fps={fps:.4f},scale=480:-2,drawtext=text='%{{pts\\:hms}}':x=6:y=6:fontcolor=white:box=1:boxcolor=black@0.5,tile=4x{(frames + 3) // 4}",
                    "-frames:v", "1", str(sheet_p)], check=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{dur / 2:.2f}", "-i", str(src), "-frames:v", "1", str(full_p)], check=True)
    return [str(sheet_p), str(full_p)]


def request(root: Path, shot: str, kind: str, path: str, out_dir: Path) -> dict:
    """Build the evidence and the question list the session answers. Returns {questions, evidence}; nothing is recorded yet."""
    root = Path(root)
    p = Path(path) if Path(path).is_absolute() else root / path
    ev = sheet(p, kind, out_dir, shot)
    qs = card_questions(root, shot, kind) + [f"[{c}] {q}" for c, q in CHECKLIST.items()]
    return {"questions": qs, "evidence": ev}


def record(root: Path, shot: str, kind: str, path: str, answers_doc: dict, evidence: list[str] | None = None) -> dict:
    """Write the ``claude`` record from the session's answers; the verdict follows the defects (OB-2), not a free yes."""
    root = Path(root)
    if not evidence:   # a look names the sheet or picture it was made from
        raise ValueError("record needs the evidence file(s) the session looked at (the sheet or the picture)")
    defects = answers_doc.get("defects", [])
    for d in defects:
        RR.action_for_defect(d["code"])   # refuses an unknown code
    states = OB.SS.ShotStates(root)
    left = RR.RETRY_LEFT(states, shot, kind if kind == "image" else "clip") > 0 if kind in ("image", "clip") else True
    rec = OB.build(root, shot, kind, "claude", path, questions=list(answers_doc.get("answers", {})), answers=answers_doc.get("answers", {}),
                   defects=defects, evidence=evidence, note=answers_doc.get("note"), generative_left=left,
                   reviewed={"by": "session", "at": OB._now(), "note": "looked at " + ", ".join(Path(e).name for e in evidence),
                             **OB.evidence_stamp(root, evidence[0])})
    return OB.write(root, rec)
