# Picture review: Christmas Truce 1914, script A (2026-11-13)

Read-only review. I opened every picture with the image viewer and zoomed into the details named below. The script fields
come from `episodes/ep_truce_1914/story/production_script.json`. The prompts come from
`planning/gemini_task/messages/API_S3_newangles_p1..p3.md`.

**Overall: 24 pictures reviewed, 17 PASS, 7 FIX.** Most of the fixes are small local edits: painting out a lantern or a
candle, or pasting in a portrait.

---

## 1. Candle findings (group A)

**S03_SH003_start_n1 (night, the Germans singing).** The script says: "Friedrich and five Saxon soldiers stand in the
trench by the candle tree", "faces lit by candles", background "the candle tree small and soft on the parapet",
foreground "the dark edge of the trench wall".
- **The candle tree, top left of centre, behind the sandbags.** It is a small fir with about 13 lit candles. The script
  asks for it. Its size is right. It is sharper than "soft", but it reads well. **Fine.**
- **One candle on the parapet, top left, on the snowy sandbags by the wire.** The script does not ask for it, but it fits
  1914: German trenches set candles along the parapet that night. **Fine, harmless.**
- **Two tall pillar candles, bottom left (about x 380-860, y 1330-1536 at full size), in front of the left soldier's
  coat.** **These are the strange ones.** They stand on nothing: no holder, no hand, no ledge. Their bottoms are cut off
  by the frame. They are huge next to the men (each is as wide as a hand) and they hang in the air in front of his chest.
  The script does not ask for them, because its foreground is "the dark edge of the trench wall". **Wrong: they float, and
  they are too big and in the wrong place.**
- **Two coke braziers, bottom left corner and bottom right edge.** These are the open iron baskets the rules allow. The
  script does not name them, but they are period-correct and they help the "faces lit" look. **Fine.**
- **Two or three open fires burning on and behind the parapet, right background (and a small one at the centre right
  of the horizon), with smoke.** They are not candles. They read as things on fire after shelling, which fights the quiet
  "the song begins" moment. The script does not ask for them. **Wrong mood. Remove.**
- Likely cause: every prompt carries the world line "the only light sources are candles, coke braziers, matches...". That
  line plus "candle glow on the faces" seems to have invited extra candles in the foreground.

