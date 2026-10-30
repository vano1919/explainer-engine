"""The episode lifecycle (docs/CONTRACTS.md, CN-03..CN-06): only the next step, gates with approvals, named back paths."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from explainer_engine.core import contracts, store
from explainer_engine.core.errors import ContractError
from explainer_engine.core.store import EpisodeJob, LIFECYCLE

SHA = "c" * 64
CREATOR = {"kind": "creator", "by": "ვანო", "ref": "cmsg_1", "at": "2026-10-29T18:00:00", "sha256": SHA}
MACHINE = {"kind": "machine", "by": "gate", "ref": "report.json", "at": "2026-10-29T18:00:00", "sha256": None}
PLANNER = {"kind": "planner", "by": "opus-thread", "ref": "cmsg_2", "at": "2026-10-29T18:00:00", "sha256": SHA}


@pytest.fixture
def job(tmp_path):
    (tmp_path / "run.json").write_text(json.dumps({"reserved": {"pod:abc": {"service": "runpod_usd", "amount": 1.0}}}), encoding="utf-8")
    (tmp_path / "dossier.md").write_text("research", encoding="utf-8")
    return EpisodeJob.create(tmp_path, job_id="job-001", episode_slug="nap", ledger="run.json", fps=24)


class _Dir:
    def __init__(self, job_dir):
        self.job_dir = job_dir


def variants_file(job, write=True):
    """N-03: VARIANT_CHOSEN binds the script_variants.json the creator picked from (the Napoleon example, v1 picked);
    returns the file and the variants_sha256 his approval carries."""
    doc = json.loads((store.ROOT / "examples" / "napoleon_vs_genghis" / "script_variants.json").read_text(encoding="utf-8"))
    doc["chosen"] = {"variant_id": "v1", "by": "creator", "ref": "cmsg_1", "at": "2026-10-30T00:00:00Z",
                     "variants_sha256": contracts.variants_sha256(doc)}
    f = job.job_dir / "script_variants.json"
    if write:
        f.write_text(json.dumps(doc), encoding="utf-8")
    return f, doc["chosen"]["variants_sha256"]


def artifact_for(folder, gate):
    """N-03 option A (ვანო 2026-10-30): the artifact a person approves at ``gate``, written in ``folder``, and the hash its own tool
    records for it (scenario file, the script's words, the paint plan file, sample_approval.json, the bundle's manifest)."""
    from explainer_engine.imagegen import plan as P
    from explainer_engine.production import sample as SMP
    from explainer_engine.scripting import script_approval as SA
    folder = Path(folder)
    script = {"segments": [{"id": "S01", "lines": [{"speaker": "narrator", "text": "Napoleon looks east."}]}]}
    if gate == "SCENARIO_APPROVED":
        f = folder / "scenario.md"
        f.write_text("Napoleon meets Genghis Khan at the river.", encoding="utf-8")
        return f, store._sha256_file(f)
    if gate == "SCRIPT_APPROVED":
        f = folder / "production_script.json"
        f.write_text(json.dumps(script), encoding="utf-8")
        return f, SA.words_sha256(script)
    if gate == "BUDGET_RESERVED":
        plan = {"id": "p1", "provider": "gemini", "model": None, "size": None, "items": []}
        plan["hash"] = P.plan_hash(plan)
        f = folder / "plans" / "p1.json"
        f.parent.mkdir(exist_ok=True)
        f.write_text(json.dumps(plan), encoding="utf-8")
        return f, store._sha256_file(f)
    if gate == "SAMPLE_APPROVED":
        (folder / "production_script.json").write_text(json.dumps(script), encoding="utf-8")
        f = folder / SMP.FILE
        f.write_text(json.dumps({"approved_by": "ვანო", "approved_at": "2026-10-30", "ref": "cmsg_1",
                                 "script_sha256": SMP.sha256(folder / "production_script.json")}), encoding="utf-8")
        return f, store._sha256_file(f)
    if gate == "REVIEW_APPROVED":
        d = folder / "review_bundle"
        d.mkdir(exist_ok=True)
        (d / "final.mp4").write_bytes(b"video")
        (d / "notes.md").write_text("QA PASS", encoding="utf-8")
        from explainer_engine.qa import review_bundle
        f = review_bundle.write(d)
        return f, store._sha256_file(f)
    raise KeyError(gate)


def step(job, to):
    kind = next(iter(store.GATES[to]))
    approval = {"creator": CREATOR, "machine": MACHINE}[kind if kind in ("creator", "machine") else "creator"]
    extra = {}
    if to == "VARIANT_CHOSEN":
        extra["variants"], sha = variants_file(job)
        approval = {**approval, "sha256": sha}
    if to == "RESEARCHED":
        extra["dossier"] = job.job_dir / "dossier.md"
    if to == "BUDGET_RESERVED":
        extra["reservation_id"] = "pod:abc"
    if to in store.BOUND_GATES:  # option A: the artifact and the hash its tool records
        extra["artifact"], sha = artifact_for(job.job_dir, to)
        approval = {**approval, "sha256": sha}
    job.move(to, reason=f"to {to}", approval=approval, **extra)


def walk(job, upto):
    for to in LIFECYCLE[1:LIFECYCLE.index(upto) + 1]:
        step(job, to)


def snapshot(job):
    return (job.job_dir / store.MANIFEST).read_text(encoding="utf-8")


def test_the_full_forward_walk(job):
    walk(job, "PUBLISHED_PUBLIC")
    m = EpisodeJob.open(job.job_dir).manifest
    assert m["state"] == "PUBLISHED_PUBLIC" and [h["to"] for h in m["history"]] == list(LIFECYCLE)
    assert m["source_dossier_sha256"] and m["budget_reservation_id"] == "pod:abc"
    with pytest.raises(ContractError):
        job.abort("ABORTED_SPEND_CAP", reason="late")
    with pytest.raises(ContractError):
        job.back("repair", reason="late")


def test_a_skipped_step_is_refused_and_writes_nothing(job):
    before = snapshot(job)
    with pytest.raises(ContractError):
        job.move("SCRIPT_APPROVED", reason="skip", approval=CREATOR)
    assert snapshot(job) == before and job.state == "CREATED"


def test_a_gate_needs_its_approval_kind_and_a_creator_needs_a_ref(job):
    walk(job, "RESEARCHED")
    f, sha = variants_file(job)
    for bad in (None, MACHINE, {**CREATOR, "ref": ""}, {**CREATOR, "by": ""}, {**CREATOR, "sha256": None}):
        with pytest.raises(ContractError):
            job.move("VARIANT_CHOSEN", reason="x", approval=bad, variants=f)
    job.move("VARIANT_CHOSEN", reason="x", approval={**CREATOR, "sha256": sha}, variants=f)


def test_researched_fixes_the_dossier_once(job):
    walk(job, "VARIANT_CHOSEN")
    first = job.manifest["source_dossier_sha256"]
    assert first
    job.back("variant_changed", reason="another variant")  # back at RESEARCHED: the dossier stays the job's
    assert job.state == "RESEARCHED" and job.manifest["source_dossier_sha256"] == first
    with pytest.raises(ContractError):  # never create a manifest over an existing one
        EpisodeJob.create(job.job_dir, job_id="j", episode_slug="s", ledger="run.json", fps=24)
    with pytest.raises(ContractError):  # RESEARCHED is not the next step from RESEARCHED: another dossier is another job
        job.move("RESEARCHED", reason="again", approval=MACHINE, dossier=job.job_dir / "dossier.md")


def test_budget_needs_a_reservation_the_ledger_holds_and_accepts_a_planner(job):
    walk(job, "STORYBOARDED")
    for rid in (None, "pod:missing"):
        with pytest.raises(ContractError):
            job.move("BUDGET_RESERVED", reason="x", approval=CREATOR, reservation_id=rid)
    with pytest.raises(ContractError):
        job.move("BUDGET_RESERVED", reason="x", approval=MACHINE, reservation_id="pod:abc")
    plan, sha = artifact_for(job.job_dir, "BUDGET_RESERVED")  # option A: the planner's approval binds the plan file
    job.move("BUDGET_RESERVED", reason="OR-24", approval={**PLANNER, "sha256": sha}, reservation_id="pod:abc", artifact=plan)
    assert job.manifest["budget_reservation_id"] == "pod:abc"


def test_every_named_back_path_once_and_a_wrong_one_is_refused(job):
    walk(job, "REVIEW_APPROVED")
    with pytest.raises(ContractError):
        job.back("plan_changed", reason="wrong state")  # leaves BUDGET_RESERVED only
    with pytest.raises(ContractError):
        job.back("made_up", reason="x")
    with pytest.raises(ContractError):
        job.back("post_review_fix", reason="x")  # the creator's word is needed after approval #2
    job.back("post_review_fix", reason="fix", approval=CREATOR)
    assert job.state == "ASSETS"
    for path, (sources, to) in store.BACK_PATHS.items():
        if path == "post_review_fix":
            continue
        fresh = EpisodeJob.create(job.job_dir / path, job_id=path, episode_slug="n", ledger="../run.json", fps=24)
        (job.job_dir / path / "dossier.md").write_text("d", encoding="utf-8")
        for to_state in LIFECYCLE[1:LIFECYCLE.index(sources[0]) + 1]:
            step(fresh, to_state)  # the same approvals, dossier and reservation; VARIANT_CHOSEN with its variants file (N-03)
        fresh.back(path, reason="named path")
        assert fresh.state == to and fresh.manifest["history"][-1]["path"] == path


def test_going_back_past_the_budget_clears_it_and_the_approvals_beyond(job):
    walk(job, "SAMPLE_APPROVED")
    job.back("words_changed", reason="a word changed (OR-17)")
    assert job.state == "SCENARIO_APPROVED" and job.manifest["budget_reservation_id"] is None
    assert set(job.manifest["approvals"]) <= set(LIFECYCLE[:LIFECYCLE.index("SCENARIO_APPROVED") + 1])


def test_abort_and_reopen(job):
    walk(job, "STORYBOARDED")
    job.abort("ABORTED_SPEND_CAP", reason="80 % of runpod_usd")
    assert job.state == "ABORTED_SPEND_CAP" and job.manifest["reopen_to"] == "STORYBOARDED"
    with pytest.raises(ContractError):
        job.move("BUDGET_RESERVED", reason="x", approval=CREATOR, reservation_id="pod:abc")
    with pytest.raises(ContractError):
        job.reopen(reason="x", approval=MACHINE)
    job.reopen(reason="the creator raised the cap", approval=CREATOR)
    assert job.state == "STORYBOARDED" and job.manifest["reopen_to"] is None


def test_published_public_is_the_creators_click(job):
    walk(job, "STAGED_UNLISTED")
    with pytest.raises(ContractError):
        job.move("PUBLISHED_PUBLIC", reason="auto", approval=MACHINE)
    job.move("PUBLISHED_PUBLIC", reason="Studio click", approval=CREATOR)


def test_artifacts_do_not_cross_jobs_or_dossiers(tmp_path):
    a = tmp_path / "jobs" / "nap" / "job-001"
    b = tmp_path / "jobs" / "nap" / "job-002"
    for d in (a, b):
        d.mkdir(parents=True)
        (d / "run.json").write_text("{}", encoding="utf-8")
        (d / "dossier.md").write_text("d", encoding="utf-8")
    ja = EpisodeJob.create(a, job_id="job-001", episode_slug="nap", ledger="run.json", fps=24)
    (b / "cover.png").write_bytes(b"cover of job B")
    with pytest.raises(ContractError):
        ja.record_artifact("cover", b / "cover.png")
    (a / "cover.png").write_bytes(b"cover of job A")
    ja.record_artifact("cover", "cover.png")
    ja.check_artifact("cover")
    (a / "cover.png").write_bytes(b"changed")
    with pytest.raises(ContractError):
        ja.check_artifact("cover")
    (a / "cover.png").write_bytes(b"cover of job A")
    ja.check_artifact("cover")
    ja.move("RESEARCHED", reason="x", approval=MACHINE, dossier=a / "dossier.md")  # the dossier hash moves: the cover predates it
    with pytest.raises(ContractError):
        ja.check_artifact("cover")


def test_a_creator_gate_binds_the_sha256_of_what_was_approved(job):
    walk(job, "RESEARCHED")
    f, sha = variants_file(job)
    with pytest.raises(ContractError, match="binds the sha256"):
        job.move("VARIANT_CHOSEN", reason="x", approval={**CREATOR, "sha256": None}, variants=f)
    job.move("VARIANT_CHOSEN", reason="x", approval={**CREATOR, "sha256": sha}, variants=f)
    assert job.manifest["approvals"]["VARIANT_CHOSEN"]["sha256"] == sha  # the variants the creator picked from (N-03)


def gates_up_to(state):
    """The approvals an owner must show to adopt into ``state``: the right kind for every gate on the way."""
    out = {}
    for s in LIFECYCLE[1:LIFECYCLE.index(state) + 1]:
        kind = sorted(store.GATES[s])[0]
        out[s] = {"creator": CREATOR, "planner": PLANNER, "machine": MACHINE}[kind]
    if "VARIANT_CHOSEN" in out:  # the pick binds the variants file the ``folder`` fixture writes (adopt checks it as move does)
        out["VARIANT_CHOSEN"] = {**out["VARIANT_CHOSEN"], "sha256": variants_file(_Dir(store.ROOT), write=False)[1]}
    for g in (g for g in store.BOUND_GATES if g in out):  # option A: each person's gate carries its artifact's hash
        out[g] = {**out[g], "sha256": _bound_hashes()[g]}
    return out


def _bound_hashes():
    """The hash of every bound gate's artifact as ``artifact_for`` writes it; the content is fixed, so any folder gives the same."""
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        return {g: artifact_for(d, g)[1] for g in store.BOUND_GATES}


