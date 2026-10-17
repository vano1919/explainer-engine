

def test_batch_get_is_retried_when_the_answer_is_cut_off_but_a_post_is_not(tmp_path, monkeypatch):
    """Syndicate Wars 2026-10-17: a 57 MB batch answer was cut off by the proxy (IncompleteRead); GET retries, POST never."""
    import http.client
    import urllib.request

    import pytest

    from explainer_engine.imagegen import gemini as G

    class Resp:
        def __init__(self, data):
            self.data = data
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False
        def read(self):
            return self.data

    calls = {"n": 0}

    def flaky(request, timeout=0):
        calls["n"] += 1
        if calls["n"] < 3:
            raise http.client.IncompleteRead(b"x")
        return Resp(b'{"ok": true}')

    monkeypatch.setattr(urllib.request, "urlopen", flaky)
    monkeypatch.setattr(G.time, "sleep", lambda s: None)
    c = G.GeminiClient(tmp_path, key="k", cap_usd=1.0)
    assert c._batch_http("GET", "https://x/y") == {"ok": True} and calls["n"] == 3
    calls["n"] = 0
    with pytest.raises(G.GeminiError):
        c._batch_http("POST", "https://x/y", {})
    assert calls["n"] == 1