**S04_SH010_start_n1 (morning, no man's land).** There are no candles. There is one brazier glowing inside a dugout in
the British trench (middle left) and two small fire glows further down that trench. The script says nothing about them.
They are plausible morning fires. **Fine.**

**S04_SH012_start_n1.** There are no candles or flames, only smoke rising from the trench on the right. **Fine.**

**S04_SH014_start_n1.** There are no candles. There are two small braziers, one on each trench line (left and right,
far back), each with a smoke column. They are period-correct and symmetric, and they suit the "two sides" picture.
**Fine.**

**S05_SH009_start_n1.** There are no candles or flames. **Fine.**

**Candle verdict.** The owner's instinct is right, but only for S03_SH003. The two floating pillar candles at the bottom
left are not in the script, and so are the fires burning on the right parapet. The candle tree and the parapet candle
are what the script asks for. The four daylight pictures have no candle problems.

---

## 2. Verdict table

| # | Picture | Verdict | Problem (for FIX) | Smallest fix |
|---|---|---|---|---|
| A1 | S03_SH003_start_n1 | **FIX** | (a) Two floating pillar candles, bottom left, not in the script. (b) Open fires burning on and behind the parapet, right background, with a second glow at centre right; they read as shelling. Otherwise it is good: Friedrich is centred, singing and looking a little left, with two singers and the candle tree behind. The face matches the reference. There are no helmets or lanterns. | Local inpaint: replace the two candles with the dark trench wall or the coat, and replace the right parapet fires with night sky and sandbags. If you redraw instead, add "no candles in the foreground, no fires on the parapet". |
| A2 | S04_SH010_start_n1 | PASS | Thomas is centre left and faces right. Friedrich's grey shoulder and cap fill the right edge. Thomas's face matches the reference. The smile is gentle rather than "nervous", which is acceptable. | none |
| A3 | S04_SH012_start_n1 | PASS | It is an over-the-shoulder shot from behind Thomas. Friedrich is centre right, smiling, with his hand out. The hand is sound (five fingers). The background has fog, wire and ruins. | none |
| A4 | S04_SH014_start_n1 | PASS | Thomas is left and Friedrich right, side-on, shaking hands in the frozen field, with wire stakes in front. The figures are mid-size rather than "small", which is fine. | none |
| A5 | S05_SH009_start_n1 (raw) | FIX (already fixed in C) | The card shows a moustached man in uniform, but the story says it shows his wife and daughter. | Use the fixed copy from C1 (already done). |
| B1 | S04_SH009 mirror | PASS | Thomas is left and Friedrich right, two paces apart, facing each other. The trench niches hold candles. | none |
| B2 | S04_SH013 mirror | **FIX** | A **glass lantern** (box-frame lantern) stands on a crate in the left trench, at about x 430-480, y 780-880 at full size. That is a banned object. Thomas looking down at the offered hand matches the start state. | Paint out the lantern, or replace it with a candle stub on the crate. |
| B3 | S05_SH005 mirror | PASS (note) | Thomas is left offering a cigarette and Friedrich is right taking it; the hands are sound. Note: the two background Germans at the far left wear covered **Pickelhauben** (spiked leather helmets). They are not steel, so the rules do not ban them, and they are correct for 1914, but they break the house costume (round Feldmütze). | Optional: paint them into Feldmützen. |
| B4 | S05_SH007 mirror | PASS | Friedrich (right) strikes a match in cupped hands. Thomas (left) has a cigarette in his mouth. There is a candle in a trench niche. | none |
| B5 | S05_SH008 mirror | PASS | Thomas is left, smoking. Friedrich is right. There are braziers in the background. | none |
| B6 | S05_SH010 mirror | PASS | The khaki sleeve is left and the grey sleeve right, which now matches the sides. The card shows the woman. A mirrored photo carries no text, so the flip is invisible. Note: there is no little girl (see section 3). | none |
| B7 | S05_SH011 mirror | **FIX** | The card in Thomas's hands shows a **man in uniform**. That contradicts the story (wife and daughter), S05_SH010 and the fixed S05_SH009. | Paste the woman's portrait in the same way as C1. |
| B8 | S05_SH012 mirror | **FIX** | The card Friedrich slips into his pocket shows a **man in khaki/brown uniform** (about x 1650-1740, y 800-950). | Paste the woman's portrait the same way. The card is small, so a quick local paste is enough. |
| B9 | S05_SH013 mirror | PASS | Thomas is left, Friedrich right, both seated and side-on. Thomas looks down rather than "across the field", which is close enough. | none |
| B10 | S05_SH018 mirror | PASS | Friedrich holds his cap and stands bareheaded by a plain wooden cross with no lettering. Thomas is beside him on the left. | none |
| B11 | S06_SH002 mirror | PASS | Thomas is left and Friedrich right, side by side on one crate at sunset. There is a small fire stand in the foreground. | none |
| B12 | S06_SH003 mirror | **FIX (minor)** | Faint stencil-like letter marks on the crate face, bottom right (about x 2380-2560, y 1460-1500). After the flip they would read backwards. Text-like marks are banned. | Blur or smudge the marks on the crate. |
| B13 | S06_SH007 mirror | **FIX** | The same **glass lantern** on a crate in the left trench (about x 450-500, y 800-880). The rest is good: Friedrich looks toward the sun. | Paint out the lantern, or replace it with a candle. |
| B14 | S06_SH008 mirror | **FIX** | The same **glass lantern** in the left trench (about x 450-500, y 800-880). | Same fix as B13. |
| B15 | S06_SH010 mirror | PASS | Thomas (left) holds a brass button on his open palm. Friedrich (right) reaches to his own coat. The hands are sound. | none |
| B16 | S06_SH011 mirror | PASS | Friedrich holds the button out. Both faces are on-model. | none |
| B17 | S07_SH002 mirror | PASS | Thomas is left and Friedrich right, in fog with a gold glow. There are candles and a brazier in the trenches. | none |
| B18 | S07_SH003 mirror | **FIX** | The same **glass lantern** in the left trench (about x 450-500, y 800-880), dimmed by fog but still readable. | Same fix as B13. |
| C1 | S05_SH009_start_n1_card (fixed) | PASS (note) | The card now clearly shows a young woman with Edwardian piled-up hair. The paste is clean: the border and the curled corner are kept, and the gloved fingers sit correctly in front of the card's lower right. It is the same woman and hairstyle as the S05_SH010 card, so the two are consistent. Two small points: (1) the photo inside is a cooler neutral grey and a little more photographic than the warm painted border (a slight sepia warm-up would blend it better); (2) like S05_SH010, it shows only the woman, with **no little girl**. | Optional: warm the photo area toward sepia by about 10-15 %. |

---

## 3. Cross-picture problems

1. **Sides (Thomas left, Friedrich right).** These are correct in all 18 mirrored pictures and in all five new ones.
   The mirroring left no visible text or badge that reads backwards, apart from the faint crate marks in S06_SH003 (B12).
2. **The portrait card does not match across shots.** S05_SH009 (fixed), S05_SH010 and S03_SH002_r2 show the woman.
   **S05_SH011 and S05_SH012 still show a man.** That is the biggest continuity break in this set: the viewer sees the
   picture change in Thomas's hands. Also, **none** of the cards shows the little girl that the S05_SH010 script and the
   narration ("wife and daughter") ask for. If the girl matters, one shared card insert of the woman with a small girl
   in a white dress should be pasted into all five shots.
3. **A glass lantern sits in the reused left-trench background** of S04_SH013, S06_SH007, S06_SH008 and S07_SH003. It is
   the same box lantern on a crate each time, and it is banned. The other mirrored pictures with that trench (S04_SH009,
   S05_SH007, S05_SH011, S05_SH012, S06_SH003, S06_SH010) show candles in the niches, which is fine. Outside this review's
   scope, the old S03_SH002_r2 also shows a hanging lantern in the dugout doorway, and the old S03_SH003 (now replaced)
   had Stahlhelms. Replacing it was right.
4. **Friedrich's cap.** In every picture of this set it is drawn as a peaked cap with a black visor. The reference portrait
   shows a round, visorless Feldmütze. The drift is consistent across the whole film, so it does not jump between shots,
   but it does not match the reference sheet. Not flagged as FIX. Worth knowing before any repaint.
5. **Faces.** Thomas (freckles, sandy hair, grey eyes) and Friedrich (square face, dark-blond hair, full fair
   handlebar moustache) stay on-model in all 24 pictures. There are no melted faces and no extra fingers.
6. **Other banned objects.** None: no steel helmets on the heroes, no gas masks, tanks, machine pistols or modern
   clothing. The Pickelhauben in S05_SH005 are background extras and are leather, not steel (see B3).
7. **Light continuity, minor.** In the reverse shots S04_SH010 and S04_SH012 the sun is behind the subject in both. This
   is a normal cheat and is not flagged.
