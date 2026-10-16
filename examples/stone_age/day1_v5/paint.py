"""Paint the Day 1 v5 pictures with Gemini (D-41, one engine). Estimate by default; --run <dir> paints, judges and writes a sheet.
The three style references are look-test frames the creator is shown first; every call is cached, logged and capped (80 %)."""
import io
import json
import sys
from pathlib import Path

from PIL import Image

from explainer_engine.imagegen.gemini import GeminiClient, estimate
from explainer_engine.qa import visual_judge as vj
from explainer_engine.world import resolver

HERE = Path(__file__).parent
MODEL, SIZE = "gemini-nano-banana-2.1", "2K"
REFS = ["m1_storm_wide", "m2_fire_argument", "a2_face_off"]
NOTE = (" Match the drawing style, ink line, colour treatment and mood of the attached reference pictures exactly (same artist, "
        "same series), but do not copy their composition or their people unless named above.")


def refs_from(look_dir: Path) -> list[bytes]:
    out = []
    for n in REFS:
        im = Image.open(look_dir / f"{n}.png").convert("RGB")
        im.thumbnail((1280, 720))
        b = io.BytesIO()
        im.save(b, "PNG")
        out.append(b.getvalue())
    return out


def main() -> None:
    P = json.loads((HERE / "prompts.json").read_text())
    world = resolver.resolve(json.loads((HERE / "world_spec.json").read_text()))
    n = len(P)
    print(f"{n} pictures, {MODEL} {SIZE}, {len(REFS)} references: estimate ${estimate(MODEL, SIZE, n, len(REFS)):.2f}")
    if "--run" not in sys.argv:
        return
    out = Path(sys.argv[sys.argv.index("--run") + 1])
    look_dir = Path(sys.argv[sys.argv.index("--look") + 1])
    only = sys.argv[sys.argv.index("--only") + 1].split(",") if "--only" in sys.argv else None
    c = GeminiClient(out, cap_usd=4.9)  # 80 % = $3.92 = what is left under the $10 Gemini cap after the look test
    refs = refs_from(look_dir)
    verdicts = {}
    for p in P:
        if only and p["id"] not in only:
            continue
        if "--judge-only" in sys.argv:
            path = out / f"{p['id']}.png"
        else:
            salt = f" Compose it differently from any earlier attempt (variation {sys.argv[sys.argv.index('--salt') + 1]})." if "--salt" in sys.argv else ""
            path = c.generate(p["id"], p["prompt"] + NOTE + salt, model=MODEL, size=SIZE, refs=refs)
        meta = {"plate": False, "hero": ", ".join(p["heroes"]) or None, "stakes": p["stakes"], "not_yet": p.get("not_yet", [])}
        try:
            ans = c.judge(path.read_bytes(), vj.build_prompt(world, meta))
            verdicts[p["id"]] = vj.verdict(vj.parse(ans), meta)
        except Exception as exc:  # the judge is advisory; a failed call never blocks a picture
            verdicts[p["id"]] = {"status": "REVIEW", "fails": [], "review": [f"judge error: {exc}"], "note": ""}
        print(p["id"], verdicts[p["id"]]["status"], round(c.spent, 3))
    (out / "judge.json").write_text(json.dumps(verdicts, indent=1))
    print("spent", round(c.spent, 3))


if __name__ == "__main__":
    main()
