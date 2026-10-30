"""P1b (docs/CLOUD_RUNBOOK.md CR-18): ``config/cloud_pins.json``, ``runpod dryrun`` and the create refusals built on them. No pod, no
network (the Hub check is injected), no money."""
import copy
import json
import re
import subprocess
from pathlib import Path

import pytest
from test_cloud_stop_paths import FakeLive, _create  # noqa: F401
from test_cloud_stop_paths import env  # noqa: F401 - the fixture of the create tests
from test_pod_wrapper import pod as wrapper  # noqa: F401 - the fixture running the real wrapper
from test_runpod import NEW_SH, VAULT_CHECK

from explainer_engine.cloud import dryrun as D, pins as P, runpod as R

PODS = Path(R.__file__).resolve().parents[1] / "training" / "pods"
SHA = "b69b98314557f7c8b08e11bbb14e48d959e6ab26"
PINS = P.load()


def _ok(rid, kind):
    return True, ""


CLEAN = """# heartbeat: datasets/o/r:run/out/beat.txt
set -e
pip install -q "huggingface_hub==1.33.0"
git clone -q https://github.com/ostris/ai-toolkit /workspace/aitk && git -C /workspace/aitk checkout -q %s
[ "${DRY:-0}" = 1 ] && exit 0
python - <<PY
from huggingface_hub import snapshot_download as s
s("Qwen/Qwen-Image-2.1", repo_type="model")
PY
echo ok > $EE_OUT/progress.txt
""" % SHA + VAULT_CHECK


# --- the pins file ---------------------------------------------------------------------------------------------------------
def test_the_committed_pins_are_well_formed_and_carry_what_the_paid_plan_names():
    assert {"smoke", "aitoolkit", "tmr_pod"} <= set(PINS["images"])
    for key, e in PINS["images"].items():
        assert P.DIGEST.match(e["digest"]) and e["size_gb"] > 0 and e["smoke_verified"] is False, key
        assert P.image_ref(key, PINS) == f"{e['repo']}@{e['digest']}"
    assert all(re.fullmatch(r"[0-9a-f]{40}", e["sha"]) for e in PINS["git"].values())
    assert PINS["pip"]["huggingface_hub"]["version"]
    # a pin that nobody measured says so: no invented pull speed
    assert all(e["pull_mb_per_s"] is None for e in PINS["images"].values())


def test_an_undecided_or_unknown_pin_is_an_error_not_a_guess():
    pins = copy.deepcopy(PINS)
    pins["images"]["smoke"]["digest"] = None
    with pytest.raises(P.PinError, match="no digest yet"):
        P.image_ref("smoke", pins)
    with pytest.raises(P.PinError, match="no image pin 'nope'"):
        P.image_ref("nope", pins)
    assert any("no digest yet" in w for w in P.check_image("runpod/pytorch@sha256:" + "a" * 64, pins))


def test_a_script_pod_image_must_be_a_pinned_digest():
    ref = P.image_ref("aitoolkit", PINS)
    assert P.check_image(ref, PINS) == [] and P.resolve_image("aitoolkit", PINS) == ref
    assert any("not pinned by digest" in w for w in P.check_image("ostris/aitoolkit:latest", PINS))           # a tag
    assert any("not in config/cloud_pins.json" in w for w in P.check_image("ostris/aitoolkit@sha256:" + "0" * 64, PINS))  # another digest
    assert P.resolve_image("ostris/aitoolkit:latest", PINS) == "ostris/aitoolkit:latest"                      # judged, not rewritten


def test_the_image_cache_rule_boot_minutes():
    ait, smoke = P.image_ref("aitoolkit", PINS), P.image_ref("smoke", PINS)
    assert P.boot_minutes_needed(ait, "COMMUNITY", PINS) == 25                  # not measured: LT-15's 25
    assert P.boot_minutes_needed("x/y@sha256:" + "1" * 64, "COMMUNITY", PINS) == 25   # an image the file does not know
    assert P.boot_minutes_needed(smoke, "SECURE", PINS) == 10
    pins = copy.deepcopy(PINS)
    pins["images"]["aitoolkit"]["pull_mb_per_s"] = 100                          # 6.58 GB at 100 MB/s = 68 s -> 2 min
    assert P.boot_minutes_needed(ait, "COMMUNITY", pins) == 10 + 2
    pins["images"]["aitoolkit"]["pull_mb_per_s"] = 5                            # 1348 s -> 23 min
    assert P.boot_minutes_needed(ait, "SECURE", pins) == 10 + 23


