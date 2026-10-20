"""YouTube Data API v3 client for staging uploads (D-57): token refresh, resumable insert, thumbnails.set, read-only checks.
stdlib only. Every request goes through ``transport`` so tests run against a fake API with no network.

Never public: ``STAGE_PRIVACY`` is the only set of privacy values this module sends, ``insert`` refuses anything else and
never sends ``status.publishAt`` (a past time would publish at once, developers.google.com/youtube/v3/docs/videos). There is
no ``videos.update`` here, so nothing can flip a staged video to public; that is the creator's click in Studio.

Sources (read 2026-10-19, V-45..V-49 in docs/MARKET_RESEARCH.md): resumable protocol
developers.google.com/youtube/v3/guides/using_resumable_upload_protocol; quota developers.google.com/youtube/v3/determine_quota_cost.
"""

from __future__ import annotations

import base64
import http.client
import json
import os
import time
import urllib.parse
from pathlib import Path
from typing import Callable

STAGE_PRIVACY = ("unlisted", "private")
SCOPES = ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube.readonly"]
TOKEN_ENV = "YOUTUBE_TOKEN_B64"  # base64 of the authorized-user JSON (client_id, client_secret, refresh_token, token_uri)
CHANNEL_ENV = "EXPLAINER_YT_CHANNEL"  # the channel id uploads must land on; a token of another channel is refused
API = "https://www.googleapis.com/youtube/v3"
UPLOAD = "https://www.googleapis.com/upload/youtube/v3"
TOKEN_URI = "https://oauth2.googleapis.com/token"
RETRY_STATUS = (500, 502, 503, 504)
FORBIDDEN_STATUS_KEYS = ("publishAt",)

# (method, url, headers, body) -> (status, headers lower-cased, body bytes); body may be bytes, None or a (file, length) pair
Transport = Callable[[str, str, dict, object], tuple[int, dict, bytes]]


class YouTubeError(RuntimeError):
    pass


class NotStaging(YouTubeError):
    """A request would make a video public or schedule it: refused before anything is sent (D-57)."""


def http_transport(method: str, url: str, headers: dict, body=None, timeout: float = 600.0) -> tuple[int, dict, bytes]:
    u = urllib.parse.urlsplit(url)
    conn = http.client.HTTPSConnection(u.netloc, timeout=timeout)
    path = u.path + ("?" + u.query if u.query else "")
    try:
        if isinstance(body, tuple):  # (open file positioned at the offset, bytes to send): streamed, never read whole
            f, length = body
            conn.putrequest(method, path)
            for k, v in headers.items():
                conn.putheader(k, v)
            conn.endheaders()
            left = length
            while left > 0:
                block = f.read(min(1 << 20, left))
                if not block:
                    break
                conn.send(block)
                left -= len(block)
        else:
            conn.request(method, path, body=body, headers=headers)
        r = conn.getresponse()
        return r.status, {k.lower(): v for k, v in r.getheaders()}, r.read()
    finally:
        conn.close()


TOKEN_FILE = Path(__file__).resolve().parents[2] / "tools" / "youtube" / "token.json"  # gitignored, one session's sign-in


def load_token(env: dict | None = None, file: Path | None = None) -> dict:
    """The token of this session's sign-in (tools/youtube/token.json, made by ``publish auth-finish``), else YOUTUBE_TOKEN_B64."""
    file = TOKEN_FILE if file is None else file
    if env is None and file.exists():
        return json.loads(file.read_text(encoding="utf-8"))
    raw = (env if env is not None else os.environ).get(TOKEN_ENV, "")
    if not raw:
        raise YouTubeError("no YouTube sign-in in this session: run `python -m explainer_engine.publish auth-url`, the creator "
                           "opens the link and sends back the 127.0.0.1 address, then `auth-finish '<address>'`")
    try:
        tok = json.loads(base64.b64decode(raw))
    except ValueError:
        raise YouTubeError(f"{TOKEN_ENV} is not base64 JSON") from None
    missing = [k for k in ("client_id", "client_secret", "refresh_token") if not tok.get(k)]
    if missing:
        raise YouTubeError(f"{TOKEN_ENV} lacks {missing}")
    return tok