def artifacts_in(folder):
    return {g: artifact_for(folder, g)[0] for g in store.BOUND_GATES}


ADOPT = dict(job_id="a", episode_slug="a", ledger="run.json", fps=24)


@pytest.fixture
def folder(tmp_path):
    (tmp_path / "run.json").write_text(json.dumps({"reserved": {"pod:abc": {"service": "runpod_usd", "amount": 1.0}}}), encoding="utf-8")
    (tmp_path / "dossier.md").write_text("research", encoding="utf-8")
    variants_file(_Dir(tmp_path))  # adopting past the pick names this file (T5's review of N-03)
    return tmp_path


def test_an_existing_episode_is_adopted_through_every_gate_on_the_way(folder):
    job = EpisodeJob.adopt(folder, state="SCRIPT_APPROVED", reason="Titans, approved 2026-10-20", approvals=gates_up_to("SCRIPT_APPROVED"),
                           dossier=folder / "dossier.md", variants=folder / "script_variants.json",
                           artifacts=artifacts_in(folder), **ADOPT)
    m = EpisodeJob.open(folder).manifest
    assert m["history"][0]["path"] == "adopted" and m["state"] == "SCRIPT_APPROVED"
    assert set(m["approvals"]) == {"RESEARCHED", "VARIANT_CHOSEN", "SCENARIO_APPROVED", "SCRIPT_APPROVED"}
    assert m["source_dossier_sha256"] == store._sha256_file(folder / "dossier.md")
    job.move("STORYBOARDED", reason="next", approval=MACHINE)  # an adopted job continues on the normal path