def test_a_pod_pins_txt_is_compared_with_the_file():
    good = f"image={PINS['images']['aitoolkit']['digest']}\ngit:ostris/ai-toolkit={SHA}\npip:huggingface_hub=1.33.0\n# a comment\n"
    assert P.compare(good, PINS) == []
    bad = good.replace(SHA, "c" * 40).replace("1.33.0", "1.2.0") + "git:other/repo=" + "d" * 40 + "\nimage=sha256:" + "e" * 64 + "\n"
    why = P.compare(bad, PINS)
    assert len(why) == 4 and any("ai-toolkit: the pod ran" in w or "git:ostris/ai-toolkit: the pod ran" in w for w in why)
    assert any("pip:huggingface_hub" in w for w in why) and any("other/repo" in w for w in why) and any("is not a digest" in w for w in why)


# --- the dry run: static rules ---------------------------------------------------------------------------------------------
def test_the_three_old_defects_are_found_in_the_scripts_that_had_them():
    text = (PODS / "xworld_v2_loop.sh").read_text()          # the round script of 2026-10-26..29: all three, read from the real file
    why = " | ".join(D.static_problems(text, PINS))
    assert "pip install -U` without `==` for" in why and "peft" in why                       # -U without a pin
    assert "`git clone` without a pinned sha" in why                                         # VideoX-Fun at HEAD of the day
    assert "`|| true` on an install" in why                                                  # a failed install trained on
    assert "git+https://github.com/huggingface/diffusers` has no `@<40-hex sha>`" in why


def test_a_clean_script_has_no_static_problem_and_each_rule_trips_alone():
    assert D.static_problems(CLEAN, PINS) == []
    assert any("pip install -U" in w for w in D.static_problems(CLEAN.replace('"huggingface_hub==1.33.0"', "-U huggingface_hub"), PINS))
    assert D.static_problems(CLEAN.replace('pip install -q "huggingface_hub==1.33.0"', 'pip install -q -U "huggingface_hub==1.33.0"'), PINS) == []
    assert any("without a pinned sha" in w for w in D.static_problems(CLEAN.replace(f" && git -C /workspace/aitk checkout -q {SHA}", ""), PINS))
    assert any("not a sha of config/cloud_pins.json" in w for w in D.static_problems(CLEAN.replace(SHA, "a" * 40), PINS))
    assert any("`|| true` on an install" in w for w in D.static_problems(CLEAN.replace("1.33.0\"", "1.33.0\" || true"), PINS))
    assert any("`|| true`" in w for w in D.static_problems(CLEAN.replace("ai-toolkit /workspace/aitk &&", "ai-toolkit /workspace/aitk || true;"), PINS))
    assert any("no `DRY=1` gate" in w for w in D.static_problems(CLEAN.replace('[ "${DRY:-0}" = 1 ] && exit 0\n', ""), PINS))
    # the gate must come AFTER the last install: one before it does not count
    early = CLEAN.replace('[ "${DRY:-0}" = 1 ] && exit 0\n', "").replace("set -e\n", 'set -e\n[ "${DRY:-0}" = 1 ] && exit 0\n')
    assert any("no `DRY=1` gate" in w for w in D.static_problems(early, PINS))
    assert D.static_problems("echo hi > $EE_OUT/progress.txt\n", PINS) == []                  # no install: no gate needed


def test_only_a_sha_pins_a_git_install_and_a_multi_line_dry_gate_counts():
    """P1b review items 1-2 (the P2 thread): `@main` is the repo's HEAD of the day again; a correct multi-line gate was refused."""
    for ref in ("main", "v1.2.0", "e8c314f"):                                              # a branch, a tag, a short sha: all move or are ambiguous
        why = D.static_problems(CLEAN.replace("pip install -q ", f'pip install -q "git+https://github.com/a/b@{ref}" '), PINS)
        assert any("has no `@<40-hex sha>`" in w for w in why), ref
    ok = CLEAN.replace("pip install -q ", f'pip install -q "git+https://github.com/a/b@{SHA}" ')
    assert D.static_problems(ok, PINS) == []
    assert any("without `==`" in w for w in D.static_problems(CLEAN.replace('pip install -q "huggingface_hub==1.33.0"', 'pip install -q -U "x@git+https://h/x@main"'), PINS))
    multi = CLEAN.replace('[ "${DRY:-0}" = 1 ] && exit 0\n', 'if [ "${DRY:-0}" = 1 ]; then\n  echo "dry run ends here"\n  exit 0\nfi\n')
    assert D.static_problems(multi, PINS) == []
    wrong = CLEAN.replace('[ "${DRY:-0}" = 1 ] && exit 0\n', 'if [ "${DRY:-0}" = 1 ]; then\n  echo "dry"\nfi\nexit 0\n')   # the exit is not inside the gate
    assert any("no `DRY=1` gate" in w for w in D.static_problems(wrong, PINS))


