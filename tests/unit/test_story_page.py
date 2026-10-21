"""EG-23 (BP-89, the creator 2026-10-20): a passing review of a /3 script comes with a one-page Georgian story page."""
import json

from explainer_engine.production import editorial_gate as EG
from test_integrated_review import STORY_PAGE, review2, scene_mini, write_pair


def eg23(script, rev):
    return [f for f in EG.check(script, rev) if f["rule"] == "EG-23"]


def test_a_clean_review_with_its_story_page_passes(tmp_path):
    script, rev = write_pair(tmp_path, scene_mini())
    assert eg23(script, rev) == []


def test_a_review_without_a_story_page_is_refused(tmp_path):
    script, rev = write_pair(tmp_path, scene_mini())
    r = json.loads(rev.read_text(encoding="utf-8"))
    del r["story_page"]
    rev.write_text(json.dumps(r), encoding="utf-8")
    assert eg23(script, rev)


def test_the_page_must_exist_be_georgian_one_page_and_say_why(tmp_path):
    script, rev = write_pair(tmp_path, scene_mini())
    page = tmp_path / "story_page.md"
    page.unlink()
    assert eg23(script, rev)  # missing file
    page.write_text("# Story\n\n" + "Mara finds the lantern in the valley. " * 30 + "\n\n## რატომ\n", encoding="utf-8")
    assert eg23(script, rev)  # English
    page.write_text(STORY_PAGE.replace("რატომ", "შემდეგ"), encoding="utf-8")
    assert eg23(script, rev)  # no "why" section
    page.write_text("# ისტორია\n\nმოკლედ.\n\n## რატომ\n", encoding="utf-8")
    assert eg23(script, rev)  # too short to tell the whole story
    page.write_text(STORY_PAGE * 5, encoding="utf-8")
    assert eg23(script, rev)  # more than one page


def test_legacy_scripts_need_no_story_page(tmp_path):
    from test_editorial_gate import valid_doc
    script = tmp_path / "production_script.json"
    script.write_text(json.dumps(valid_doc()), encoding="utf-8")
    rev = tmp_path / "editorial_review.json"
    r = review2(script)
    del r["story_page"]
    rev.write_text(json.dumps(r), encoding="utf-8")
    assert eg23(script, rev) == []
