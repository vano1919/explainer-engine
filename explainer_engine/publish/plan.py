"""The staging plan (D-56): what each upload of an episode carries, built from the episode's own files. Pure, no network.

Inputs: ``<episode>/publish.json`` (publish/1: title, description, chapters, disclosure, tags, thumbnail, and per Short an
optional title/description/tags) and ``<episode>/production_script.json`` (the Shorts in order, with their hooks). Output: one item per video (the long one first, then the
Shorts in script order), each with the exact ``videos.insert`` body, and the YouTube rules each field was checked against.

Field rules (developers.google.com/youtube/v3/docs/videos, read 2026-10-19, V-45): title <= 100 characters, description
<= 5000 bytes, neither may contain < or >; tags <= 500 characters counted with the commas and with quotes round a tag that
has a space. ``recordingDetails.location`` is deprecated in the API (V-46), so the US location is a Studio step; paid
promotion defaults to false and is not settable on insert (V-46), so it is left at the default and listed for review.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from explainer_engine.publish.youtube import STAGE_PRIVACY

TITLE_MAX, DESCRIPTION_MAX_BYTES, TAGS_MAX = 100, 5000, 500
CATEGORY_IDS = {"Film & Animation": "1", "Gaming": "20", "People & Blogs": "22", "Comedy": "23", "Entertainment": "24",
                "Education": "27", "Science & Technology": "28"}
DEFAULTS = {"category": "Entertainment", "language": "en", "location": "United States", "made_for_kids": False,
            "paid_promotion": False}
LONG_ID = "long"
LONG_LINK = "https://youtu.be/{id}"
PENDING_LINK = "(the full video's link is added when it is uploaded)"
SHOUTY = re.compile(r"\b[A-Z]{4,}\b")
BANNED_TITLE = re.compile(r"%|\bboring\b", re.I)  # TITLE_THUMBNAIL_SYSTEM title rules
HASHTAG = re.compile(r"(?<!\w)#\w+")
ADULT_TEXT = re.compile(r"(?<!\w)(?:18|21)\s*\+", re.I)  # THUMBNAIL_RULES TN-07: ad guidelines, sexual text
TITLE_TARGET = 70  # THUMBNAIL_RULES TN-14 working target (a hypothesis, so only REVIEW)
HASHTAGS_SHOWN = 3  # Help 6390658: three show above the title, over 60 are all ignored


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def tags_length(tags: list[str]) -> int:
    return len(",".join(f'"{t}"' if " " in t else t for t in tags))


def fit_tags(tags: list[str], limit: int = TAGS_MAX) -> tuple[list[str], list[str]]:
    """The tags that fit YouTube's 500-character count, in order, and the ones left out."""
    kept, dropped = [], []
    for t in (t.strip() for t in tags):
        if not t or t.lower() in {k.lower() for k in kept}:
            continue
        (kept if tags_length(kept + [t]) <= limit else dropped).append(t)
    return kept, dropped


def field_findings(item_id: str, title: str, description: str) -> list[dict]:
    out = []

    def add(sev, field, detail):
        out.append({"item": item_id, "severity": sev, "field": field, "detail": detail})

    if not title.strip():
        add("FAIL", "title", "empty")
    if len(title) > TITLE_MAX:
        add("FAIL", "title", f"{len(title)} characters; YouTube takes {TITLE_MAX}")
    if len(description.encode("utf-8")) > DESCRIPTION_MAX_BYTES:
        add("FAIL", "description", f"{len(description.encode('utf-8'))} bytes; YouTube takes {DESCRIPTION_MAX_BYTES}")
    for field, text in (("title", title), ("description", description)):
        if "<" in text or ">" in text:
            add("FAIL", field, "contains < or >, which YouTube refuses")
    if SHOUTY.search(title):
        add("REVIEW", "title", f"ALL-CAPS word {SHOUTY.search(title).group()!r} (TITLE_THUMBNAIL_SYSTEM: no all caps)")
    if BANNED_TITLE.search(title):
        add("REVIEW", "title", "'%' or 'boring' in the title (TITLE_THUMBNAIL_SYSTEM)")
    if TITLE_TARGET < len(title) <= TITLE_MAX:
        add("REVIEW", "title", f"{len(title)} characters; feeds cut long titles, target about {TITLE_TARGET} (TN-14)")
    tags = HASHTAG.findall(description)
    if len(tags) > 60:
        add("FAIL", "description", f"{len(tags)} hashtags; over 60 are all ignored (Help 6390658)")
    elif item_id == LONG_ID and len(tags) > HASHTAGS_SHOWN:
        add("REVIEW", "description", f"{len(tags)} hashtags; only {HASHTAGS_SHOWN} show above the title (TN-16)")
    for field, text in (("title", title), ("description", description)):
        if ADULT_TEXT.search(text):
            add("REVIEW", field, "'18+' or '21+' wording; the ad guidelines treat it as adult (TN-07)")
    return out


def chapters_block(chapters: list[dict]) -> str:
    return "\n".join(f"{c['t']} {c['title']}" for c in chapters)


def long_description(pub: dict) -> str:
    """publish.json's description, then the chapters (YouTube reads them from the description), unless already there."""
    text = pub["description"].rstrip()
    chapters = pub.get("chapters") or []
    if chapters and chapters_block(chapters) not in text:
        text += "\n\nChapters\n" + chapters_block(chapters)
    return text


