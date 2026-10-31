"""The shot router (P6, CN-02): ``film_shots/2`` -> one ``shot_spec/1`` per renderable shot, plus ``shots/route.json``
(``shot_route/1``), all DERIVED: a spec is never written by hand and a stale one is refused by its inputs' sha256.

Route table (docs/CONTRACTS.md, "Shot router"):

    KEYFRAME_LTX   still spec (keyframe model + the xworld_v2 LoRA)  + video spec (LTX i2v from that keyframe)
    DIALOGUE_CU    the same two, and the video spec carries ``audio_slice_sha256`` (D-90: the ElevenLabs take conditions the
                   clip; its window is a recorded ``audio_spine/2.post_hoc_shots`` entry with a clip hash)
    ATMOS_BROLL    video spec only
    STILL_HOLD     still spec only
    MAP, COMPENSATOR   no spec: the route points at the ``visual_comp_manifest/1`` item(s) of the same ``shot_id``; none = refused
    HOST_COMMENTARY, DRAMA_BLOCKED_3D   refused (D-89, card A2): ``core/contracts`` raises before anything is routed

Prompts come from ``scripting/film_shots.compose`` (the one prompt writer, CT-13, KP-30); model ids, revisions and the LoRA's hash
from ``config/cloud_pins.json`` ``models`` through ``cloud/pins.load`` (CR-18). A model whose revision and sha256 are both null is
not decided: its lane is refused, nothing is guessed (OR-22). The seed of attempt N is ``SEEDS[N-1]`` (BP-165 ``max_tries`` tries).

    python -m explainer_engine.edit.router <film_shots.json> <job folder> --job-id ID [--comp M.json] [--spine S.json] [--attempt N]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from explainer_engine.cloud import pins as pins_mod
from explainer_engine.core import contracts as C
from explainer_engine.core import shot_cache
from explainer_engine.core.errors import ContractError
from explainer_engine.core.store import write_json_atomic
from explainer_engine.qa import keyframe_gate
from explainer_engine.scripting import film_shots
from explainer_engine.standards import sourced_rules as SR

SEEDS = (42, 1337, 9001)   # the creator's seeds per shot (brief 2026-10-31); one per try, BP-165 max_tries
STILL_RECIPE = "qwen_image_keyframe/1"
VIDEO_RECIPE = "ltx_i2v/1"
LORA_KEY = "xworld_v2"
HAS_STILL = {"KEYFRAME_LTX", "DIALOGUE_CU", "STILL_HOLD"}
HAS_VIDEO = {"KEYFRAME_LTX", "DIALOGUE_CU", "ATMOS_BROLL"}
HAS_COMP = {"MAP", "COMPENSATOR"}


def _rel(job: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(job.resolve()).as_posix()
    except ValueError:
        raise ContractError(f"{path} is not inside the job folder {job}: a derived file names its inputs relative to it (CN-02)")


def _ref(job: Path, path: Path) -> dict:
    return {"path": _rel(job, path), "sha256": C.sha256_file(path)}


def _model(pins: dict, key: str) -> dict:
    e = (pins.get("models") or {}).get(key)
    if e is None:
        raise ContractError(f"config/cloud_pins.json has no models.{key}: the lane cannot be routed (CR-18)")
    if not (e.get("sha256") or e.get("revision")):
        raise ContractError(f"model {e['id']} (models.{key}) has no revision or sha256 in config/cloud_pins.json: it is not decided, "
                            "so its lane is not routed (CN-07, CR-18, Rule one)")
    return {"id": e["id"], "sha256": e.get("sha256"), "revision": e.get("revision")}


def _lora(pins: dict, model_id: str) -> dict:
    e = ((pins.get("models") or {}).get("loras") or {}).get(LORA_KEY)
    if e is None or not e.get("sha256"):
        raise ContractError(f"models.loras.{LORA_KEY} has no sha256 in config/cloud_pins.json (CN-07)")
    try:
        keyframe_gate.check_stack(model_id, {e["id"]: e["weight"]})   # KG-16: a LoRA only into its own base
    except ValueError as exc:
        raise ContractError(str(exc)) from exc
    return {"id": e["id"], "sha256": e["sha256"], "weight": e["weight"]}


def _spine_window(spine: dict | None, shot_id: str, fps: int) -> dict:
    """The recorded window of a DIALOGUE_CU shot: it must exist, be a real clip with a hash, and sit at the job's fps."""
    if spine is None or spine.get("schema") != "audio_spine/2":
        raise ContractError(f"{shot_id}: DIALOGUE_CU needs an audio_spine/2 with a window for it (D-90)")
    if spine["fps"] != fps:
        raise ContractError(f"{shot_id}: the spine runs at {spine['fps']} fps, the shots at {fps} (CN-09)")
    for w in spine["post_hoc_shots"]:
        if w["shot_id"] == shot_id:
            if w["source"] != "clip" or not w.get("clip_sha256"):
                raise ContractError(f"{shot_id}: its spine window is still planned: the voice take is not recorded, so there is no "
                                    "audio slice to condition the clip on (D-90)")
            return w
    raise ContractError(f"{shot_id}: DIALOGUE_CU has no window in the audio spine's post_hoc_shots (D-90)")