class YouTube:
    def __init__(self, token: dict, transport: Transport | None = None, sleep=time.sleep, retries: int = 5):
        self.token = token
        self.transport = transport or http_transport
        self.sleep = sleep
        self.retries = retries
        self.access = ""

    # --- auth -------------------------------------------------------------------------------------------------------
    def _refresh(self) -> None:
        body = urllib.parse.urlencode({"client_id": self.token["client_id"], "client_secret": self.token["client_secret"],
                                       "refresh_token": self.token["refresh_token"], "grant_type": "refresh_token"}).encode()
        status, _, data = self.transport("POST", self.token.get("token_uri") or TOKEN_URI,
                                         {"Content-Type": "application/x-www-form-urlencoded"}, body)
        if status != 200:
            detail = data.decode("utf-8", "replace")[:200]
            hint = " (the refresh token expired or was revoked: run `publish auth` again)" if "invalid_grant" in detail else ""
            raise YouTubeError(f"token refresh failed: HTTP {status}{hint}")  # the body may echo ids; never printed whole
        self.access = json.loads(data)["access_token"]

    def _headers(self, extra: dict | None = None) -> dict:
        if not self.access:
            self._refresh()
        return {"Authorization": f"Bearer {self.access}", **(extra or {})}

    def _call(self, method: str, url: str, headers: dict | None = None, body=None, ok=(200,)) -> tuple[int, dict, bytes]:
        delay = 2.0
        for attempt in range(self.retries + 1):
            status, h, data = self.transport(method, url, self._headers(headers), body)
            if status == 401 and attempt == 0:
                self.access = ""
                continue
            if status in RETRY_STATUS and attempt < self.retries and not isinstance(body, tuple):
                self.sleep(delay)
                delay *= 2
                continue
            if status not in ok:
                raise YouTubeError(f"{method} {url.split('?')[0]}: HTTP {status}: {data.decode('utf-8', 'replace')[:300]}")
            return status, h, data
        raise YouTubeError(f"{method} {url}: no answer")

    def _get(self, path: str, **params) -> dict:
        return json.loads(self._call("GET", f"{API}/{path}?{urllib.parse.urlencode(params)}")[2])

    # --- read-only checks (1 unit each) -----------------------------------------------------------------------------
    def my_channel(self) -> dict:
        items = self._get("channels", part="id,snippet,contentDetails,status", mine="true").get("items") or []
        if not items:
            raise YouTubeError("this token has no YouTube channel")
        return items[0]

    def recent_titles(self, uploads_playlist: str, max_results: int = 50) -> dict[str, str]:
        """title -> video id of the channel's latest uploads (a second line of defence against double uploads)."""
        data = self._get("playlistItems", part="snippet", playlistId=uploads_playlist, maxResults=max_results)
        return {i["snippet"]["title"]: i["snippet"]["resourceId"]["videoId"] for i in data.get("items") or []}

    def video_status(self, video_id: str) -> dict:
        items = self._get("videos", part="status,processingDetails", id=video_id).get("items") or []
        return items[0] if items else {}

    # --- staging upload ---------------------------------------------------------------------------------------------
    @staticmethod
    def guard(body: dict) -> None:
        status = body.get("status") or {}
        if status.get("privacyStatus") not in STAGE_PRIVACY:
            raise NotStaging(f"privacyStatus {status.get('privacyStatus')!r}: this tool stages only {STAGE_PRIVACY}; "
                             "going public is the creator's click in Studio")
        for k in FORBIDDEN_STATUS_KEYS:
            if k in status:
                raise NotStaging(f"status.{k} would publish or schedule the video; never sent")

    def start_session(self, body: dict, size: int, content_type: str = "video/mp4", notify: bool = False) -> str:
        self.guard(body)
        parts = ",".join(k for k in body if k in ("snippet", "status", "recordingDetails"))
        q = urllib.parse.urlencode({"uploadType": "resumable", "part": parts, "notifySubscribers": str(notify).lower()})
        _, h, _ = self._call("POST", f"{UPLOAD}/videos?{q}", {
            "Content-Type": "application/json; charset=UTF-8", "X-Upload-Content-Length": str(size),
            "X-Upload-Content-Type": content_type}, json.dumps(body).encode())
        if not h.get("location"):
            raise YouTubeError("no resumable session URI in the answer")
        return h["location"]

    def received(self, session: str, size: int) -> int | None:
        """Bytes the server already holds for this session; None when the session is gone (404/410: start again)."""
        status, h, data = self.transport("PUT", session, self._headers({"Content-Range": f"bytes */{size}",
                                                                          "Content-Length": "0"}), b"")
        if status in (200, 201):
            return size
        if status == 308:
            rng = h.get("range")
            return int(rng.split("-")[1]) + 1 if rng else 0
        if status in (404, 410):
            return None
        raise YouTubeError(f"upload status: HTTP {status}: {data.decode('utf-8', 'replace')[:200]}")

    def send(self, session: str, path: Path, size: int, offset: int = 0, content_type: str = "video/mp4",
             progress=None) -> dict:
        """Upload from ``offset`` to the end, resuming after a dropped connection or a 5xx; returns the video resource."""
        delay = 2.0
        for attempt in range(self.retries + 1):
            try:
                with open(path, "rb") as f:
                    f.seek(offset)
                    headers = {"Content-Type": content_type, "Content-Length": str(size - offset)}
                    if offset:
                        headers["Content-Range"] = f"bytes {offset}-{size - 1}/{size}"
                    status, h, data = self.transport("PUT", session, self._headers(headers), (f, size - offset))
                if status in (200, 201):
                    return json.loads(data)
                if status == 401:
                    self.access = ""
                elif status not in RETRY_STATUS + (308,):
                    raise YouTubeError(f"upload: HTTP {status}: {data.decode('utf-8', 'replace')[:300]}")
            except (OSError, http.client.HTTPException) as exc:
                if attempt == self.retries:
                    raise YouTubeError(f"upload: {exc}") from None
            if attempt == self.retries:
                break
            self.sleep(delay)
            delay *= 2
            got = self.received(session, size)
            if got is None:
                raise YouTubeError("the upload session expired; run the stage again (it starts a new session)")
            offset = got
            if progress:
                progress(offset, size)
        raise YouTubeError("upload: no success after retries; run the stage again to resume")

    def set_thumbnail(self, video_id: str, image: Path) -> dict:
        data = Path(image).read_bytes()
        ctype = "image/png" if str(image).lower().endswith(".png") else "image/jpeg"
        _, _, out = self._call("POST", f"{UPLOAD}/thumbnails/set?videoId={urllib.parse.quote(video_id)}",
                               {"Content-Type": ctype}, data)
        return json.loads(out or b"{}")