def hashtags(tags: list[str], n: int = 2) -> str:
    words = ["#" + re.sub(r"[^A-Za-z0-9]", "", t.title()) for t in tags[:n]]
    return " ".join(["#shorts"] + [w for w in words if len(w) > 1])


def short_title(short: dict) -> str:
    title = (short.get("title") or short.get("hook") or "").strip()
    return title if len(title) <= TITLE_MAX else title[: TITLE_MAX - 1].rsplit(" ", 1)[0] + "…"


def short_description(short: dict, long_title: str, long_link: str, tags: list[str], note: str) -> str:
    lines = [(short.get("description") or short.get("hook") or "").strip(), "",
             f"Full video: {long_title}", long_link]
    if note:
        lines += ["", note]
    lines += ["", hashtags(tags)]
    return "\n".join(lines).strip()


def body(title: str, description: str, tags: list[str], cfg: dict, synthetic: bool, privacy: str) -> dict:
    if privacy not in STAGE_PRIVACY:
        raise ValueError(f"privacy {privacy!r}: staging is {STAGE_PRIVACY} only (D-56)")
    return {
        "snippet": {"title": title, "description": description, "tags": tags,
                    "categoryId": CATEGORY_IDS[cfg["category"]], "defaultLanguage": cfg["language"],
                    "defaultAudioLanguage": cfg["language"]},
        "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": bool(cfg["made_for_kids"]),
                   "containsSyntheticMedia": synthetic, "embeddable": True, "license": "youtube"},
    }


def load_episode(episode: Path) -> tuple[dict, dict]:
    episode = Path(episode)
    pub_path = episode / "publish.json"
    if not pub_path.exists():
        raise FileNotFoundError(f"{pub_path} is missing: write the episode's publish/1 package first "
                                "(docs/QA_SPECIFICATION.md PC rules)")
    pub = json.loads(pub_path.read_text(encoding="utf-8"))
    script_path = episode / "production_script.json"
    doc = json.loads(script_path.read_text(encoding="utf-8")) if script_path.exists() else {}
    return pub, doc


def build(episode: Path, *, privacy: str = "unlisted", video: Path | None = None, shorts_dir: Path | None = None,
          long_id: str | None = None, only: set[str] | None = None) -> dict:
    """The staging plan of an episode. ``long_id`` (the uploaded long video) fills the Shorts' links."""
    episode = Path(episode)
    pub, doc = load_episode(episode)
    yt = {**DEFAULTS, **(pub.get("youtube") or {}), "made_for_kids": pub.get("audience") == "made_for_kids"}
    if yt["category"] not in CATEGORY_IDS:
        raise ValueError(f"youtube.category {yt['category']!r}; one of {sorted(CATEGORY_IDS)}")
    synthetic = (pub.get("disclosure") or {}).get("decision") == "disclose"
    note = yt.get("ai_note") or ""
    tags, dropped = fit_tags(pub.get("tags") or [])
    files = pub.get("files") or {}
    video = Path(video) if video else episode / files.get("video", "render/video.mp4")
    shorts_dir = Path(shorts_dir) if shorts_dir else episode / files.get("shorts_dir", "render/shorts")
    findings = []
    if dropped:
        findings.append({"item": LONG_ID, "severity": "REVIEW", "field": "tags",
                         "detail": f"left out to fit {TAGS_MAX} characters: {dropped}"})
    if not tags:
        findings.append({"item": LONG_ID, "severity": "REVIEW", "field": "tags", "detail": "no tags in publish.json"})
    items = []
    desc = long_description(pub)
    items.append({"id": LONG_ID, "kind": "long", "file": str(video),
                  "thumbnail": (pub.get("thumbnail") or {}).get("file"),
                  "body": body(pub["title"], desc, tags, yt, synthetic, privacy)})
    findings += field_findings(LONG_ID, pub["title"], desc)
    link = LONG_LINK.format(id=long_id) if long_id else PENDING_LINK
    overrides = {s["id"]: s for s in pub.get("shorts") or []}
    for short in doc.get("shorts") or []:
        sid = short["id"]
        short = {**short, **{k: v for k, v in (overrides.get(sid) or {}).items() if k in ("title", "description", "tags")}}
        title = short_title(short)
        stags, _ = fit_tags(list(short.get("tags") or []) + tags + ["shorts"])
        sdesc = short_description(short, pub["title"], link, stags, note if synthetic else "")
        items.append({"id": sid, "kind": "short", "file": str(shorts_dir / f"{sid}.mp4"), "thumbnail": None,
                      "body": body(title, sdesc, stags, yt, synthetic, privacy)})
        findings += field_findings(sid, title, sdesc)
    if only:
        items = [i for i in items if i["id"] in only]
        findings = [f for f in findings if f["item"] in only]
    for it in items:
        if not Path(it["file"]).exists():
            findings.append({"item": it["id"], "severity": "FAIL", "field": "file", "detail": f"{it['file']} not found"})
    return {"schema": "youtube_stage/1", "episode": str(episode), "privacy": privacy, "settings": yt,
            "synthetic_media": synthetic, "items": items, "findings": findings}
