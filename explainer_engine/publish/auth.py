# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0): Synchronous Master Mold v2.1.0 Alignment for `explainer_engine/publish/auth.py`
# Target Module : explainer_engine/publish/auth.py
# Target Classes/Symbols : def _client_from_env(), def consent_url(), def _exchange(), def _save(), def url_step(), def finish_step(), def _catch_code(), def main()
# Reference Guide : docs/wip/CLAUDE_SYNCHRONIZED_TODO_EXECUTION_GUIDE_2026-11-04.md
# Roadmap Reference : docs/wip/MASTER_MOLD_INTEGRATION_ROADMAP_2026-11-02.md
# =============================================================================
#
# 1. რა ცვლილება უნდა გაკეთდეს (EXACT SYNCHRONOUS CHANGE SPECIFICATION):
#    Synchronize this core module with `production_script/4` (`schema_version.py`, `mold_contract.py`), the 4-tier visual router (`tier_router.py`), the 6-stage `D-81` voice chain (`voice_chain.py`), and the 24 fps rational-time `bounded_timeline.py` solver so all CLI commands, config loaders, and package exports operate seamlessly across `/1`, `/2`, `/3`, and `/4` scripts.
#
# 2. რა ნაკლოვანება აქვს ამჟამინდელ კოდს (CURRENT CODE FLAW / DEFICIT AT 5013a55a):
#    Currently this core module defaults to v2/v3 assumptions and does not expose or wire the new Master Mold v2.1.0 subsystems.
#
# 3. რატომაა უახლესი გადაწყვეტა უკეთესი (WHY THE NEW SOLUTION IS SUPERIOR):
#    Ensures end-to-end synchronous behavior from CLI invocation through script validation, audio synthesis, 4-tier rendering, OTIO export, and final QA verification.
#
# 4. დამადასტურებელი ვებ-წყაროები — მინიმუმ 5 წყარო (VERIFIED WEB SOURCES >= 5):
#    [1] JSON Schema Draft 2020-12 Official Specification
#        URL: https://json-schema.org/draft/2020-12
#        Rationale: Defines canonical $schema URI resolution, discriminator dispatch, additionalProperties: false enforcement, and backwards-compatible schema evolution across versioned contracts.
#    [2] JSON Schema Core Validation Spec (2020-12)
#        URL: https://json-schema.org/draft/2020-12/json-schema-core
#        Rationale: Establishes structural validation guarantees so versioned payloads (/1, /2, /3, /4) cannot silently fall back to incompatible schema validators.
#    [3] Python jsonschema Library Documentation
#        URL: https://python-jsonschema.readthedocs.io/en/stable/
#        Rationale: Reference implementation used by explainer_engine for Draft202012Validator dispatch and strict contract validation.
#    [4] Anthropic Claude Code Costs & Prompt Caching
#        URL: https://code.claude.com/docs/en/costs
#        Rationale: Demonstrates why deterministic offline schema/contract validation (BATCH-M0/M2) must precede paid LLM/API calls to avoid wasted token and GPU spend.
#    [5] OpenTimelineIO File Format Specification
#        URL: https://opentimelineio.readthedocs.io/en/v0.13/tutorials/otio-file-format-specification.html
#        Rationale: Defines timeline metadata and rational-time contract serialization that downstream edit/render stages consume from production_script/4.
# =============================================================================