def test_a_sha_pin_is_anchored_and_a_dry_gate_is_a_real_dry_is_1_test_whose_branch_exits_zero():
    """P1b review (P3b thread) of PR #49: `@main#egg=b@<sha>`, uppercase / 39 / 41 hex, and gates that only look like one."""
    def pinned(ref):
        return not any("has no `@<40-hex sha>`" in w for w in D.static_problems(
            CLEAN.replace("pip install -q ", f'pip install -q "git+https://github.com/a/b@{ref}" '), PINS))
    assert pinned(SHA) and pinned(SHA + "#egg=b") and pinned(SHA + "&subdirectory=x")
    for bad in ("main#egg=b@" + SHA, SHA[:39], SHA + "0", SHA.upper(), "x" + SHA[1:], "main"):   # a sha later in the url pins nothing
        assert not pinned(bad), bad
    assert any("without `==`" in w for w in D.static_problems(
        CLEAN.replace('pip install -q "huggingface_hub==1.33.0"', f'pip install -q -U "x@git+https://h/x@main#egg=x@{SHA}"'), PINS))

    gate = '[ "${DRY:-0}" = 1 ] && exit 0\n'

    def has_gate(block):
        return not any("no `DRY=1` gate" in w for w in D.static_problems(CLEAN.replace(gate, block), PINS))
    for good in (gate, 'if [ "${DRY:-0}" = 1 ]; then exit 0; fi\n', 'if [ "$DRY" -eq 1 ]\nthen\n  echo stop\n  exit 0\nfi\n',
                 'if [[ "${DRY:-}" == 1 ]]; then\n  echo stop; exit 0\nelse\n  echo go\nfi\n'):
        assert has_gate(good), good
    for bad in ('if [ "${DRY:-0}" = 0 ]; then exit 0; fi\n',                                     # exits when DRY is NOT 1
                'if [ "${DRY:-0}" = 1 ]; then\n  echo stop\nelse\n  exit 1\nfi\n',                # the exit is the other branch, and not 0
                'if [ "${DRY:-0}" = 1 ]; then\n  echo stop\nelse\n  exit 0\nfi\n',                # exit 0 in the else branch
                'if [ "${DRY:-0}" = 1 ]; then\n  if [ -f x ]; then exit 0; fi\nfi\n',               # exit only under a nested condition
                'if [ "${DRY:-0}" = 1 ]; then\n  exit 1\nfi\n',                                    # the dry run FAILS
                'echo "DRY=$DRY"\nexit 1\n', 'echo "DRY=$DRY"\n[ -f x ] && exit 0\n',            # a DRY mention and a later exit
                '[ "${DRY:-0}" = 0 ] && exit 0\n', 'DRY=1\nexit 0\n',
                '[ "${DRY:-0}" = 1 ] && return 0\n', 'if [ "${DRY:-0}" = 1 ]; then return 0; fi\n'):    # a top-level return only errors, the script goes on
        assert not has_gate(bad), bad


def test_backslash_continuations_are_one_command():
    text = CLEAN.replace("1.33.0\"", "1.33.0\" \\\n  || true")
    assert any("`|| true`" in w for w in D.static_problems(text, PINS))


def test_the_repo_ids_a_script_names_are_read_literally():
    ids = dict(D.repo_ids((PODS / "xworld_v2_loop.sh").read_text()))
    assert ids["vano1919/tmr-artifacts"] == "dataset" and ids["Qwen/Qwen-Image-2.1"] == "model"
    got = dict(D.repo_ids('# heartbeat: datasets/o/r:run/out/beat.txt\nhf download a/b --repo-type dataset\n'
                          "python -c 'snapshot_download(repo_id=\"c/d\")'\nx=$(snapshot_download(\"$X/y\"))\n"))
    assert got == {"o/r": "dataset", "a/b": "dataset", "c/d": "model"}          # a name computed at run time ($X) is not guessed


# --- the dry run: the record and the create refusals -------------------------------------------------------------------------
def test_run_looks_up_every_repo_and_a_missing_one_fails(tmp_path):
    seen = []

    def exists(rid, kind):
        seen.append((rid, kind))
        return (rid != "Qwen/Qwen-Image-2.1"), "no such repo"
    rec = D.run(CLEAN, exists=exists, pins=PINS)
    assert ("Qwen/Qwen-Image-2.1", "model") in seen and ("o/r", "dataset") in seen
    assert not rec["ok"] and any("Qwen/Qwen-Image-2.1" in p for p in rec["problems"])