def test_adopting_is_no_way_round_the_gates(tmp_path, folder):
    # the review's case: STAGED_UNLISTED with only a machine approval skips the creator's REVIEW_APPROVED on the way to the click
    only_target = {"STAGED_UNLISTED": MACHINE}
    with pytest.raises(ContractError, match="gate"):
        EpisodeJob.adopt(folder, state="STAGED_UNLISTED", reason="x", approvals=only_target, dossier=folder / "dossier.md", **ADOPT)
    skipped = gates_up_to("STAGED_UNLISTED")
    skipped["REVIEW_APPROVED"] = MACHINE  # CN-06 / invariant 4: approval #2 is the creator's
    with pytest.raises(ContractError):
        EpisodeJob.adopt(folder, state="STAGED_UNLISTED", reason="x", approvals=skipped, dossier=folder / "dossier.md",
                         reservation_id="pod:abc", **ADOPT)
    unbound = gates_up_to("SCRIPT_APPROVED")
    unbound["SCRIPT_APPROVED"] = {**CREATOR, "sha256": None}  # CN-04: bound to the words
    with pytest.raises(ContractError, match="binds the sha256"):
        EpisodeJob.adopt(folder, state="SCRIPT_APPROVED", reason="x", approvals=unbound, dossier=folder / "dossier.md", **ADOPT)
    with pytest.raises(ContractError, match="not reached"):
        EpisodeJob.adopt(folder, state="RESEARCHED", reason="x", approvals={**gates_up_to("RESEARCHED"), "SCRIPT_APPROVED": CREATOR},
                         dossier=folder / "dossier.md", **ADOPT)
    for state in ("PUBLISHED_PUBLIC", "ABORTED_SPEND_CAP", "NOPE"):  # nothing is adopted into the click, a terminal state or a typo
        with pytest.raises(ContractError):
            EpisodeJob.adopt(folder, state=state, reason="x", approvals=gates_up_to("STAGED_UNLISTED"), dossier=folder / "dossier.md",
                             reservation_id="pod:abc", **ADOPT)
    assert not (folder / store.MANIFEST).exists()


