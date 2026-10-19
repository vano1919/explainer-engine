"""D-57: YouTube staging against a fake API (no network): never public, idempotent, resumable, quota-aware, channel-checked."""
import base64
import json
from pathlib import Path

import pytest

from explainer_engine.publish import plan as P
from explainer_engine.publish import stage as S
from explainer_engine.publish import thumbnail as T
from explainer_engine.publish.__main__ import main as cli
from explainer_engine.publish.youtube import NotStaging, YouTube, YouTubeError, load_token

CHANNEL = "UC_explainer"
PUB = {
    "schema": "publish/1", "title": "Syndicate Wars: Four Crime Bosses in GTA 6's Leonida",
    "description": "Four bosses, one city. Sources: https://example.org/claims", "duration_s": 600,
    "chapters": [{"t": "0:00", "title": "Four bosses"}, {"t": "2:20", "title": "Round 1"}, {"t": "5:00", "title": "Round 2"}],
    "audience": "not_made_for_kids",
    "disclosure": {"decision": "not_needed", "reason": "clearly drawn 2D fiction", "photoreal_pictures": False,
                   "real_person_realistic": False, "real_event_altered": False, "ai_music_main": False},
    "mid_roll": "off", "self_certification_answered": True, "approval": None,
    "tags": ["GTA 6", "Al Capone", "crime boss"],
    "youtube": {"category": "Entertainment", "language": "en", "location": "United States"},
    "thumbnail": {"file": "publish/thumbnail.jpg", "text": "WHO FALLS FIRST?", "concept": "four bosses on a neon street"},
    "shorts": [{"id": "SH02", "seconds": 40, "audio": ["library"], "title": "The boss who never raised his voice"}],
}
SCRIPT = {"segments": [], "shorts": [{"id": "SH01", "hook": "Could one line in a ledger bring down Al Capone?"},
                                     {"id": "SH02", "hook": "Why did Vito never shout?"}]}


def episode(tmp_path: Path, pub: dict | None = None) -> Path:
    ep = tmp_path / "ep"
    (ep / "render" / "shorts").mkdir(parents=True)
    (ep / "publish.json").write_text(json.dumps(pub or PUB), encoding="utf-8")
    (ep / "production_script.json").write_text(json.dumps(SCRIPT), encoding="utf-8")
    (ep / "render" / "video.mp4").write_bytes(b"L" * 3000)
    for sid in ("SH01", "SH02"):
        (ep / "render" / "shorts" / f"{sid}.mp4").write_bytes(sid.encode() * 500)
    return ep


class FakeAPI:
    """A tiny YouTube: token, channels, playlistItems, resumable uploads, thumbnails. Records every request."""

    def __init__(self, channel=CHANNEL, existing=None, drop_first_put=False):
        self.calls, self.bodies, self.sessions, self.n = [], [], {}, 0
        self.channel, self.existing, self.drop = channel, existing or {}, drop_first_put

    def __call__(self, method, url, headers, body=None):
        self.calls.append((method, url.split("?")[0]))
        if "oauth2" in url:
            return 200, {}, json.dumps({"access_token": "a"}).encode()
        if "/channels" in url:
            return 200, {}, json.dumps({"items": [{"id": self.channel, "snippet": {"title": "Crossworld"},
                                                   "contentDetails": {"relatedPlaylists": {"uploads": "UU1"}}}]}).encode()
        if "/playlistItems" in url:
            items = [{"snippet": {"title": t, "resourceId": {"videoId": v}}} for t, v in self.existing.items()]
            return 200, {}, json.dumps({"items": items}).encode()
        if "/upload/youtube/v3/videos" in url:
            meta = json.loads(body)
            self.bodies.append(meta)
            self.n += 1
            uri = f"https://upload.example/s{self.n}"
            self.sessions[uri] = {"meta": meta, "size": int(headers["X-Upload-Content-Length"]), "got": 0}
            return 200, {"location": uri}, b""
        if url in self.sessions:
            s = self.sessions[url]
            if body == b"":  # status query
                return (308, {"range": f"bytes=0-{s['got'] - 1}"} if s["got"] else {}, b"")
            f, length = body
            data = f.read(length)
            if self.drop:
                self.drop = False
                s["got"] += len(data) // 2
                raise ConnectionResetError("dropped")
            s["got"] += len(data)
            assert s["got"] == s["size"]
            vid = f"vid{list(self.sessions).index(url) + 1}"
            return 201, {}, json.dumps({"id": vid, "status": {"privacyStatus": s["meta"]["status"]["privacyStatus"]}}).encode()
        if "/thumbnails/set" in url:
            return 200, {}, b"{}"
        raise AssertionError(url)


def token():
    return {"client_id": "c", "client_secret": "s", "refresh_token": "r"}


