"""Where free sounds may come from, and what each licence allows (the sound library's licence policy, LIB-03..LIB-06 in
docs/SOUND_LIBRARY.md; the creator's order 2026-11-13: library, then free licence-checked sources, then ElevenLabs).

Two things live here:

* ``LICENCES``: every licence the library meets, with what it allows (commercial use, modification, standalone
  redistribution, attribution, share-alike, AI processing) and the verdict for a monetised YouTube channel: ``verified``
  (production-ready), ``quarantine`` (kept, never played: the terms are unclear or unread) or ``rejected`` (never stored for
  production: NC, SA on synchronisation, GPL). ``verdict`` is the one function the importer and the catalog ask.
* page readers (``read_page``): read ONE public asset page and return what it says about the asset (title, author, licence
  as written on the page, files). The importer re-reads the page at import time, so a licence is recorded as read on that
  day, never copied from memory. Readers fetch one page per call (no crawling, no mass download: Mixkit's User Terms 9 forbid
  scripted mass downloads; OpenGameArt and Incompetech are read item by item too).

Sources that this cloud container cannot reach are listed in ``BLOCKED`` with what was seen (2026-11-13), so a later run
knows why they are absent instead of guessing.
"""
from __future__ import annotations

import html
import json
import re
import subprocess
import sys
import urllib.parse

UA = "Mozilla/5.0 (compatible; sound-catalog/1.0)"