def test_nothing_is_adopted_into_the_public_click_even_with_every_approval(folder):
    full = gates_up_to("PUBLISHED_PUBLIC")  # every gate shown, the creator's click included
    assert full["PUBLISHED_PUBLIC"]["kind"] == "creator"
    with pytest.raises(ContractError, match="public click"):
        EpisodeJob.adopt(folder, state="PUBLISHED_PUBLIC", reason="x", approvals=full, dossier=folder / "dossier.md",
                         reservation_id="pod:abc", **ADOPT)
    assert not (folder / store.MANIFEST).exists()


@pytest.mark.parametrize("state", LIFECYCLE[:-1])
def test_the_full_chain_adopts_into_every_state_before_the_click(folder, state):
    job = EpisodeJob.adopt(folder, state=state, reason="chain", approvals=gates_up_to(state), dossier=folder / "dossier.md",
                           reservation_id="pod:abc", variants=folder / "script_variants.json",
                           artifacts=artifacts_in(folder), **ADOPT)
    assert job.state == state and set(job.manifest["approvals"]) == set(LIFECYCLE[1:LIFECYCLE.index(state) + 1])
    assert EpisodeJob.open(folder).state == state
    for _ in LIFECYCLE[LIFECYCLE.index(state) + 1:-1]:  # an adopted job walks on to the last state before the click
        nxt = LIFECYCLE[LIFECYCLE.index(job.state) + 1]
        kind = sorted(store.GATES[nxt])[0]
        variants, approval = None, {"creator": CREATOR, "planner": PLANNER, "machine": MACHINE}[kind]
        artifact = None
        if nxt == "VARIANT_CHOSEN":  # N-03: the pick binds its script_variants.json
            variants, sha = variants_file(job)
            approval = {**approval, "sha256": sha}
        if nxt in store.BOUND_GATES:  # option A
            artifact, sha = artifact_for(folder, nxt)
            approval = {**approval, "sha256": sha}
        job.move(nxt, reason="on", approval=approval, reservation_id="pod:abc" if nxt == "BUDGET_RESERVED" else None, artifact=artifact,
                 dossier=folder / "dossier.md" if nxt == "RESEARCHED" else None, variants=variants)
    assert job.state == "STAGED_UNLISTED"


