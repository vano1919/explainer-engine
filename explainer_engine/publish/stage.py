"""``publish stage``: upload an episode's long video and its Shorts as unlisted (or private), never public (D-56).

Order: the publish checklist (PC rules) must have no FAIL and the plan no FAIL -> the token's channel must be the one in
``EXPLAINER_YT_CHANNEL`` -> the long video -> its thumbnail -> each Short, whose description links the long video. Every video
id is written to ``<episode>/publish/youtube_state.json`` the moment the API returns it, keyed by the file's sha256, so a
second run never uploads the same file twice; an interrupted upload resumes from its session (``.sessions.json``, gitignored).
A video with the same title among the channel's latest uploads but not in the state is refused (adopt it with ``--adopt``).

Quota (developers.google.com/youtube/v3/determine_quota_cost, read 2026-10-19, V-47): videos.insert has its own bucket of
100 calls a day at 1 unit; thumbnails.set costs 50 and list calls 1 unit of the 10,000-unit daily bucket.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from explainer_engine.core.store import write_json_atomic
from explainer_engine.publish import plan as P
from explainer_engine.publish.youtube import CHANNEL_ENV, YouTube, YouTubeError
from explainer_engine.qa import publish_check

UPLOADS_PER_DAY, UNITS_PER_DAY = 100, 10_000
UNIT_COST = {"thumbnail": 50, "list": 1}
STUDIO = "https://studio.youtube.com/video/{id}/edit"
WATCH = "https://youtu.be/{id}"


def state_path(episode: Path) -> Path:
    return Path(episode) / "publish" / "youtube_state.json"


def sessions_path(episode: Path) -> Path:
    return Path(episode) / "publish" / ".sessions.json"


def _load(path: Path, default: dict) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def load_state(episode: Path) -> dict:
    return _load(state_path(episode), {"schema": "youtube_state/1", "channel": None, "items": {}, "quota": {}})


def quota_estimate(items: list[dict], with_thumbnail: bool) -> dict:
    uploads = len(items)
    units = UNIT_COST["list"] * (2 + uploads) + (UNIT_COST["thumbnail"] if with_thumbnail else 0)
    return {"uploads": uploads, "uploads_per_day": UPLOADS_PER_DAY, "units": units, "units_per_day": UNITS_PER_DAY}


def _count(state: dict, uploads: int = 0, units: int = 0) -> None:
    day = time.strftime("%Y-%m-%d", time.gmtime(time.time() - 8 * 3600))  # quota resets at midnight Pacific
    q = state["quota"] if state["quota"].get("day") == day else {"day": day, "uploads": 0, "units": 0}
    if q["uploads"] + uploads > UPLOADS_PER_DAY or q["units"] + units > UNITS_PER_DAY:
        raise YouTubeError(f"daily quota: {q['uploads']}/{UPLOADS_PER_DAY} uploads and {q['units']}/{UNITS_PER_DAY} units "
                           "already used today (Pacific time); run again tomorrow")
    q["uploads"] += uploads
    q["units"] += units
    state["quota"] = q


def gate(episode: Path, stage: dict) -> list[str]:
    """Why staging must not start (empty when it may)."""
    pub, doc = P.load_episode(episode)
    problems = [f"{f['rule']} {f['where']}: {f['detail']}" for f in publish_check.check(pub, doc or None)
                if f["severity"] == "FAIL"]
    problems += [f"{f['item']} {f['field']}: {f['detail']}" for f in stage["findings"] if f["severity"] == "FAIL"]
    return problems


def checklist(stage: dict, state: dict) -> list[str]:
    """What the creator checks in Studio before switching anything to public (the API cannot do these)."""
    s = stage["settings"]
    lines = []
    for it in stage["items"]:
        rec = state["items"].get(it["id"]) or {}
        vid = rec.get("video_id")
        where = f"{STUDIO.format(id=vid)}  ({WATCH.format(id=vid)})" if vid else "(not uploaded)"
        lines.append(f"[{it['id']}] {it['body']['snippet']['title']}\n    {where}")
    lines += [
        "",
        "In Studio, for every video above (Details -> Show more):",
        f"  [ ] title, description, tags read back correctly; category {s['category']}, language {s['language']}",
        f"  [ ] audience: 'No, it's not made for kids' (sent: selfDeclaredMadeForKids={s['made_for_kids']})",
        f"  [ ] AI use / altered content: {'Yes' if stage['synthetic_media'] else 'No'} "
        "(sent as containsSyntheticMedia; YouTube Help 14328491)",
        f"  [ ] paid promotion: unticked (the API leaves it at false; it cannot be set on upload)",
        f"  [ ] video location: {s['location']} (the API field is deprecated, V-46: type it in Studio)",
        "  [ ] the long video: thumbnail shown; chapters detected; end screen to the next video",
        "  [ ] each Short: Related video = the long video (Studio only); optional 9:16 thumbnail (Studio on a computer)",
        "  [ ] pinned comment (publish.json pinned_comment) posted after it goes public",
        "  [ ] then, and only then, Visibility -> Public: your click; this tool cannot do it",
    ]
    return lines


def run(episode: Path, *, privacy: str = "unlisted", yes: bool = False, confirm: str = "", video: Path | None = None,
        shorts_dir: Path | None = None, only: set[str] | None = None, adopt: dict | None = None, yt: YouTube | None = None,
        env: dict | None = None, log=print) -> int:
    episode = Path(episode)
    state = load_state(episode)
    long_id = (state["items"].get(P.LONG_ID) or {}).get("video_id")
    stage = P.build(episode, privacy=privacy, video=video, shorts_dir=shorts_dir, long_id=long_id, only=only)
    out_dir = episode / "publish"
    write_json_atomic(out_dir / "youtube_stage.json", stage)
    for f in stage["findings"]:
        log(f"{f['severity']:6} {f['item']} {f['field']}: {f['detail']}")
    todo = [it for it in stage["items"] if not (state["items"].get(it["id"]) or {}).get("video_id")]
    thumb = next((it for it in stage["items"] if it["kind"] == "long" and it.get("thumbnail")), None)
    q = quota_estimate(todo, bool(thumb))
    log(f"plan: {len(stage['items'])} videos as {privacy} ({len(todo)} to upload); quota {q['uploads']}/{q['uploads_per_day']} "
        f"uploads + ~{q['units']}/{q['units_per_day']} units today; written {out_dir / 'youtube_stage.json'}")
    problems = gate(episode, stage)
    for p in problems:
        log(f"BLOCK  {p}")
    if not yes:
        log("dry run: nothing sent. Add --yes --confirm '<who said OK, where>' to upload (never public).")
        log("\n".join(checklist(stage, state)))
        return 1 if problems else 0
    if problems:
        log("refusing to upload: fix the BLOCK lines first")
        return 1
    if not confirm.strip():
        log("refusing: --confirm '<who said OK, where>' records the creator's OK for this staging upload")
        return 1
    env = env if env is not None else __import__("os").environ
    expected = env.get(CHANNEL_ENV, "")
    if not expected:
        log(f"refusing: set {CHANNEL_ENV} to the channel id the videos belong on (a token of another channel is refused)")
        return 1
    if yt is None:
        from explainer_engine.publish.youtube import load_token
        yt = YouTube(load_token(env))
    channel = yt.my_channel()
    _count(state, units=UNIT_COST["list"])
    if channel["id"] != expected:
        log(f"refusing: the token belongs to channel {channel['snippet']['title']!r} ({channel['id']}), not {expected}")
        return 1
    state["channel"] = {"id": channel["id"], "title": channel["snippet"]["title"]}
    uploads = (channel.get("contentDetails") or {}).get("relatedPlaylists", {}).get("uploads")
    remote = yt.recent_titles(uploads) if uploads else {}
    _count(state, units=UNIT_COST["list"])
    write_json_atomic(state_path(episode), state)
    sessions = _load(sessions_path(episode), {})
    ctx = {"episode": episode, "state": state, "yt": yt, "privacy": privacy, "confirm": confirm, "adopt": adopt or {},
           "remote": remote, "sessions": sessions, "log": log}
    longs = [it for it in stage["items"] if it["kind"] == "long"]
    for it in longs:
        _stage_one(ctx, it)
    long_id = (state["items"].get(P.LONG_ID) or {}).get("video_id")
    if long_id and longs:
        _thumbnail(episode, state, yt, thumb, log)
    # the Shorts link the long video: plan them again now that its id is known
    stage = P.build(episode, privacy=privacy, video=video, shorts_dir=shorts_dir, long_id=long_id, only=only)
    write_json_atomic(out_dir / "youtube_stage.json", stage)
    for it in stage["items"]:
        if it["kind"] != "short":
            continue
        if not long_id:
            log(f"{it['id']}: the long video is not staged yet, so its link is missing; skipped")
            continue
        _stage_one(ctx, it)
    log("\nReview checklist (nothing is public):")
    log("\n".join(checklist(stage, state)))
    missing = [it["id"] for it in stage["items"] if not (state["items"].get(it["id"]) or {}).get("video_id")]
    if missing:
        log(f"not staged: {missing}")
    return 1 if missing else 0


def _stage_one(ctx: dict, it: dict) -> None:
    """One video: skipped when this file is already staged, refused when the channel has a same-titled video with no
    record here, else uploaded (resuming a saved session of the same file); its id is saved before anything else."""
    episode, state, yt, log, sessions = ctx["episode"], ctx["state"], ctx["yt"], ctx["log"], ctx["sessions"]
    rec = state["items"].get(it["id"]) or {}
    path = Path(it["file"])
    digest = P.sha256(path)
    title = it["body"]["snippet"]["title"]
    if rec.get("video_id"):
        if rec.get("sha256") != digest:
            log(f"{it['id']}: a DIFFERENT file was already staged as {rec['video_id']}; not uploading again. Delete it in "
                "Studio and remove its entry from youtube_state.json if the new file should replace it")
        else:
            log(f"{it['id']}: already staged as {rec['video_id']} (same file); skipped")
        return
    if ctx["adopt"].get(it["id"]):
        vid = ctx["adopt"][it["id"]]
        log(f"{it['id']}: adopted existing video {vid} (no upload)")
    elif title in ctx["remote"]:
        log(f"{it['id']}: the channel already has {ctx['remote'][title]} titled like this, with no record here; refusing. "
            f"If it is this file, run again with --adopt {it['id']}={ctx['remote'][title]}")
        return
    else:
        _count(state, uploads=1)
        write_json_atomic(state_path(episode), state)
        size = path.stat().st_size
        sess = sessions.get(it["id"])
        offset = 0
        if sess and sess.get("sha256") == digest:
            got = yt.received(sess["uri"], size)
            if got is None:
                sess = None
            else:
                offset = got
                log(f"{it['id']}: resuming at {offset}/{size} bytes")
        if not sess or sess.get("sha256") != digest:
            sess = {"uri": yt.start_session(it["body"], size), "sha256": digest}
            sessions[it["id"]] = sess
            write_json_atomic(sessions_path(episode), sessions)
        log(f"{it['id']}: uploading {path.name} ({size / 1e6:.1f} MB) as {ctx['privacy']}...")
        res = yt.send(sess["uri"], path, size, offset)
        vid = res["id"]
        got_privacy = (res.get("status") or {}).get("privacyStatus")
        if got_privacy and got_privacy != ctx["privacy"]:
            log(f"{it['id']}: NOTE YouTube set it to {got_privacy!r}, not {ctx['privacy']!r} (an unaudited API project may "
                "be held private, V-48); set the visibility in Studio")
        sessions.pop(it["id"], None)
        write_json_atomic(sessions_path(episode), sessions)
    state["items"][it["id"]] = {"video_id": vid, "sha256": digest, "file": path.name, "title": title,
                                "privacy_requested": ctx["privacy"], "confirmed_by": ctx["confirm"],
                                "staged_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    write_json_atomic(state_path(episode), state)
    log(f"{it['id']}: staged -> {STUDIO.format(id=vid)}")


def _thumbnail(episode: Path, state: dict, yt: YouTube, thumb: dict | None, log) -> None:
    if not thumb:
        log("long: no thumbnail in publish.json (thumbnail.file); run `publish thumbnail` or set it in Studio")
        return
    rec = state["items"][P.LONG_ID]
    image = Path(episode) / thumb["thumbnail"]
    if not image.exists():
        log(f"long: thumbnail {image} not found; not set")
        return
    digest = P.sha256(image)
    if rec.get("thumbnail_sha256") == digest:
        return
    _count(state, units=UNIT_COST["thumbnail"])
    try:
        yt.set_thumbnail(rec["video_id"], image)
    except YouTubeError as exc:  # 403: the channel is not verified for custom thumbnails (Help 72431)
        log(f"long: thumbnail NOT set: {exc}")
        write_json_atomic(state_path(episode), state)
        return
    rec.update({"thumbnail": image.name, "thumbnail_sha256": digest})
    write_json_atomic(state_path(episode), state)
    log(f"long: thumbnail set ({image.name})")
