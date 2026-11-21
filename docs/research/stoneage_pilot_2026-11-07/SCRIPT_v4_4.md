# Stone-age pilot: SCRIPT v4.4 — 459 words for 165 s — DRAFT
Changes vs v4.3: leading `<break>` tags became `[DELAY: +Ns]` on the speaker label (edit-time silence, stripped before TTS, so the model cannot shorten them). Changes vs v4.2: narrator em dashes replaced (S04, S07, S10); cut-off lines use "--" in both places (S08, S09); [OVERLAP]/[CUT] editing tags sit LEFT of the colon on the speaker label; `<break>` stays INSIDE the spoken text, right of the colon.
Build rule: the TTS builder strips every `[OVERLAP: ..]`/`[CUT: ..]`/`[DELAY: ..]` (they live only on the label, never in the text sent to ElevenLabs); those two tags only feed the FFmpeg/edit timing.


## S01
NARRATOR (Odom): Marcus Hale delivers sandwiches in Manhattan.
NARRATOR (Odom): Tonight, he steps in a puddle.
NARRATOR (Odom): He lands in snow.

## S02
NARRATOR (Odom): Forty thousand years back. A mammoth herd walks by.
MARCUS: Okay. Okay. That's not a pigeon. That's a mammoth.
NARRATOR (Odom): Phone at fourteen percent. No plan.

## S03
NARRATOR (Odom): Spears. Right at his throat.
MARCUS: Guys, c'mon. I just deliver sandwiches!
NARRATOR (Odom): Then a drum. One beat. They step back.

## S04
NARRATOR (Odom): The old man in the antlers lowers his drum. He called Marcus here.
URA (Frederick): Mountains of light I saw, in my sleep. Out of them, you walked.
MARCUS [OVERLAP: -0.45s]: Out of... what? Man, I was crossing Forty-Second.
URA (Frederick): Quiet. The fire is listening.
NARRATOR (Odom): Behind Ura, fresh red paint on the rock. And one space left empty.

## S05
NARRATOR (Odom): Marcus owns a bike and a phone. He can't make fire. He can't cut a blade.
MARCUS: I had a lighter. Back home. In my... other pants.
MARCUS: Okay. Sticks. I rub sticks. Nothing's happening!
URA (Frederick): Your head is full of stone towers. Your hands know nothing.
NARRATOR (Odom): Eight million people back home. Not one of them here to strike a spark.

## S06
NARRATOR (Odom): He does the one thing he can.
NARRATOR (Odom): Phone light. On.
NARRATOR (Odom): White light floods the cave. The hunters drop to their knees.

## S07
NARRATOR (Odom): Gods get meat, furs, and sticky little fingers on the screen.
CHILD: Is light inside the stone-thing?
CHILD: Can I eat it?
MARCUS: No, buddy. Don't eat the phone.
MARCUS: Guys, please, stand up. I'm not... okay. Hi.
NARRATOR (Odom): Each night, Marcus keeps the light on a little shorter.

## S08
NARRATOR (Odom): Nine percent. He rations the flash three seconds a night.
MARCUS: Look, nine percent, if I turn it on again it's gonna--
URA (Frederick) [OVERLAP: -0.45s]: Again. For the people.
NARRATOR (Odom): And Ura counts the nights.

## S09
NARRATOR (Odom): The screen dies. Everyone sees it.
URA (Frederick): Enough. Put down the spears. Look at him. A man. Only a man.
MARCUS: Yeah. I'm just a guy, I'm--
URA (Frederick) [CUT: -0.25s]: A man. Then tell me, man. Why would I open the way for you?

## S10
NARRATOR (Odom): A whole wall of red hands.
URA (Frederick): My mother's hand. Her mother's hand. All here.
MARCUS: Wow. Okay. That's older than my whole city.
MARCUS: Wait. That empty spot by your hand... you saved that for me?
NARRATOR (Odom): Forty thousand years of skyline. Started with wet red dirt on rock.

## S11
MARCUS: Let me go.
MARCUS: Forty thousand years from now, people stand in front of your hand.
MARCUS: They go quiet.
URA (Frederick) [DELAY: +0.7s]: Quiet. Yes. That is what a hand does to stone.
MARCUS [DELAY: +0.9s]: If you keep me here, all you get is a guy who can't start a fire.

## S12
NARRATOR (Odom): Storm. Torches. Hunters block the gate.
NARRATOR (Odom): A dead black glass. A fake god. The hunters raise their spears.

## S13
NARRATOR (Odom): Ura drums.
NARRATOR (Odom): Marcus slaps his palm on stone.
URA (Frederick): Go home, light-walker.
MARCUS: Thanks. Seriously.

## S14
NARRATOR (Odom): Fire runs up the wall.
NARRATOR (Odom): Gold floods the paintings.
NARRATOR (Odom): Wet red clay. His palm beside Ura's.

## S15
(no lines: spears lower, 1.0 s full silence)

## S16
NARRATOR (Odom) [DELAY: +2.0s]: Rain. A horn. Ochre on his fingers.
NARRATOR (Odom): In a museum window, two handprints. One bigger.
MARCUS: Okay. Okay. I'm home.