def test_run_passes_a_clean_script_and_offline_never_passes():
    rec = D.run(CLEAN, exists=_ok, pins=PINS)
    assert rec["ok"], rec["problems"]
    off = D.run(CLEAN, exists=_ok, pins=PINS, offline=True)
    assert not off["ok"] and any("--offline" in p for p in off["problems"]) and all(r["ok"] is None for r in off["repos"])
    assert not D.run("if then\n", exists=_ok, pins=PINS)["ok"]                                  # bash -n


def test_the_record_is_keyed_by_the_script_text_and_the_pins(real_dryrun, tmp_path, monkeypatch):
    monkeypatch.setattr(D, "DIR", tmp_path / "dr")
    assert "no dry run of this script" in D.passed(CLEAN)[0]
    D.record(D.run(CLEAN, exists=_ok, pins=PINS))
    fixed = CLEAN
    assert D.passed(fixed) == []
    assert "no dry run of this script" in D.passed(fixed + "echo more\n")[0]                    # one changed byte = another script
    pf = tmp_path / "pins.json"
    pf.write_text(json.dumps(PINS))
    D.record({**D.run(fixed, exists=_ok, pins=PINS), "pins_sha": D.sha256_of(pf.read_text())})
    assert D.passed(fixed, pins_path=pf) == []
    pf.write_text(json.dumps({**PINS, "looked_up": "later"}))
    assert "changed after the dry run" in D.passed(fixed, pins_path=pf)[0]
    D.record(D.run(fixed, exists=lambda r, k: (False, "gone"), pins=PINS))                      # the same text, now failing: overwrites
    assert "failed" in D.passed(fixed)[0] and "gone" in D.passed(fixed)[0]


def test_create_refuses_a_script_without_a_passing_dryrun(real_dryrun, env, monkeypatch, tmp_path):
    fake, api, tmp = env
    monkeypatch.delenv("RUNPOD_POD_API_KEY", raising=False)
    monkeypatch.setattr(D, "DIR", tmp_path / "dr")
    with pytest.raises(SystemExit, match="no dry run of this script"):
        _create(api, tmp, NEW_SH, live=FakeLive(age=60))
    assert not fake.pods
    D.record(D.run(NEW_SH, exists=lambda r, k: (False, "no such repo"), pins=PINS))           # a record of a dry run that failed
    with pytest.raises(SystemExit, match="dry run of this script .* failed"):
        _create(api, tmp, NEW_SH, live=FakeLive(age=60))
    assert not fake.pods
    D.record(D.run(NEW_SH, exists=_ok, pins=PINS))
    assert D.passed(NEW_SH) == []


def test_create_refuses_an_unpinned_image_and_a_short_boot_on_community(env, monkeypatch):
    fake, api, tmp = env
    monkeypatch.delenv("RUNPOD_POD_API_KEY", raising=False)
    for image, match in (("ostris/aitoolkit:latest", "not pinned by digest"), ("ostris/aitoolkit@sha256:" + "0" * 64, "not in config/cloud_pins.json")):
        with pytest.raises(SystemExit, match=match):
            _create(api, tmp, NEW_SH, "--image", image, live=FakeLive(age=60))
    why = R.preflight_create(api, max_usd=0.5, max_hours=1.0, gpu="cheap", now=10**6, script=NEW_SH, heartbeat="x:b/beat.txt", pod_key=True,
                             image=P.image_ref("aitoolkit"), boot_minutes=10, cloud="COMMUNITY")
    assert any("--boot-minutes >= 25" in w for w in why)
    assert not any("boot-minutes" in w for w in R.preflight_create(api, max_usd=0.5, max_hours=1.0, gpu="cheap", now=10**6, script=NEW_SH,
                                                                     heartbeat="x:b/beat.txt", pod_key=True, image=P.image_ref("aitoolkit"),
                                                                     boot_minutes=25, cloud="COMMUNITY"))
    assert not any("boot-minutes" in w for w in R.preflight_create(api, max_usd=0.5, max_hours=1.0, gpu="cheap", now=10**6, script=NEW_SH,
                                                                     heartbeat="x:b/beat.txt", pod_key=True, image=P.image_ref("aitoolkit"),
                                                                     boot_minutes=10, cloud="SECURE"))


