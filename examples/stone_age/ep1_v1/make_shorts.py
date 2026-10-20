"""Episode 1 Shorts (SH-01..SH-04): five trailers that advertise the video. Writes the `shorts` block into production_script.json
(replacing any earlier one); the script is otherwise edited directly."""
import json
from pathlib import Path

P = Path(__file__).with_name("production_script.json")
doc = json.loads(P.read_text(encoding="utf-8"))


def L(text, **k):
    return {"text": text, **k}


SH = [
    {"id": "SH01", "source_period": "day1",
     "hook": "Could a hundred of history's smartest people light one fire before dark?",
     "lines": [L("Could a hundred of history's smartest people light one fire before dark?", tags=["softly", "intrigued"], emphasis=["dark"]),
               L("No matches. No lighter. Only what's in their pockets."),
               L("Nansen asks who can make fire. Two hands go up. Two. Out of a hundred.", tags=["deadpan"], emphasis=["hundred"]),
               L("He tries a bow drill. A dozen tries. Nothing but smoke.", tags=["sighs"]),
               L("Then Einstein takes off his reading glasses.", tags=["intrigued"]),
               L("A convex lens. The afternoon sun. One bright point on the grass.", tags=["softly"]),
               L("A thread of smoke. One careful breath... and FIRE.", tags=["whispers"], emphasis=["fire"]),
               L("That was only day one. The full story is on the channel.", tags=["warmly"])],
     "shots": [{"at": "Could a hundred", "picture": "v5_d1-31", "crop_x": 0.38, "zoom": 1.0},
               {"at": "Nansen asks", "picture": "v5_d1-32", "crop_x": 0.5, "zoom": 1.0},
               {"at": "Then Einstein", "picture": "v6_einstein_glasses", "crop_x": 0.62, "zoom": 1.0},
               {"at": "A convex lens.", "picture": "v6_lens_point", "crop_x": 0.7, "zoom": 1.0},
               {"at": "That was only", "picture": "v5_d1-36", "crop_x": 0.5, "zoom": 1.0}]},
    {"id": "SH02", "source_period": "week1",
     "hook": "How much grain does a hundred-person camp need every single day?",
     "lines": [L("How much grain does a hundred-person camp need every single day?", tags=["softly", "intrigued"], emphasis=["day"]),
               L("Seventy-five kilograms. Every. Day.", tags=["deadpan"]),
               L("Wallace cuts about two kilograms an hour with a flint sickle.", tags=["amused"]),
               L("Nansen does the sum, and the sum does not care how clever he is.", emphasis=["sum"]),
               L("By the end of the week, a third of the colony does nothing but grain.", tags=["slowly"]),
               L("And Newton? Newton hits a flint. The flint wins.", tags=["amused"], emphasis=["wins"]),
               L("Week one of a hundred geniuses in the Stone Age. The full story is on the channel.", tags=["warmly"])],
     "shots": [{"at": "How much grain", "picture": "w1_wallace_sickle", "crop_x": 0.42, "zoom": 1.0},
               {"at": "Nansen does", "picture": "w1_nansen_sum", "crop_x": 0.7, "zoom": 1.0},
               {"at": "By the end", "picture": "w1_grinders_rows", "crop_x": 0.5, "zoom": 1.0},
               {"at": "And Newton?", "picture": "w1_newton_flint", "crop_x": 0.4, "zoom": 1.0}]},
    {"id": "SH03", "source_period": "month1",
     "hook": "Why did the smartest people in history explode seven pots in a row?",
     "lines": [L("Why did the smartest people in history explode seven pots in a row?", tags=["softly", "intrigued"], emphasis=["seven"]),
               L("Marie Curie digs river clay with her bare hands.", tags=["warmly"]),
               L("But plain clay shrinks as it dries, and then it cracks.", tags=["slowly"]),
               L("Seven pots. Seven explosions.", tags=["deadpan"], emphasis=["explosions"]),
               L("So Newton does what Newton does. He measures.", tags=["amused"], emphasis=["measures"]),
               L("Eleven days later, one pot holds water. And then, at last, there is soup.", tags=["softly"]),
               L("A month into the Stone Age. The full story is on the channel.", tags=["warmly"])],
     "shots": [{"at": "Why did the", "picture": "m1_pots_cracked", "crop_x": 0.75, "zoom": 1.0},
               {"at": "Marie Curie digs", "picture": "m1_curie_clay", "crop_x": 0.32, "zoom": 1.0},
               {"at": "So Newton", "picture": "m1_newton_pot", "crop_x": 0.5, "zoom": 1.0},
               {"at": "Eleven days", "picture": "m1_soup", "crop_x": 0.6, "zoom": 1.0}]},
    {"id": "SH04", "source_period": "year10",
     "hook": "What stopped a hundred geniuses from making bronze?",
     "lines": [L("What stopped a hundred geniuses from making bronze?", tags=["softly", "intrigued"], emphasis=["bronze"]),
               L("Year ten. Marie Curie smelts a green rock into a bead of copper.", tags=["warmly"], emphasis=["copper"]),
               L("But copper is soft. A copper axe bends where a stone axe would chip.", tags=["slowly"]),
               L("Bronze needs tin, and there is almost no tin near here.", tags=["deadpan"], emphasis=["tin"]),
               L("Archaeologists still argue about where the ancient Near East found its tin.", tags=["thoughtful"]),
               L("Iron instead? Under two kilograms of iron swallows about forty kilograms of charcoal. A single knife costs a forest.", tags=["slowly"], emphasis=["forest"]),
               L("Ten years into the Stone Age. The full story is on the channel.", tags=["warmly"])],
     "shots": [{"at": "What stopped", "picture": "y10_axe_bend", "crop_x": 0.62, "zoom": 1.0},
               {"at": "Year ten.", "picture": "y10_malachite", "crop_x": 0.4, "zoom": 1.0},
               {"at": "But copper is", "picture": "y10_bead", "crop_x": 0.55, "zoom": 1.0},
               {"at": "Bronze needs", "picture": "y10_nansen_map", "crop_x": 0.72, "zoom": 1.0},
               {"at": "Iron instead?", "picture": "y10_charcoal", "crop_x": 0.62, "zoom": 1.0}]},
    {"id": "SH05", "source_period": "compare",
     "hook": "Would a hundred geniuses beat real history by thousands of years?",
     "lines": [L("Would a hundred geniuses beat real history by thousands of years?", tags=["softly", "intrigued"], emphasis=["thousands"]),
               L("In the real world, writing was still six thousand seven hundred years away.", tags=["slowly"]),
               L("They would bring it on day one.", tags=["warmly"], emphasis=["one"]),
               L("Copper smelting was five thousand years away. They would do it in ten.", tags=["amused"]),
               L("Knowledge is a time machine. For discoveries.", tags=["thoughtful"], emphasis=["discoveries"]),
               L("But a hundred geniuses is not a civilization.", tags=["slowly"], emphasis=["not"]),
               L("So who wins: the hundred, or the winter? The full video is on the channel.", tags=["warmly"], emphasis=["winter"])],
     "shots": [{"at": "Would a hundred", "picture": "c_road", "crop_x": 0.55, "zoom": 1.0},
               {"at": "Copper smelting", "picture": "y10_tesla_curie", "crop_x": 0.7, "zoom": 1.0},
               {"at": "But a hundred", "picture": "c_tiny_crowd", "crop_x": 0.5, "zoom": 1.0},
               {"at": "So who wins", "picture": "c_steam", "crop_x": 0.35, "zoom": 1.0}]},
]
doc["shorts"] = SH
P.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
print(len(SH), "shorts")
