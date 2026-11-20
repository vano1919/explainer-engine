"""L32: the token file for the cloud env variable is written only on request; the token source is logged; no token is tracked."""

from __future__ import annotations

import base64
import json
import subprocess
from pathlib import Path

import pytest

from explainer_engine.publish import auth
from explainer_engine.publish.youtube import YouTubeError, load_token

ROOT = Path(__file__).resolve().parents[2]
TOK = {"client_id": "c", "client_secret": "s", "refresh_token": "r"}


def test_save_without_flag_writes_only_token_json(tmp_path, capsys):
    auth._save(TOK, [], out=tmp_path)
    assert (tmp_path / "token.json").exists()
    assert not (tmp_path / "token.b64.txt").exists()
    assert "token.b64.txt" not in capsys.readouterr().out


def test_save_with_export_env_writes_b64_and_names_it(tmp_path, capsys):
    auth._save(TOK, [], out=tmp_path, export_env=True)
    assert json.loads(base64.b64decode((tmp_path / "token.b64.txt").read_text())) == TOK
    assert "token.b64.txt" in capsys.readouterr().out


def test_cli_accepts_export_env_flag():
    from explainer_engine.publish import __main__ as m
    import inspect
    assert "--export-env" in inspect.getsource(m)


def test_token_source_file_is_logged_without_the_token(tmp_path):
    f = tmp_path / "token.json"
    f.write_text(json.dumps(TOK))
    lines: list[str] = []
    assert load_token(file=f, log=lines.append)["refresh_token"] == "r"
    assert len(lines) == 1 and "token.json" in lines[0] and "r" != lines[0] and "refresh" not in lines[0]


def test_token_source_env_is_logged_without_the_token(tmp_path):
    raw = base64.b64encode(json.dumps(TOK).encode()).decode()
    lines: list[str] = []
    load_token({"YOUTUBE_TOKEN_B64": raw}, file=tmp_path / "none.json", log=lines.append)
    assert len(lines) == 1 and "YOUTUBE_TOKEN_B64" in lines[0] and raw not in lines[0]


def test_no_source_logs_nothing_and_raises(tmp_path):
    lines: list[str] = []
    with pytest.raises(YouTubeError):
        load_token({}, file=tmp_path / "none.json", log=lines.append)
    assert lines == []


def _tracked() -> list[str]:
    return subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.splitlines()


def test_no_token_or_pending_file_is_tracked_under_tools():
    bad = [f for f in _tracked() if f.startswith("tools/") and (Path(f).name.startswith("token") or Path(f).name == "pending.json")]
    assert not bad


def test_gitignore_covers_the_youtube_tools_folder():
    for name in ("token.b64.txt", "token.json", "pending.json"):
        r = subprocess.run(["git", "check-ignore", "-q", f"tools/youtube/{name}"], cwd=ROOT)
        assert r.returncode == 0, name
