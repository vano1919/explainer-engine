"""Download a FREE itch.io pack the way the page's own download button does (roadmap 21.6 PoC 1; ICW-06).

Quaternius (Universal Base Characters, Universal Animation Library, Modular Character Outfits) and KayKit publish their CC0 packs
on itch.io as "name your own price" items with a minimum of $0. The button is three requests, all public and without an
account: the page's CSRF token -> ``POST <page>/download_url`` (a signed download page) -> ``POST <page>/file/<upload id>``
(a 60-second signed URL of the file). ICW-05b could not fetch KayKit because only the button knew this; this module is that
button as a reusable step, stdlib only. It refuses a pack whose minimum price is not 0 (a paid item is the creator's purchase,
never ours), and it never logs in.

    python -m explainer_engine.assets.itch list https://quaternius.itch.io/universal-animation-library
    python -m explainer_engine.assets.itch get https://quaternius.itch.io/universal-animation-library --out D [--match Standard]

The file lands in ``--out`` under its own upload name; the caller registers it (``assets.library import --source <key>``) and
keeps its sha256. Nothing here is paid.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import http.cookiejar
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

UA = "explainer-engine-asset-import/1"
CSRF = re.compile(r'name="csrf_token" value="([^"]+)"')
UPLOAD = re.compile(r'data-upload_id="(\d+)".*?title="([^"]+)"', re.S)
MIN_PRICE = re.compile(r'"min_price":(\d+)')


class ItchError(RuntimeError):
    pass


class Session:
    """One cookie jar for the three requests (the CSRF token is bound to the session cookie)."""

    def __init__(self, opener=None, backoff_s: float = 20.0):
        self.backoff_s = backoff_s
        if opener is None:
            opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        self.opener = opener

    def _req(self, url: str, data: dict | None = None, referer: str | None = None) -> bytes:
        headers = {"User-Agent": UA}
        if referer:
            headers["Referer"] = referer
        body = urllib.parse.urlencode(data).encode() if data is not None else None
        for attempt in range(3):
            try:
                with self.opener.open(urllib.request.Request(url, data=body, headers=headers), timeout=120) as r:
                    return r.read()
            except urllib.error.HTTPError as e:
                if e.code != 429 or attempt == 2:
                    raise ItchError(f"{url}: HTTP {e.code} {e.reason}") from e
                time.sleep(self.backoff_s * (attempt + 1))  # itch.io rate limit: wait, then the same request again
        raise AssertionError("unreachable")

    def get(self, url: str, referer: str | None = None) -> str:
        return self._req(url, referer=referer).decode("utf-8", "replace")

    def post_json(self, url: str, data: dict, referer: str | None = None) -> dict:
        raw = self._req(url, data=data, referer=referer)
        try:
            return json.loads(raw)
        except ValueError as e:
            raise ItchError(f"{url}: not a JSON answer ({raw[:120]!r})") from e

    def stream(self, url: str, dest: Path) -> str:
        """Write the file in 1 MiB blocks under a temporary name, then rename; returns its sha256."""
        h = hashlib.sha256()
        tmp = dest.with_name(dest.name + ".part")
        with self.opener.open(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=600) as r, open(tmp, "wb") as f:
            while True:
                block = r.read(1 << 20)
                if not block:
                    break
                h.update(block)
                f.write(block)
        tmp.replace(dest)
        return h.hexdigest()


def _token(page: str, url: str) -> str:
    m = CSRF.search(page)
    if not m:
        raise ItchError(f"{url}: no CSRF token on the page (itch.io changed its page?)")
    return html.unescape(m.group(1))


def uploads(page_url: str, *, session: Session | None = None) -> tuple[str, list[dict]]:
    """The signed download page of a free pack and its files [{id, name}]."""
    s = session or Session()
    page_url = page_url.rstrip("/")
    page = s.get(page_url)
    m = MIN_PRICE.search(page)
    if m is None or int(m.group(1)) != 0:
        raise ItchError(f"{page_url}: not a free pack (min_price {m.group(1) if m else 'unknown'}); a paid item is the creator's purchase")
    ans = s.post_json(page_url + "/download_url", {"csrf_token": _token(page, page_url)}, referer=page_url)
    if "url" not in ans:
        raise ItchError(f"{page_url}: no download page ({ans})")
    dl_url = ans["url"]
    dl = s.get(dl_url, referer=page_url)
    files = [{"id": int(i), "name": html.unescape(n)} for i, n in UPLOAD.findall(dl)]
    if not files:
        raise ItchError(f"{dl_url}: the download page lists no file")
    return dl_url, files


def download(page_url: str, out: Path, *, match: str | None = None, session: Session | None = None) -> list[dict]:
    """Every file of the pack whose name contains ``match`` (all when None) into ``out``: [{name, path, sha256, bytes}]."""
    s = session or Session()
    page_url = page_url.rstrip("/")
    dl_url, files = uploads(page_url, session=s)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    chosen = [f for f in files if match is None or match.lower() in f["name"].lower()]
    if not chosen:
        raise ItchError(f"{page_url}: no file matches {match!r} (have {[f['name'] for f in files]})")
    token = _token(s.get(dl_url, referer=page_url), dl_url)
    done = []
    for f in chosen:
        ans = s.post_json(f"{page_url}/file/{f['id']}?source=game_download&after_download_lightbox=1",
                          {"csrf_token": token}, referer=dl_url)
        if not ans.get("url") or ans.get("external"):
            raise ItchError(f"{f['name']}: itch.io gave no direct file URL ({ {k: v for k, v in ans.items() if k != 'lightbox'} })")
        dest = out / f["name"]
        digest = s.stream(ans["url"], dest)
        done.append({"name": f["name"], "upload_id": f["id"], "path": str(dest), "sha256": digest, "bytes": dest.stat().st_size,
                     "page": page_url})
    return done


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m explainer_engine.assets.itch", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("list")
    a.add_argument("page")
    g = sub.add_parser("get")
    g.add_argument("page")
    g.add_argument("--out", required=True)
    g.add_argument("--match")
    args = ap.parse_args(argv)
    try:
        if args.cmd == "list":
            print(json.dumps(uploads(args.page)[1], indent=1))
        else:
            print(json.dumps(download(args.page, Path(args.out), match=args.match), indent=1))
    except ItchError as e:
        print(f"itch: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