# licence id -> what it allows. "sync_adaptation": a sound synced to moving pictures is an adaptation (CC 4.0 s.1(a)), so a
# share-alike licence would bind the whole video: rejected. Pages read 2026-11-13 (urls below).
LICENCES: dict[str, dict] = {
    "cc0": {"name": "CC0 1.0", "url": "https://creativecommons.org/publicdomain/zero/1.0/", "commercial": True,
            "modification": True, "redistribution": True, "attribution": False, "share_alike": False, "verdict": "verified"},
    "public_domain": {"name": "Public Domain", "url": "https://creativecommons.org/publicdomain/mark/1.0/", "commercial": True,
                      "modification": True, "redistribution": True, "attribution": False, "share_alike": False,
                      "verdict": "verified"},
    "cc_by_3": {"name": "CC BY 3.0", "url": "https://creativecommons.org/licenses/by/3.0/", "commercial": True,
                "modification": True, "redistribution": True, "attribution": True, "share_alike": False, "verdict": "verified"},
    "cc_by_4": {"name": "CC BY 4.0", "url": "https://creativecommons.org/licenses/by/4.0/", "commercial": True,
                "modification": True, "redistribution": True, "attribution": True, "share_alike": False, "verdict": "verified"},
    "oga_by_3": {"name": "OGA-BY 3.0", "url": "https://static.opengameart.org/OGA-BY-3.0.txt", "commercial": True,
                 "modification": True, "redistribution": True, "attribution": True, "share_alike": False, "verdict": "verified"},
    "oga_by_4": {"name": "OGA-BY 4.0", "url": "https://static.opengameart.org/OGA-BY-4.0.txt", "commercial": True,
                 "modification": True, "redistribution": True, "attribution": True, "share_alike": False, "verdict": "verified"},
    "mixkit_sfx_free": {"name": "Mixkit Sound Effects Free License", "url": "https://mixkit.co/license/#sfxFree",
                        "commercial": True, "modification": True, "redistribution": False, "attribution": False,
                        "share_alike": False, "verdict": "verified",
                        "terms": "use in YouTube videos and commercial projects; never redistribute the item on its own, as stock, in "
                                 "a tool or template; never claim it or register it on a rights-management service (Content ID); "
                                 "User Terms 9: no scripted mass download (read 2026-11-13)"},
    "mixkit_music_free": {"name": "Mixkit Stock Music Free License", "url": "https://mixkit.co/license/#musicFree",
                          "commercial": True, "modification": False, "redistribution": False, "attribution": False,
                          "share_alike": False, "verdict": "verified",
                          "terms": "YouTube videos allowed; NOT CDs/DVDs, TV/radio broadcast or video games; no remix or music-only "
                                   "track; no Content ID registration; claims go to team@mixkit.co (read 2026-11-13)"},
    "pixabay_content": {"name": "Pixabay Content License", "url": "https://pixabay.com/service/license-summary/",
                        "commercial": True, "modification": True, "redistribution": False, "attribution": False,
                        "share_alike": False, "verdict": "quarantine",
                        "terms": "not re-read: pixabay.com answers this container with a bot challenge (2026-11-13)"},
    "sonniss_gdc_2": {"name": "Sonniss GDC Bundle License 2.0", "url": "https://sonniss.com/gdc-bundle-license/",
                      "commercial": True, "modification": True, "redistribution": False, "attribution": False,
                      "share_alike": False, "ai_processing": False, "verdict": "quarantine",
                      "terms": "from the creator's brief (2026-11-13): commercial synchronisation allowed; no standalone "
                               "redistribution; no upload to AI systems for training, adaptation or AI-based analysis or "
                               "classification; private store only. Not re-read here: sonniss.com answers with a bot challenge"},
    "youtube_audio_library": {"name": "YouTube Audio Library", "url": "https://studio.youtube.com/channel/UC/music",
                              "commercial": True, "modification": True, "redistribution": False, "attribution": None,
                              "share_alike": False, "verdict": "quarantine",
                              "terms": "per track (attribution or not); needs the creator's YouTube Studio sign-in"},
    "zapsplat_standard": {"name": "Zapsplat Standard License", "url": "https://www.zapsplat.com/license-type/standard-license/",
                          "commercial": True, "modification": True, "redistribution": False, "attribution": True,
                          "share_alike": False, "verdict": "quarantine",
                          "terms": "free (Basic) downloads need attribution; needs an account; zapsplat.com answers with a bot challenge"},
    "elevenlabs_output": {"name": "ElevenLabs output (paid plan)", "url": "https://elevenlabs.io/terms-of-use",
                          "commercial": True, "modification": True, "redistribution": False, "attribution": False,
                          "share_alike": False, "verdict": "verified",
                          "terms": "V-59: inside video productions, commercially on a paid plan; never standalone or in a sound library"},
    "own_procedural": {"name": "Own procedural (numpy)", "url": "", "commercial": True, "modification": True,
                       "redistribution": True, "attribution": False, "share_alike": False, "verdict": "verified"},
    "generated_unverified": {"name": "Generated, provider terms not checked", "url": "", "commercial": None,
                             "modification": None, "redistribution": False, "attribution": False, "share_alike": False,
                             "verdict": "quarantine"},
    "cc_by_nc": {"name": "CC BY-NC", "url": "https://creativecommons.org/licenses/by-nc/4.0/", "commercial": False,
                 "modification": True, "redistribution": True, "attribution": True, "share_alike": False, "verdict": "rejected"},
    "cc_by_sa": {"name": "CC BY-SA", "url": "https://creativecommons.org/licenses/by-sa/4.0/", "commercial": True,
                 "modification": True, "redistribution": True, "attribution": True, "share_alike": True, "verdict": "rejected",
                 "terms": "a sound synced to video is an adaptation (CC BY-SA 4.0 s.1(a)): the whole video would fall under SA"},
    "gpl": {"name": "GPL", "url": "https://www.gnu.org/licenses/gpl-3.0.html", "commercial": True, "modification": True,
            "redistribution": True, "attribution": True, "share_alike": True, "verdict": "rejected",
            "terms": "copyleft for software; unclear for media in a video"},
    "bbc_remarc": {"name": "BBC RemArc", "url": "https://sound-effects.bbcrewind.co.uk/licensing", "commercial": False,
                   "modification": True, "redistribution": False, "attribution": True, "share_alike": False,
                   "verdict": "rejected", "terms": "personal, educational or research only: never on a monetised channel"},
    "unknown": {"name": "unknown", "url": "", "commercial": None, "modification": None, "redistribution": None,
                "attribution": None, "share_alike": None, "verdict": "quarantine"},
}
# how licence names are written on source pages -> our id
_NAMES = {"cc0": "cc0", "creative commons zero": "cc0", "public domain": "public_domain", "cc-by 3.0": "cc_by_3",
          "cc by 3.0": "cc_by_3", "attribution 3.0": "cc_by_3", "cc-by 4.0": "cc_by_4", "cc by 4.0": "cc_by_4",
          "attribution 4.0": "cc_by_4", "oga-by 3.0": "oga_by_3", "oga-by 4.0": "oga_by_4", "cc-by-sa 3.0": "cc_by_sa",
          "cc-by-sa 4.0": "cc_by_sa", "gpl 2.0": "gpl", "gpl 3.0": "gpl", "lgpl 2.1": "gpl", "lgpl 3.0": "gpl",
          "cc-by-nc": "cc_by_nc", "noncommercial": "cc_by_nc", "sampling plus": "unknown", "personal use only": "cc_by_nc"}