def go(ep, api, **kw):
    lines = []
    rc = S.run(ep, yes=True, confirm="vano1919 in the project thread", yt=YouTube(token(), api, sleep=lambda s: None),
               env={"EXPLAINER_YT_CHANNEL": CHANNEL}, log=lines.append, **kw)
    return rc, "\n".join(lines)


def test_plan_fills_every_field_and_never_public(tmp_path):
    stage = P.build(episode(tmp_path))
    long, sh1, sh2 = stage["items"]
    assert long["body"]["status"] == {"privacyStatus": "unlisted", "selfDeclaredMadeForKids": False,
                                      "containsSyntheticMedia": False, "embeddable": True, "license": "youtube"}
    assert long["body"]["snippet"]["categoryId"] == "24" and long["body"]["snippet"]["defaultLanguage"] == "en"
    assert "0:00 Four bosses" in long["body"]["snippet"]["description"]  # chapters go into the description
    assert sh1["body"]["snippet"]["title"] == SCRIPT["shorts"][0]["hook"]
    assert sh2["body"]["snippet"]["title"] == "The boss who never raised his voice"  # publish.json override
    assert P.PENDING_LINK in sh1["body"]["snippet"]["description"]
    assert "#shorts" in sh1["body"]["snippet"]["description"]
    assert all("publishAt" not in it["body"]["status"] for it in stage["items"])
    with pytest.raises(ValueError):
        P.build(episode(tmp_path / "x"), privacy="public")


def test_the_client_refuses_public_and_scheduling():
    yt = YouTube(token(), FakeAPI())
    with pytest.raises(NotStaging):
        yt.start_session({"snippet": {}, "status": {"privacyStatus": "public"}}, 10)
    with pytest.raises(NotStaging):
        yt.start_session({"snippet": {}, "status": {"privacyStatus": "private", "publishAt": "2026-10-20T00:00:00Z"}}, 10)
    with pytest.raises(SystemExit):
        cli(["stage", "ep", "--privacy", "public"])


def test_youtube_field_limits():
    assert P.fit_tags(["a b", "x" * 492, "yy"])[1] == ["yy"]  # '"a b",' counts the quotes and the comma
    found = P.field_findings("long", "x" * 101 + "<", "d" * 5001)
    assert {(f["field"], f["severity"]) for f in found} == {("title", "FAIL"), ("description", "FAIL")}
    assert any(f["severity"] == "REVIEW" for f in P.field_findings("long", "WHO wins EVERYTHING", ""))


def test_package_findings_follow_the_thumbnail_rules():
    def sev(item, title, desc):
        return {(f["severity"], f["field"]) for f in P.field_findings(item, title, desc)}
    assert ("REVIEW", "title") in sev("long", "t" * 80, "")
    assert not sev("long", "t" * 60, "")
    assert ("REVIEW", "description") in sev("long", "ok", "#a #b #c #d")
    assert not sev("long", "ok", "#a #b #c")
    assert not sev("s1", "ok", "#shorts #a #b #c #d")
    assert ("FAIL", "description") in sev("long", "ok", " ".join(f"#t{i}" for i in range(61)))
    assert ("REVIEW", "title") in sev("long", "Only 18+ may watch", "")
    assert not sev("long", "Chapter 18 and 21 plus", "")


def test_dry_run_sends_nothing_and_prints_checklist(tmp_path):
    ep = episode(tmp_path)
    lines = []
    rc = S.run(ep, log=lines.append, yt=YouTube(token(), lambda *a: pytest.fail("network in a dry run")))
    out = "\n".join(lines)
    assert rc == 0 and "dry run" in out and "Visibility -> Public: your click" in out
    assert "video location: United States" in out and "not made for kids" in out
    assert json.loads((ep / "publish" / "youtube_stage.json").read_text())["items"][0]["id"] == "long"


def test_stage_uploads_long_first_then_shorts_with_its_link_and_never_twice(tmp_path):
    ep = episode(tmp_path)
    (ep / "publish").mkdir()
    (ep / "publish" / "thumbnail.jpg").write_bytes(b"jpg")
    api = FakeAPI()
    rc, out = go(ep, api)
    assert rc == 0, out
    assert [b["snippet"]["title"] for b in api.bodies][0] == PUB["title"]
    assert all(b["status"]["privacyStatus"] == "unlisted" for b in api.bodies)
    assert "https://youtu.be/vid1" in api.bodies[1]["snippet"]["description"]
    assert ("POST", "https://www.googleapis.com/upload/youtube/v3/thumbnails/set") not in api.calls  # the creator's job
    state = json.loads(S.state_path(ep).read_text())
    assert {k: v["video_id"] for k, v in state["items"].items()} == {"long": "vid1", "SH01": "vid2", "SH02": "vid3"}
    assert "thumbnail" not in state["items"]["long"]
    assert state["quota"]["uploads"] == 3
    rc, out = go(ep, api)  # again: nothing new is sent
    assert rc == 0 and len(api.bodies) == 3 and out.count("already staged") == 3


