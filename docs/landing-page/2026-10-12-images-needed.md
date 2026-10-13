# Images and facts needed for the landing pages (12 Oct 2026)

Where each one goes, what it replaces, and the exact spec. Send them in any format; I'll convert and resize.

## Must have

| # | What | Where it goes | Spec |
|---|---|---|---|
| 1 | ~~Tushar's portrait~~ **Done 12 Oct**: studio portrait received, live in the founder section (`public/images/founder/tushar-joshi-founder.webp`) | "Meet Tushar Joshi" on every variant | — |
| 2 | **A real sample audit** (1–3 pages or screenshots; brand name blurred) | "What your free audit shows you" on `/audit` (today a drawing with grey lines) | PNG/PDF, as it really looks when DTJ sends it |
| 3 | **Category of each brand** (text) | Labels on results and case studies ("Fashion", "Food", "Beauty", "Baby care"…), later a filter | Pro Effex, The Royal Dosa Paper, Zebein, Sindhoi Patola Arts, Little Rituals, Saatvi |

## Nice to have (each makes a section stronger)

| # | What | Where it goes | Spec |
|---|---|---|---|
| 4 | Tushar portrait **cut out** (prompt B) | A founder-in-hero version like WebVeda, if we test it | PNG with transparent background, same pose as #1 |
| 5 | Tushar **at work** (prompt C) | Desktop founder section / about strip | Landscape 16:9, at least 2400 × 1350 px |
| 6 | **30–45 s founder video** ("Hi, I'm Tushar…"), vertical | Founder section or hero (Yuvraj Juneja, Siddharth Rajsekar do this) | 9:16, 1080 × 1920, captions burned in; I can write the script |
| 7 | **Team / office photos** (real) | Founder section ("the team behind your growth"), like GetNos's office story | 2–4 photos, landscape, at least 2000 px wide |
| 8 | **Client video testimonials** (with permission) | Reviews section, as Rahul Malodia's "Then / Now" video cards | 30–60 s, vertical or square, one line of who + brand |

## Facts I need to write the next sections (no images)

- Who the audit is for: minimum monthly revenue and/or ad spend ("For brands doing ₹__ +/month").
- Years in business / since when DTJ has run ads for brands; city to show (Rajkot?).
- Any real press or awards (only if real).
- Whether Tushar wants the offer framed as "your first 3 fixes" (GetNos-style count) — it promises a number.
- The comparison periods for the "before" numbers, before we label them "Then / Now" (audit item F4).

## AI edit prompts for Tushar's photo

Use with any AI image editor (Gemini "Nano Banana", ChatGPT image editing, Photoshop Generative Fill). Upload
`D:\Extra Data\DTJ\dtj\tushar joshi.png` (or a better original). If the face changes even slightly, reject it and run again:
he must be instantly recognisable. Don't add trophies, awards, logos or text: anything fake on the photo is a fake claim.

### A. Main portrait (for the "Meet Tushar Joshi" section)

```
Edit this photo into a premium studio portrait for a business website. Keep the man's face, facial features,
skin tone, hairstyle and build exactly the same — he must be instantly recognisable. Change only:
1) Expression: mouth closed, calm and confident, a slight warm smile, eyes looking straight into the camera.
2) Pose: upper body facing the camera, arms loosely folded at chest level, shoulders relaxed and straight.
3) Clothes: the same black band-collar (mandarin collar) shirt, clean and neatly pressed, no logos.
4) Background: remove the shelves, plants, statues, desk, keyboard and laptop. Replace with a smooth, plain,
   very dark warm charcoal-brown backdrop (#15110E) with a soft, low orange glow (#FF5500) behind one shoulder.
5) Light: soft key light from the front-left, a gentle warm rim light along the right edge of the hair and
   shoulder to separate him from the background, natural soft shadows.
Photorealistic, natural skin texture (no plastic or beauty-filter look), sharp eyes, 85 mm portrait lens look,
shallow depth of field. Frame from the waist up with a little space above the head. Vertical 4:5,
at least 2000 x 2500 px. No text, no logos, no watermark, no props, no other people.
```

### B. Cut-out version (same pose, for overlays)

```
Same edit as before — same man, same face, same black band-collar shirt, same pose and light — but on a plain,
flat, light warm-grey background (#E9E5DE) with no shadow on the background, so the person can be cut out
cleanly. Vertical 4:5, at least 2000 x 2500 px. No text, no logos.
```
(Then remove the background in the same tool, or send it to me and I'll cut it out.)

### C. At work (landscape, optional)

```
Keep this man's face, features and black band-collar shirt exactly the same. Place him seated at a clean, modern
desk in a bright, minimal office with warm wood and soft daylight from a window. A laptop is open in front of
him; its screen is blurred and unreadable. He looks into the camera with a slight, confident smile, hands
resting together on the desk. Photorealistic, natural skin, 35 mm lens look, shallow depth of field.
Landscape 16:9, at least 2400 x 1350 px. No readable text, no logos, no trophies, no other people.
```