def test_adopting_names_the_dossier_file_and_the_reservation(folder):
    ok = gates_up_to("SCRIPT_APPROVED")
    for dossier in (None, folder / "missing.md"):
        with pytest.raises(ContractError, match="dossier"):
            EpisodeJob.adopt(folder, state="SCRIPT_APPROVED", reason="x", approvals=ok, dossier=dossier, **ADOPT)
    budget = gates_up_to("BUDGET_RESERVED")
    for rid in (None, "pod:missing"):
        with pytest.raises(ContractError, match="reservation"):
            EpisodeJob.adopt(folder, state="BUDGET_RESERVED", reason="x", approvals=budget, dossier=folder / "dossier.md",
                             reservation_id=rid, **ADOPT)
    assert not (folder / store.MANIFEST).exists()
    job = EpisodeJob.adopt(folder, state="BUDGET_RESERVED", reason="x", approvals=budget, dossier=folder / "dossier.md",
                           reservation_id="pod:abc", variants=folder / "script_variants.json",
                           artifacts=artifacts_in(folder), **ADOPT)
    assert job.manifest["budget_reservation_id"] == "pod:abc"
    with pytest.raises(ContractError):  # never over an existing manifest
        EpisodeJob.adopt(folder, state="CREATED", reason="x", approvals={}, **ADOPT)