# preference when a page offers several licences (the asset may be used under any one of them)
PREFERENCE = ("cc0", "public_domain", "cc_by_4", "cc_by_3", "oga_by_4", "oga_by_3")

BLOCKED = {
    "freesound": "freesound.org answers HTTP 403 (empty body) to this container, API included; originals also need OAuth2 "
                 "(2026-11-13)",
    "sonniss": "sonniss.com answers a Cloudflare bot challenge; the bundles are tens of GB; licence 2.0 forbids AI-based "
               "analysis, so they stay out of this AI-run workflow until the creator clarifies (2026-11-13)",
    "pixabay": "pixabay.com answers a bot challenge; its API has no sound effects (2026-11-13)",
    "zapsplat": "zapsplat.com answers a bot challenge and downloads need an account (2026-11-13)",
    "youtube_audio_library": "needs the creator's signed-in YouTube Studio (2026-11-13)",
    "wikimedia_commons": "the Commons API answers HTTP 429 (rate limit for this shared cloud address) (2026-11-13)",
    "freepd": "freepd.com is closed (site notice, 2025)",
    "bigsoundbank": "bigsoundbank.com answers HTTP 403 (2026-11-13)",
}


def licence_id(written: str) -> str:
    """Our id for a licence as a page writes it ('CC-BY 3.0', 'CC0', 'Creative Commons Zero (CC0)')."""
    w = (written or "").strip().lower()
    for key in sorted(_NAMES, key=len, reverse=True):
        if key in w:
            return _NAMES[key]
    return "unknown"


def best_of(ids: list[str]) -> str:
    """The licence to use when a page offers several: the most permissive accepted one, else the first."""
    for pref in PREFERENCE:
        if pref in ids:
            return pref
    return ids[0] if ids else "unknown"


# The creator's licence scope (2026-11-13 07:24 UTC: "licence does not interest me, quality does; licence concerns only the
# background music"; 07:49 UTC card "yes, BBC too"): a sound effect is taken by quality, its licence recorded as information;
# music keeps the licence gate. A temporary exception to CLAUDE.md invariant 5 for sound effects, by his recorded word.
SFX_LICENCE_RULE = "creator 2026-11-13: sound effects by quality, licence recorded only (music keeps the licence gate)"
SFX_EXCEPTIONS = {"bbc_remarc": "creator card 2026-11-13 07:49 UTC (yes, BBC too)"}


def verdict(lic: str, *, ai_workflow: bool = True, use: str = "music") -> str:
    """``verified`` | ``quarantine`` | ``rejected`` for a monetised YouTube channel. ``use="music"`` (the default, the strict
    reading) judges the licence; ``use="sfx"`` follows the creator's 2026-11-13 rule: a licence on ``SFX_EXCEPTIONS`` is
    verified for an effect; any other licence keeps its verdict. A licence that forbids AI processing is quarantine inside
    this AI-run workflow (the creator's Sonniss rule)."""
    spec = LICENCES.get(lic, LICENCES["unknown"])
    if use == "sfx" and lic in SFX_EXCEPTIONS:
        return "verified"
    if ai_workflow and spec.get("ai_processing") is False and spec["verdict"] == "verified":
        return "quarantine"
    return spec["verdict"]