def test_create_runs_a_script_pod_on_the_pinned_digest_by_default_and_accepts_a_pin_key(env, monkeypatch):
    fake, api, tmp = env
    monkeypatch.delenv("RUNPOD_POD_API_KEY", raising=False)
    seen = []
    real = R.create
    monkeypatch.setattr(R, "create", lambda api, body, **kw: seen.append(body) or real(api, body, **kw))
    _create(api, tmp, NEW_SH, "--volume", "0", live=FakeLive(age=60))
    assert seen[0]["image"] == P.image_ref("tmr_pod") and seen[0]["env"]["EE_HF_PIN"] == PINS["pip"]["huggingface_hub"]["version"]


def test_the_dryrun_and_pins_commands(real_dryrun, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(D, "DIR", tmp_path / "dr")
    monkeypatch.setattr(D, "hf_exists", _ok)
    sf = tmp_path / "s.sh"
    sf.write_text("echo hi\n")                                                  # no upload loop, no wrapper marker: fails its lint
    with pytest.raises(SystemExit) as e:
        R.main(["dryrun", "--script", str(sf)], api=object())
    assert e.value.code == 1 and "dryrun FAILED" in capsys.readouterr().out
    good = CLEAN
    sf.write_text(good)
    R.main(["dryrun", "--script", str(sf)], api=object())
    assert f"dryrun ok sha256 {D.sha256_of(good)}" in capsys.readouterr().out and D.passed(good) == []
    with pytest.raises(SystemExit, match="needs --script"):
        R.main(["dryrun"], api=object())
    pt = tmp_path / "pins.txt"
    pt.write_text(f"git:ostris/ai-toolkit={SHA}\n")
    R.main(["pins", str(pt)], api=object())
    assert "pins ok" in capsys.readouterr().out
    pt.write_text("git:ostris/ai-toolkit=" + "f" * 40 + "\n")
    with pytest.raises(SystemExit):
        R.main(["pins", str(pt)], api=object())


# --- the wrapper's uploader (the paid plan's item 6) -------------------------------------------------------------------------
PY_STUB = """#!/bin/bash
for a in "$@"; do
  if [ "$a" = "import huggingface_hub" ]; then [ -f "$STUB_DIR/hf_installed" ] && exit 0 || exit 1; fi
done
exec %s "$@"
"""
PIP_STUB = """#!/bin/bash
echo "$*" >> "$STUB_DIR/pip.log"
[ "$STUB_PIP_FAILS" = 1 ] && exit 1
touch "$STUB_DIR/hf_installed"; exit 0
"""


def _stubs(stub):
    import shutil
    import stat
    real = shutil.which("python3")
    for name, text in (("python3", PY_STUB % real), ("pip", PIP_STUB)):
        p = stub / "bin" / name
        p.write_text(text)
        p.chmod(p.stat().st_mode | stat.S_IEXEC)


def test_the_wrapper_installs_the_pinned_huggingface_hub_when_the_image_lacks_it(wrapper):
    _stubs(wrapper.out.parent)
    p, beat, stops, stub = wrapper("echo done > $EE_OUT/progress.txt\n", EE_FORCE_HF_CHECK="1", EE_HF_PIN="1.33.0")
    assert "huggingface_hub==1.33.0" in (stub / "pip.log").read_text() and beat["word"] == "DONE" and stops


def test_the_wrapper_ends_the_pod_when_there_is_no_uploader_at_all(wrapper):
    _stubs(wrapper.out.parent)
    p, beat, stops, stub = wrapper("echo should-not-run > $EE_OUT/ran\n", EE_FORCE_HF_CHECK="1", EE_HF_PIN="1.33.0", STUB_PIP_FAILS="1")
    assert "no uploader" in p.stdout and "at 1.33.0" in p.stdout and not (wrapper.out / "ran").exists()   # the job never ran
    assert beat["word"] == "BAD_HOST" and stops                                                          # the pod was stopped
    (stub / "pip.log").unlink()
    p, beat, stops, stub = wrapper("echo should-not-run > $EE_OUT/ran2\n", EE_FORCE_HF_CHECK="1", STUB_PIP_FAILS="1")   # no pin: no pip call
    assert "no uploader" in p.stdout and not (stub / "pip.log").exists() and stops


def test_the_wrapper_with_a_stubbed_uploader_never_touches_pip(wrapper):
    _stubs(wrapper.out.parent)
    p, beat, stops, stub = wrapper("echo ok > $EE_OUT/progress.txt\n", EE_HF_PIN="1.33.0")
    assert beat["word"] == "DONE" and not (stub / "pip.log").exists()