def test_adopt_refuses_a_directory_dossier_and_non_dict_approvals(folder):
    with pytest.raises(ContractError, match="dossier"):
        EpisodeJob.adopt(folder, state="RESEARCHED", reason="x", approvals=gates_up_to("RESEARCHED"), dossier=folder, **ADOPT)
    for bad in (None, [], "x"):
        with pytest.raises(ContractError, match="approvals"):
            EpisodeJob.adopt(folder, state="RESEARCHED", reason="x", approvals=bad, dossier=folder / "dossier.md", **ADOPT)
    assert not (folder / store.MANIFEST).exists()


def test_create_makes_only_the_initial_state(folder):
    with pytest.raises(TypeError):
        EpisodeJob.create(folder, state="PUBLISHED_PUBLIC", **ADOPT)  # type: ignore[call-arg]
    assert EpisodeJob.create(folder, **ADOPT).state == "CREATED"
    assert EpisodeJob.adopt(folder / "n", state="CREATED", reason="new", approvals={}, **ADOPT).state == "CREATED"


def test_a_cached_render_and_the_asset_library_may_be_recorded_but_not_a_stray_assets_folder(tmp_path, monkeypatch):
    cache = tmp_path / "cache"
    monkeypatch.setenv("EXPLAINER_SHOT_CACHE", str(cache))
    jd = tmp_path / "jobs" / "nap" / "job-001"
    jd.mkdir(parents=True)
    job = EpisodeJob.create(jd, job_id="job-001", episode_slug="nap", ledger="run.json", fps=24)
    (cache / "ab" / "abc").mkdir(parents=True)
    (cache / "ab" / "abc" / "clip.mp4").write_bytes(b"clip")
    job.record_artifact("clip_s1", cache / "ab" / "abc" / "clip.mp4")
    stray = tmp_path / "somewhere" / "assets" / "x.png"  # a path that merely contains "assets" is not the library
    stray.parent.mkdir(parents=True)
    stray.write_bytes(b"x")
    with pytest.raises(ContractError):
        job.record_artifact("stray", stray)
