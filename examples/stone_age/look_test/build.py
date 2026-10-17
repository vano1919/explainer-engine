"""Look test (D-41 step 1): 4 masters + 2 alternates of the Stone Age in look v2. Builds, lints and prices the prompts; with
--run (after the creator's yes and a price shown) paints them with Gemini Pro and writes a contact sheet.
Pictures stay outside the repository."""
import json
import sys
from pathlib import Path

from explainer_engine.edit import prompt_v2
from explainer_engine.imagegen.gemini import GeminiClient, estimate
from explainer_engine.world import resolver

HERE = Path(__file__).parent
W = resolver.resolve(json.loads((HERE.parent / "world_spec.json").read_text()))
FRANKLIN = "Benjamin Franklin: balding crown with long grey hair, round spectacles, plump weathered face, brown frock coat"
NEWTON = "Isaac Newton: long wavy shoulder-length wig, long pale stern face, dark coat with a white cravat"
VISITOR_COSTUME = "muddy frock coats, waistcoats, long skirts and spectacles of the 1700s to 1900s"
HUNTERS = "hunter-gatherer adults in hides and furs tied with sinew, matted long hair, bone ornaments, painted-ochre faces"
SHOTS = [
 ("m1_storm_wide", "A", 1, True, False, "a hundred bewildered scientists in mixed-century clothes huddled and arguing in scattered "
  "clusters on an open limestone steppe under an approaching storm, small and exposed, no shelter anywhere, " + VISITOR_COSTUME),
 ("m2_fire_argument", "B", 3, True, False, f"two named heroes shouting at each other across a dying campfire, {FRANKLIN}; versus "
  f"{NEWTON}; Franklin shields the last small flame with both hands while Newton points an accusing finger, fear and anger, "
  "cold darkness closing in"),
 ("m3_hosts_watch", "B", 1, True, False, f"{HUNTERS}, a family of adult hunters crouching on the rocks above, watching the strangers "
  "below with wary curiosity and spears of wood and flint, dust blowing"),
 ("m4_hands_fire", "C", 3, True, False, "extreme close-up of two raw blistered adult hands held open to a small struggling fire, "
  "cracked skin, ash on the wrists, the cuff of a muddy frock coat, no faces"),
 ("a1_empty_ridge", "A", 1, False, True, "a bare windswept limestone ridge with dry grass bending in the wind and a river far below, "
  "wide empty open ground across the centre foreground, nothing standing on it"),
 ("a2_face_off", "B", 1, True, False, f"an adult hunter-gatherer elder in hides, {HUNTERS.split(',')[1]}, and {NEWTON}, facing each "
  "other three paces apart on the steppe, tense standoff, the elder holds a flint spear low, Newton raises an open palm, wary "
  "and baffled"),
]


def prompts():
    out = []
    for sid, typ, beat, people, plate, subject in SHOTS:
        hint = VISITOR_COSTUME if "frock" in subject or "scientists" in subject else ""
        p = prompt_v2.compose(typ, subject, W, beat, people=people, plate=plate, costume_hint=hint)
        findings = prompt_v2.lint(p, W, plate=plate, people=people, visitors_named=["newton", "franklin"])
        out.append({"id": sid, "prompt": p, "findings": findings})
    return out


if __name__ == "__main__":
    P = prompts()
    (HERE / "prompts.json").write_text(json.dumps(P, indent=1))
    bad = [f for x in P for f in x["findings"] if f["severity"] == "FAIL"]
    print(f"{len(P)} prompts, {len(bad)} FAIL, {sum(len(x['findings']) for x in P) - len(bad)} REVIEW; "
          f"estimate ${estimate('gemini-3-pro-image', '2K', len(P)):.3f}")
    for x in P:
        for f in x["findings"]:
            print(x["id"], f)
    if "--run" in sys.argv and not bad:
        out = Path(sys.argv[sys.argv.index("--run") + 1])
        c = GeminiClient(out, cap_usd=1.2)
        for x in P:
            c.generate(x["id"], x["prompt"], model="gemini-3-pro-image", size="2K")
        print("spent", round(c.spent, 3))