"""``publish auth``: the one-time YouTube sign-in, run on the creator's PC (a browser is needed). stdlib only.

    .venv\\Scripts\\python -m explainer_engine.publish auth path\\to\\client_secret.json

Opens Google's consent page (scopes: youtube.upload to upload and set thumbnails, youtube.readonly to check the channel and
avoid double uploads; no scope can change a video's visibility after upload), catches the answer on localhost, prints the
channel the token belongs to and writes ``tools/youtube/token.json`` (gitignored) plus ``token.b64.txt``: its content is the
value of the cloud environment variable YOUTUBE_TOKEN_B64. Never prints the token itself.

Without a PC (the creator on a phone, 2026-10-19), the same sign-in in two steps from the cloud session:

    python -m explainer_engine.publish auth-url                 # prints the consent link; the PKCE verifier stays here
    python -m explainer_engine.publish auth-finish '<the 127.0.0.1 address the phone ended on>'

The phone's browser ends on an unreachable http://127.0.0.1 page; its address holds a one-time code that is useless without
this session's client secret and verifier, and expires within minutes. The client comes from YOUTUBE_CLIENT_B64.
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


PENDING = OUT / "pending.json"
MANUAL_REDIRECT = "http://127.0.0.1:8765"


def _client_from_env(env=None) -> dict:
    import os
    raw = (env if env is not None else os.environ).get("YOUTUBE_CLIENT_B64", "")
    if not raw:
        raise SystemExit("YOUTUBE_CLIENT_B64 is not set (the OAuth client JSON, base64)")
    c = json.loads(base64.b64decode(raw))
    return c.get("installed") or c.get("web") or c


def consent_url(client: dict, redirect: str, state: str, verifier: str) -> str:
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    return AUTH_URI + "?" + urllib.parse.urlencode({
        "client_id": client["client_id"], "redirect_uri": redirect, "response_type": "code", "scope": " ".join(SCOPES),
        "access_type": "offline", "prompt": "consent select_account", "state": state, "code_challenge": challenge,
        "code_challenge_method": "S256"})


def _exchange(client: dict, code: str, redirect: str, verifier: str) -> tuple[dict, list]:
    body = urllib.parse.urlencode({"code": code, "client_id": client["client_id"],
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
    if items:
        saved["channel_id"] = items[0]["id"]  # `stage` refuses any other channel unless EXPLAINER_YT_CHANNEL says otherwise
    return saved, items


def _save(saved: dict, items: list, out: Path = OUT) -> None:
    out.mkdir(parents=True, exist_ok=True)
    (out / "token.json").write_text(json.dumps(saved, indent=1), encoding="utf-8")
    (out / "token.b64.txt").write_text(base64.b64encode(json.dumps(saved).encode()).decode(), encoding="utf-8")
    for c in items:
        print(f"channel: {c['snippet']['title']}  id: {c['id']}  -> EXPLAINER_YT_CHANNEL={c['id']}")
    print(f"saved {out / 'token.json'}; the value of YOUTUBE_TOKEN_B64 is in {out / 'token.b64.txt'}")


def url_step() -> int:
    client = _client_from_env()
    state, verifier = secrets.token_urlsafe(16), secrets.token_urlsafe(64)
    OUT.mkdir(parents=True, exist_ok=True)
    PENDING.write_text(json.dumps({"state": state, "verifier": verifier}), encoding="utf-8")
    print(consent_url(client, MANUAL_REDIRECT, state, verifier))
    return 0


def finish_step(answer: str) -> int:
    pending = json.loads(PENDING.read_text(encoding="utf-8"))
    q = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(answer.strip()).query)) if "?" in answer else {"code": answer.strip()}
    if q.get("state", pending["state"]) != pending["state"]:
        raise SystemExit("this answer belongs to another sign-in link; make a new one with auth-url")
    if "code" not in q:
        raise SystemExit(f"no code in the answer ({q.get('error', 'unknown')})")
    saved, items = _exchange(_client_from_env(), q["code"], MANUAL_REDIRECT, pending["verifier"])
    PENDING.unlink()
    _save(saved, items)
    return 0


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
    result, port, server = _catch_code(state)
    redirect = f"http://127.0.0.1:{port}"
    print("A browser opens: sign in, then pick the CHANNEL the videos belong to (not the sleep channel).")
    webbrowser.open(consent_url(client, redirect, state, verifier))
    while "code" not in result:
        server.handle_request()
    _save(*_exchange(client, result["code"], redirect, verifier))
    return 0