def _card_refs(job: Path, shot: dict) -> list[dict]:
    """The references of the shot's continuity card (``continuity_ref`` = ``<file>#<shot id>``), each as role, path and hash."""
    ref = shot.get("continuity_ref")
    if not ref:
        return []
    name, _, sid = ref.partition("#")
    card = json.loads((job / name).read_text(encoding="utf-8"))
    row = next((s for s in card["shots"] if s["shot_id"] == (sid or shot["id"])), None)
    if row is None:
        raise ContractError(f"{shot['id']}: continuity_ref {ref} names no shot of {name}")
    out = []
    for r in row["refs"]:
        path = job / r["path"]
        if not path.exists():
            raise ContractError(f"{shot['id']}: reference {r['path']} of {name} does not exist (CN-02)")
        out.append({"role": r["role"], "path": r["path"], "sha256": C.sha256_file(path)})
    return out


def _spec(base: dict, **over) -> dict:
    return {"schema": "shot_spec/1", "negative": "", "loras": [], "frames": None, "audio_slice_sha256": None, "refs": [],
            "blocking_sha256": None, "params": {}, **base, **over}


def route(film_shots_path: Path | str, job_dir: Path | str, *, job_id: str, pins: dict | None = None,
          comp_manifest: Path | str | None = None, audio_spine: Path | str | None = None, attempt: int = 1) -> dict:
    """Write ``shots/<id>.still.spec.json`` / ``<id>.video.spec.json`` and ``shots/route.json`` under ``job_dir``; return the route."""
    job, fs_path = Path(job_dir), Path(film_shots_path)
    pins = pins if pins is not None else pins_mod.load()
    if not 1 <= attempt <= min(len(SEEDS), SR.T("BP-165", "max_tries")):
        raise ContractError(f"attempt {attempt}: there are {SR.T('BP-165', 'max_tries')} tries per shot, then the item stops (BP-165, OR-04)")
    seed = SEEDS[attempt - 1]
    doc = film_shots.load(fs_path)
    C.validate(doc)   # the lane refusals (D-89, A2), CN-08/09 geometry and the schema, before anything is routed
    fps = doc["fps"]
    manifest = job / "job_manifest.json"
    if manifest.exists():
        bad = [f for f in C.cross_fps(json.loads(manifest.read_text(encoding="utf-8")), doc) if f["severity"] == "FAIL"]
        if bad:
            raise ContractError("; ".join(f"{f['rule']} {f['where']}: {f['detail']}" for f in bad))
    derived = {"film_shots": _ref(job, fs_path)}
    comp = spine = None
    if comp_manifest is not None:
        comp = json.loads(Path(comp_manifest).read_text(encoding="utf-8"))
        C.validate(comp, job)
        derived["visual_comp_manifest"] = _ref(job, Path(comp_manifest))
    if audio_spine is not None:
        spine = json.loads(Path(audio_spine).read_text(encoding="utf-8"))
        C.validate(spine, job)
        derived["audio_spine"] = _ref(job, Path(audio_spine))
    prompts = {p["id"]: p for p in film_shots.compose(doc)}
    routes = []
    for shot in doc["shots"]:
        sid, lane = shot["id"], shot["lane"]
        entry = {"shot_id": sid, "lane": lane, "specs": [], "comp_items": []}
        if lane in HAS_COMP:
            items = [it["item_id"] for it in (comp or {}).get("items", []) if it["shot_id"] == sid]
            if not items:
                raise ContractError(f"{sid}: lane {lane} has no item with its shot_id in the visual_comp_manifest (CN-15, CMP-14)")
            entry["comp_items"] = items
            routes.append(entry)
            continue
        common = {"shot_id": sid, "job_id": job_id, "lane": lane, "seed": seed, "width": shot["width"], "height": shot["height"], "fps": fps}
        still_key = None
        if lane in HAS_STILL:
            first = prompts[f"{sid}.first"]
            model = _model(pins, "keyframe")
            inf = first["inference"]
            spec = _spec(common, prompt=first["prompt"], negative=first["neg"], model=model, loras=[_lora(pins, model["id"])],
                         refs=_card_refs(job, shot), recipe=STILL_RECIPE,
                         params={"steps": inf["steps"], "true_cfg": inf["true_cfg"], "dtype": inf["dtype"]})
            still_key = _write(job, entry, "still", spec)
        if lane in HAS_VIDEO:
            vid = prompts[f"{sid}.video"]
            slice_hash = _spine_window(spine, sid, fps)["clip_sha256"] if lane == "DIALOGUE_CU" else None
            # until the keyframe is accepted its file does not exist: the ref's sha256 is the still spec's cache key; the renderer
            # re-derives this video spec with the accepted PNG's real sha256 (docs/CONTRACTS.md "Shot router")
            refs = [{"role": "keyframe", "path": f"keyframes/{sid}.png", "sha256": still_key}] if still_key else []
            pin = (pins.get("models") or {}).get("video_ltx") or {}
            spec = _spec(common, prompt=vid["prompt"], negative=vid["neg"], model=_model(pins, "video_ltx"), frames=shot["duration_frames"],
                         audio_slice_sha256=slice_hash, refs=refs, recipe=VIDEO_RECIPE, params=dict(pin.get("params") or {}))
            _write(job, entry, "video", spec)
        routes.append(entry)
    out = {"schema": "shot_route/1", "job_id": job_id, "fps": fps, "derived_from": derived, "routes": routes}
    C.validate(out, job)
    write_json_atomic(job / "shots" / "route.json", out)
    return out


def _write(job: Path, entry: dict, role: str, spec: dict) -> str:
    """Validate and write one spec; the route entry records its file, file hash and cache key. Returns the cache key."""
    key = shot_cache.key(spec)   # validates the spec against shot_spec/1 first
    path = job / "shots" / f"{spec['shot_id']}.{role}.spec.json"
    write_json_atomic(path, spec)
    entry["specs"].append({"role": role, "path": _rel(job, path), "sha256": C.sha256_file(path), "cache_key": key})
    return key


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    opts = {}
    for flag, name in (("--job-id", "job_id"), ("--comp", "comp_manifest"), ("--spine", "audio_spine"), ("--attempt", "attempt")):
        if flag in argv:
            i = argv.index(flag)
            opts[name] = argv[i + 1]
            del argv[i:i + 2]
    if len(argv) != 2 or "job_id" not in opts:
        print(__doc__)
        return 2
    if "attempt" in opts:
        opts["attempt"] = int(opts["attempt"])
    try:
        out = route(argv[0], argv[1], **opts)
    except ContractError as exc:
        print(f"FAIL {exc}")
        return 1
    print(f"routed {len(out['routes'])} shots, {sum(len(r['specs']) for r in out['routes'])} specs -> {argv[1]}/shots/route.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