def licence_record(lic: str, *, creator: str, source_url: str, read_on: str, attribution_text: str | None = None,
                   use: str = "music") -> dict:
    """The licence fields every library item carries (LIB-04)."""
    spec = LICENCES.get(lic, LICENCES["unknown"])
    rec = {"type": lic, "url": spec["url"], "source_url": source_url, "creator": creator,
           "attribution_required": bool(spec["attribution"]), "attribution_text": attribution_text,
           "commercial_use": spec["commercial"], "modification": spec["modification"],
           "redistribution": spec["redistribution"], "ai_processing": spec.get("ai_processing", True),
           "read_on": read_on, "production": verdict(lic, use=use), "use": use}
    if use == "sfx" and lic in SFX_EXCEPTIONS:
        rec["exception"] = SFX_EXCEPTIONS[lic] + "; " + SFX_LICENCE_RULE
    return rec


def _get(url: str) -> str:
    r = subprocess.run(["curl", "-sL", "-m", "40", "-A", UA, url], capture_output=True, text=True, errors="ignore")
    return r.stdout


def _text(fragment: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def read_opengameart(url: str, page: str | None = None) -> dict:
    t = page if page is not None else _get(url)
    title = _text((re.findall(r"<title>([^<|]*)", t) or ["?"])[0])
    author = _text((re.findall(r"field-name-author-submitter.*?<a href=\"/users/[^\"]*\">([^<]+)", t, re.S) or ["?"])[0])
    written = [_text(x) for x in re.findall(r"class='license-name'>([^<]+)", t)]
    files = [{"name": urllib.parse.unquote(n), "url": u, "bytes": int(b)} for u, b, n in
             re.findall(r'<a href="(https://opengameart.org/sites/default/files/[^"]+)" type="[^";]+; length=(\d+)"[^>]*download="([^"]+)"', t)]
    tags = [_text(x) for x in re.findall(r'field_art_tags_tid=[^"]*"[^>]*>([^<]+)</a>', t)]
    body = re.findall(r'<meta name="description" content="([^"]*)"', t)
    ids = [licence_id(w) for w in written]
    return {"source": "opengameart", "page": url, "title": title, "creator": author, "licences_written": written,
            "licence": best_of(ids), "files": files, "tags": tags, "description": html.unescape(body[0])[:400] if body else ""}


def read_mixkit(url: str, page: str | None = None) -> dict:
    """A Mixkit sound-effect category page (https://mixkit.co/free-sound-effects/<cat>/): its items with title, length, tags
    and the official download (the download modal's WAV, ``assets.mixkit.co/active_storage/sfx/<id>/<id>.wav``)."""
    t = page if page is not None else _get(url)
    items = []
    for m in re.finditer(r'data-audio-player-item-id-value="(\d+)".*?<h2 class="item-grid-card__title">(.*?)</h2>(.*?)'
                         r'data-test-id="duration">\s*([0-9:]+)', t, re.S):
        iid, title, mid, dur = m.groups()
        tags = [_text(x).lower() for x in re.findall(r'class="meta-links__link"[^>]*>([^<]+)</a>', mid)]
        mm, ss = (dur.split(":") + ["0"])[:2]
        items.append({"id": iid, "name": _text(title), "seconds": int(mm) * 60 + int(ss), "tags": tags,
                      "url": f"https://assets.mixkit.co/active_storage/sfx/{iid}/{iid}.wav"})
    return {"source": "mixkit", "page": url, "creator": "Mixkit (Envato)", "licences_written": ["Mixkit Sound Effects Free License"],
            "licence": "mixkit_sfx_free", "files": items}


def read_incompetech(title: str, catalog: list[dict]) -> dict:
    """An Incompetech piece from its public catalogue (pieces.json): CC BY 4.0 with the credit the FAQ gives."""
    p = next((x for x in catalog if x.get("title") == title), None)
    if p is None:
        raise KeyError(f"Incompetech has no piece titled {title!r}")
    fn = p["filename"]
    credit = (f"\"{title}\" Kevin MacLeod (incompetech.com) Licensed under Creative Commons: By Attribution 4.0 "
              "https://creativecommons.org/licenses/by/4.0/")
    return {"source": "incompetech", "page": "https://incompetech.com/music/royalty-free/index.html?isrc=" + str(p.get("isrc") or ""),
            "title": title, "creator": "Kevin MacLeod", "licences_written": ["Creative Commons: By Attribution 4.0"],
            "licence": "cc_by_4", "attribution_text": credit,
            "files": [{"name": fn, "url": "https://incompetech.com/music/royalty-free/mp3-royaltyfree/" + urllib.parse.quote(fn)}],
            "tags": [w.strip().lower() for w in (p.get("feel") or "").split(",") if w.strip()],
            "description": p.get("description") or "", "instruments": p.get("instruments") or "", "bpm": p.get("bpm"),
            "length": p.get("length")}


def incompetech_catalog() -> list[dict]:
    return json.loads(_get("https://incompetech.com/music/royalty-free/pieces.json"))


BBC_API = "https://sound-effects-api.bbcrewind.co.uk/api/sfx/search"
BBC_MEDIA = "https://sound-effects-media.bbcrewind.co.uk/wav/{id}.wav"
BBC_CREDIT = "Contains sound effects from BBC Sound Effects (https://sound-effects.bbcrewind.co.uk), \u00a9 copyright BBC"


def search_bbc(query: str, size: int = 10, start: int = 0) -> list[dict]:
    """The BBC Sound Effects archive's own public search (the site's API): id, description, duration, channels, rate, CD."""
    body = json.dumps({"criteria": {"from": start, "size": size, "query": query}})
    r = subprocess.run(["curl", "-sS", "-m", "40", "-X", "POST", BBC_API, "-H", "content-type: application/json", "-A", UA,
                        "-d", body], capture_output=True, text=True)
    out = []
    for x in json.loads(r.stdout or "{}").get("results", []):
        t = x.get("technicalMetadata") or {}
        out.append({"id": x["id"], "description": x.get("description", ""), "seconds": float(t.get("duration") or 0),
                    "channels": int(t.get("channels") or 0), "sample_rate": int(t.get("sample_rate") or 0),
                    "bits": t.get("bits_per_sample"), "cd": (x.get("additionalMetadata") or {}).get("cdName", ""),
                    "tags": x.get("tags", []), "wav_bytes": int((x.get("fileSizes") or {}).get("wavFileSize") or 0)})
    return out


def read_bbc(item: str) -> dict:
    """One BBC archive item: its description (from the search by id), the WAV's url, the RemArc licence and the credit."""
    hit = next((h for h in search_bbc(item, size=5) if h["id"] == item), None)
    return {"source": "bbc", "page": f"https://sound-effects.bbcrewind.co.uk/search?q={item}", "creator": "BBC",
            "title": (hit or {}).get("description") or item, "licences_written": ["RemArc Licence"], "licence": "bbc_remarc",
            "files": [{"name": f"{item}.wav", "url": BBC_MEDIA.format(id=item), "bytes": (hit or {}).get("wav_bytes")}],
            "meta": hit, "attribution_text": BBC_CREDIT}


def read_page(source: str, url: str) -> dict:
    if source == "opengameart":
        return read_opengameart(url)
    if source == "mixkit":
        return read_mixkit(url)
    raise ValueError(f"no page reader for {source!r} (blocked sources: {', '.join(sorted(BLOCKED))})")


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="read one public asset page and print what it says (licence, author, files)")
    ap.add_argument("source", choices=["opengameart", "mixkit", "incompetech", "bbc", "bbc-search", "blocked"])
    ap.add_argument("what", nargs="?", default="")
    a = ap.parse_args(argv)
    if a.source == "blocked":
        print(json.dumps(BLOCKED, indent=1))
        return 0
    if a.source == "bbc-search":
        for h in search_bbc(a.what, size=15):
            print(f"{h['id']}  {h['seconds']:7.1f} s  ch{h['channels']}  {h['description'][:100]}  [{h['cd']}]")
        return 0
    rec = (read_incompetech(a.what, incompetech_catalog()) if a.source == "incompetech" else read_bbc(a.what)
           if a.source == "bbc" else read_page(a.source, a.what))
    rec["verdict"] = verdict(rec["licence"], use="sfx" if a.source == "bbc" else "music")
    print(json.dumps(rec, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
