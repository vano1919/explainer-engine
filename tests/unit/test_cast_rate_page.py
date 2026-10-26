import json

from PIL import Image

from explainer_engine.training.cast import rate_page


def test_rate_page_keeps_pass_over_fail_and_skips_errors(tmp_path):
    w = tmp_path / "world"; w.mkdir()
    for n in ("c000", "c000_t1", "p000"):
        Image.new("RGB", (40, 40), "white").save(w / f"{n}.png")
    rows = [{"name": "c000", "id": "c000", "kind": "person", "verdict": "FAIL", "why": ["x"]},
            {"name": "c000_t1", "id": "c000", "kind": "person", "verdict": "PASS", "why": []},
            {"name": "p000", "id": "p000", "kind": "place", "verdict": "REVIEW", "why": ["y"]},
            {"name": "o000", "id": "o000", "kind": "object", "verdict": "ERROR"}]
    (w / "report.jsonl").write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    out = rate_page.build(w, tmp_path / "out", looks={"p000": "note"})
    assert [r["name"] for r in out] == ["c000_t1", "p000"]
    page = (tmp_path / "out" / "index.html").read_text(encoding="utf-8")
    assert "ratings/" in page and "იდეალურია" in page and "note" in page
    assert (tmp_path / "out" / "img" / "c000_t1.jpg").exists()
