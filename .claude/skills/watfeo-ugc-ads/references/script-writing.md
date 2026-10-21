# Writing the script

## Contents
1. Ad shapes that work for this book · 2. Hooks · 3. Spoken language (English, Hinglish, Hindi) · 4. Structure and timing ·
5. The CTA · 6. script.json format · 7. A worked example

## 1. Ad shapes (from Harsh's winners and the 7 creator references)
- **Talking selfie, one room** (book_0831, book_3, the references): she talks to the phone with the book in hand. The default.
- **Read-a-line**: she opens the book and reads one real line, then reacts. Needs the exact quote from `book_search.py`.
- **Which-one-are-you / tag a friend**: characters as types; drives comments.
- **Trope recs** ("book recs for every romantasy trope"): this book as the answer to one trope (friends-to-lovers, forced
  marriage, road trip, found family).
- **Haul / shelf moment**: she pulls it from a packed shelf or a stack; talk is about the story, not the paper (rule 8).
- **Podcaster mic**: holding a mic, "hot take" energy.
Avoid: cinematic re-enactments of the plot in a UGC ad (that is the Higgsfield "story trailer" style, a different format),
multi-room shoots, faceless page-flip only.

## 2. Hooks (the first 2 seconds decide it)
- Speech starts at 0.0 s, the book is in frame in frame 0, 7-14 words in the first 3 s (all 11 of Harsh's ads).
- Types that work: a question about the viewer's life; a specific surprising fact from the book ("He's scared to cross an empty
  road."); a challenge ("Tell me which one you are."); a contrarian take; a one-word cold open.
- The hook connects to a real-life moment the viewer has had (situationship, family pressure, the friend who notices), not to
  the book's plot alone.
- Put the hook as on-screen text too (white rounded box, black text, top band) when the top is empty.

## 3. Spoken language
- Write it the way a 22-30-year-old Indian reader talks to a friend. Contractions, fillers, a restart, a trailing "...".
- English: "honestly", "like", "literally", "okay but", "wait", "yes, that friend". Hinglish: "yaar", "matlab", "na", "toh",
  "basically", "arre", "sach mein". Hindi: casual daily Hindi, Romanized like the book prints its Hindi lines.
- Do not mirror sentence shapes between clips (that is copywriting). Vary length: one long run-on, then a two-word line.
- About 2.5-3 words per second. An 8-second clip holds 18-24 words; a 4-second clip 8-12.
- Names: Sagar, Malar, Harsh, Sai (and others only if the book has them). Pronounce "Chudesara" as written; captions take the
  script's spelling.

## 4. Structure and timing
- 4-6 clips of 8 s (or 4 s for punchy beats), 25-45 s total. Clip 1 = hook. Middle = the story beat(s) + the real-life link.
  Last clip = the title, the author, the CTA.
- One book state per clip (house rule 11); plan the states as a sequence: next to her face -> lap -> chest -> one hand ->
  cover to camera.
- Each clip's line must finish 0.5 s before the clip ends (nothing new in the last second).

## 5. The CTA (last clip, spoken)
"Read Now", "Shop Now" or "Abhi padhe", worked into a natural line: "...comment which one you are, and Read Now." Say the title
and "by Sagar Chudesara" in the last two clips. Optional, from the official facts only: "National Bestseller", "every order
comes with a signed letter from the author".

## 6. script.json (what `scripts/lint_script.py` checks)
```json
{"ad": "book-03", "angle": 13, "language": "en | hi | hinglish", "creator": "C7",
 "setup": "the ONE room, light, clothes and phone position, written once",
 "character": "the full text-only character prompt (see prompts.md)",
 "shots": [{"id": "s1", "seconds": 8, "book": "the book's state for the whole clip",
            "line": "exact spoken words",
            "image_prompt": "start picture for this beat (same woman, same room...)",
            "video_prompt": "phone setup + small motion + the exact line in quotes + one emotion + book state + what must not happen"}]}
```
`assets/example-script.json` is a complete, lint-clean example (book-02).

## 7. Worked example (book-02, angle #56)
1. "Every friend group has these four people. This book has all four. Tell me which one you are."
2. "Harsh. Six-pack, shirtless gym videos, shayari on his stories... and he's scared to cross an empty road. Like, actually scared."
3. "Sagar. Sends a love letter way too early. Gets rejected. And writes all of it in his diary. Yes, that friend."
4. "Malar, the topper, ninety-six percent. And Sai, the girl playing the dhol, who wants to take everyone to Hampi."
5. "It's called We Are There For Each Other, by Sagar Chudesara. Comment which one you are... and Read Now."
Every detail was found in the book first (p.48-49 six-pack/shayari, p.105 agoraphobia, p.2-3 the letter, p.92 the diary,
96% and CA in the early chapters, p.117 dhol-tasha, p.125 Hampi).
