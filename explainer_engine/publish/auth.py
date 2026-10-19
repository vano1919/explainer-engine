"""``publish auth``: the one-time YouTube sign-in, run on the creator's PC (a browser is needed). stdlib only.

    .venv\\Scripts\\python -m explainer_engine.publish auth path\\to\\client_secret.json

Opens Google's consent page (scopes: youtube.upload to upload and set thumbnails, youtube.readonly to check the channel and
avoid double uploads; no scope can change a video's visibility after upload), catches the answer on localhost, prints the
channel the token belongs to and writes ``tools/youtube/token.json`` (gitignored) plus ``token.b64.txt``: its content is the
value of the cloud environment variable YOUTUBE_TOKEN_B64. Never prints the token itself.
"""

from __future__ import annotations

import base64
import hashlib
import http.server
import json
import secrets
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path

from explainer_engine.publish.youtube import SCOPES, TOKEN_URI

AUTH_URI = "https://accounts.google.com/o/oauth2/auth"
OUT = Path(__file__).resolve().parents[2] / "tools" / "youtube"


def _catch_code(state: str) -> tuple[str, int, http.server.HTTPServer]:
    result = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            q = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(self.path).query))
            if q.get("state") == state and "code" in q:
                result["code"] = q["code"]
            self.send_response(200)
            self.end_headers()
            self.wfile.write("Signed in. You can close this tab.".encode())

        def log_message(self, *a):
            pass

    server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    return result, server.server_port, server


def main(client_file: str) -> int:
    client = json.loads(Path(client_file).read_text(encoding="utf-8"))
    client = client.get("installed") or client.get("web") or client
    state = secrets.token_urlsafe(16)
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    result, port, server = _catch_code(state)
    redirect = f"http://127.0.0.1:{port}"
    url = AUTH_URI + "?" + urllib.parse.urlencode({
        "client_id": client["client_id"], "redirect_uri": redirect, "response_type": "code", "scope": " ".join(SCOPES),
        "access_type": "offline", "prompt": "consent select_account", "state": state, "code_challenge": challenge,
        "code_challenge_method": "S256"})
    print("A browser opens: sign in, then pick the CHANNEL the videos belong to (not the sleep channel).")
    webbrowser.open(url)
    while "code" not in result:
        server.handle_request()
    body = urllib.parse.urlencode({"code": result["code"], "client_id": client["client_id"],
                                   "client_secret": client["client_secret"], "redirect_uri": redirect,
                                   "grant_type": "authorization_code", "code_verifier": verifier}).encode()
    tok = json.load(urllib.request.urlopen(client.get("token_uri") or TOKEN_URI, body, timeout=60))
    if not tok.get("refresh_token"):
        raise SystemExit("Google returned no refresh token; remove the app's access at myaccount.google.com/permissions "
                         "and run this again")
    req = urllib.request.Request("https://www.googleapis.com/youtube/v3/channels?part=snippet&mine=true",
                                 headers={"Authorization": f"Bearer {tok['access_token']}"})
    items = json.load(urllib.request.urlopen(req, timeout=60)).get("items") or []
    saved = {"client_id": client["client_id"], "client_secret": client["client_secret"],
             "refresh_token": tok["refresh_token"], "token_uri": client.get("token_uri") or TOKEN_URI, "scopes": SCOPES}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "token.json").write_text(json.dumps(saved, indent=1), encoding="utf-8")
    (OUT / "token.b64.txt").write_text(base64.b64encode(json.dumps(saved).encode()).decode(), encoding="utf-8")
    for c in items:
        print(f"channel: {c['snippet']['title']}  id: {c['id']}  -> EXPLAINER_YT_CHANNEL={c['id']}")
    print(f"saved {OUT / 'token.json'}; the value of YOUTUBE_TOKEN_B64 is in {OUT / 'token.b64.txt'} (paste it into the "
          "cloud environment's variables, not into a chat)")
    return 0