def test_thumbnail_is_sent_only_when_publish_json_allows_it(tmp_path):
    ep = episode(tmp_path, pub={**PUB, "thumbnail": {**PUB["thumbnail"], "upload": True}})
    (ep / "publish").mkdir()
    (ep / "publish" / "thumbnail.jpg").write_bytes(b"jpg")
    api = FakeAPI()
    rc, out = go(ep, api)
    assert rc == 0, out
    assert ("POST", "https://www.googleapis.com/upload/youtube/v3/thumbnails/set") in api.calls


def test_a_dropped_upload_resumes_in_the_same_session(tmp_path):
    ep = episode(tmp_path)
    api = FakeAPI(drop_first_put=True)
    rc, out = go(ep, api, only={"long"})
    assert rc == 0, out
    assert len(api.bodies) == 1  # one session, resumed, not a second insert


def test_wrong_channel_and_remote_duplicates_are_refused(tmp_path):
    ep = episode(tmp_path)
    rc, out = go(ep, FakeAPI(channel="UC_sleep"))
    assert rc == 1 and "not UC_explainer" in out and not S.state_path(ep).exists() or "video_id" not in out
    api = FakeAPI(existing={PUB["title"]: "old1"})
    rc, out = go(ep, api, only={"long"})
    assert rc == 1 and "--adopt long=old1" in out and api.bodies == []
    rc, out = go(ep, api, only={"long"}, adopt={"long": "old1"})
    assert rc == 0 and json.loads(S.state_path(ep).read_text())["items"]["long"]["video_id"] == "old1"


def test_gates_block_the_upload(tmp_path):
    bad = {**PUB, "audience": "made_for_kids"}  # PC-02 FAIL
    ep = episode(tmp_path, bad)
    rc, out = go(ep, FakeAPI())
    assert rc == 1 and "PC-02" in out
    ep2 = episode(tmp_path / "b")
    (ep2 / "render" / "shorts" / "SH02.mp4").unlink()
    rc, out = go(ep2, FakeAPI())
    assert rc == 1 and "SH02 file" in out
    rc = S.run(episode(tmp_path / "c"), yes=True, confirm="", yt=YouTube(token(), FakeAPI()), env={}, log=lambda s: None)
    assert rc == 1


def test_disclosure_maps_to_contains_synthetic_media(tmp_path):
    pub = {**PUB, "disclosure": {**PUB["disclosure"], "decision": "disclose", "reason": "realistic voice of a real person"},
           "youtube": {**PUB["youtube"], "ai_note": "Voices are AI-generated."}}
    stage = P.build(episode(tmp_path, pub))
    assert all(it["body"]["status"]["containsSyntheticMedia"] for it in stage["items"])
    assert "Voices are AI-generated." in stage["items"][1]["body"]["snippet"]["description"]


def test_quota_stops_at_the_daily_bucket():
    state = {"quota": {}}
    S._count(state, uploads=100)
    with pytest.raises(YouTubeError):
        S._count(state, uploads=1)


def test_token_comes_from_the_env_only():
    raw = base64.b64encode(json.dumps(token()).encode()).decode()
    assert load_token({"YOUTUBE_TOKEN_B64": raw})["refresh_token"] == "r"
    with pytest.raises(YouTubeError):
        load_token({})


def test_thumbnail_estimate_is_free_and_generation_needs_approval(tmp_path):
    ep = episode(tmp_path)
    lines = []
    assert T.run(ep, log=lines.append) == 0
    assert any("gemini-3-pro-image" in l and "USD" in l for l in lines)

    class Paid:
        calls = 0

        def generate(self, name, prompt, **kw):
            Paid.calls += 1
            from PIL import Image
            out = ep / "raw.png"
            Image.new("RGB", (2048, 1152), (40, 40, 60)).save(out)
            return out

    assert T.run(ep, generate=True, approved_by="", client=Paid(), log=lambda s: None) == 1 and Paid.calls == 0
    assert T.run(ep, generate=True, approved_by="vano1919, thread", client=Paid(), log=lambda s: None) == 0
    assert T.check_image(ep / "publish" / "thumbnail.jpg") == []
    assert T.check_text("one two three four five") and not T.check_text("WHO FALLS FIRST?")


def test_no_code_path_names_public_or_update():
    src = "\n".join(p.read_text(encoding="utf-8") for p in Path(P.__file__).parent.glob("*.py"))
    assert "privacyStatus\": \"public" not in src and "'public'" not in src
    assert "videos.update" not in src.replace("no ``videos.update``", "")
    assert "/videos?" not in src.replace("{UPLOAD}/videos?", "")  # the only videos write is the resumable insert
