"""Paint the three missing Day 1 pictures with Gemini from the Gemini reference frames (creator's one-off exception, 2026-10-16;
the pod was unavailable). One variant each, cached, logged, capped at $0.50 (the client stops at 80 %)."""
import io
import json
import sys
from pathlib import Path

from PIL import Image

from explainer_engine.imagegen.gemini import GeminiClient, estimate

HERE = Path(__file__).parent
MODEL, SIZE = "gemini-nano-banana-2.1", "2K"


def ref(pics: Path, pid: str) -> bytes:
    im = Image.open(pics / f"{pid}.png").convert("RGB")
    im.thumbnail((1280, 720))
    b = io.BytesIO()
    im.save(b, "PNG")
    return b.getvalue()


def main() -> None:
    doc = json.loads((HERE / "production_script.json").read_text())
    pics, out = Path(sys.argv[1]), Path(sys.argv[2])
    jobs = [s["picture"] for seg in doc["segments"] for s in seg["shots"] if isinstance(s["picture"], dict)
            and s["picture"].get("engine") == "pod_ref"]
    refs_n = sum(len(j["refs"]) for j in jobs)
    print(len(jobs), "pictures, estimate $", round(sum(estimate(MODEL, SIZE, 1, len(j["refs"])) for j in jobs), 4))
    if "--run" not in sys.argv:
        return
    if "--run" in sys.argv and "--force" not in sys.argv:  # audit 2026-10-19 H3: one-off painter outside the run ledger
        raise SystemExit("history: this one-off paints outside the run ledger; use `production.paint plan/approve/run` "
                         "(or add --force after the creator said yes)")
    c = GeminiClient(out, cap_usd=0.5)
    for j in jobs:
        p = c.generate(j["id"], j["prompt"], model=MODEL, size=SIZE, refs=[ref(pics, r) for r in j["refs"]])
        print(j["id"], p, round(c.spent, 4))
    print("spent", round(c.spent, 4))


if __name__ == "__main__":
    main()
