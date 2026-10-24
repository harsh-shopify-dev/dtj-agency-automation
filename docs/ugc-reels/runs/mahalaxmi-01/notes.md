# mahalaxmi-01: Mahalaxmi Masala, Gujarati testimonial reel (22 Oct 2026, DONE)

Concept: Two Brothers Organic Farms reel #4 (Khapli flour, 166 days live): a woman at home talks to her propped phone
holding the pack, with black-and-white "before" cut-ins. Library: `Downloads/dtj-reel-library/spices/` (47 ads).
Job folder: `Downloads/dtj-ugc-mahalaxmi-01/` (script.json approved by Harsh: "script is perfect").

Done:
- Packs: the website packs (Harsh's pick), full size from mahalaxmispices.com/wp-content/uploads/2024/08/*-pik-min.png.
- 8 start pictures made in ChatGPT only (Harsh's rule), one chat: images/s1..s8.png (s1 = character, s3 = hero).
- Pictures reach Flow through DTJ's n8n media folder (`/media/reel-inputs/mx01-<token>/`, see media_url.txt) + images.weserv.nl.
- Flow project https://flow.google.com/project/7609aa8e-4046-426f-9746-6c69e774a826: 16 takes (8 shots x2; s2/s7 6 s, others 8 s),
  all downloaded to clips/. Omni speaks Gujarati well (s1_a: the whole line, 0.0-7.7 s; s1_b lost the opening).
- Music: Pixabay "Free Soul - Gentle Flute and Strings" (music/LICENSE.txt).

Left: `job check` (was running; it skips takes already done, re-run to finish), pick one take per shot by eye at 4 fps,
`job edit` (Gujarati captions need a Gujarati font check), watch, deliver.
Pausing note: the browser pane can sign Flow out on restart; a person signs in again.

## Result (22 Oct 2026, 23:30)
`Downloads/dtj-ugc-mahalaxmi-01/final/reel_final.mp4`: 49.6 s, 1080x1920, -14.0 LUFS, Remotion captions in Gujarati script
(fallback font Nirmala UI / Noto Sans Gujarati), flute music. Picks: s1_a, s2_a (0-3.2 s), s3_a, s4_a, s5_b, s6_b, s7_b (1.5-5.0 s), s8_a (0-7.8 s).
Captions at the top on the pack shots (s3-s6, s8). Watched at 1.25 fps: lines in sync, packs steady and readable.
Fixed on the way: Whisper echoes its prompt on Gujarati/silence (shots with no line now have no speech); a person's trim is
never moved by beat-sync; caption font fallback for Indian scripts; language gu.
Time: ~2 h 10 m of work (log in the session); ~45 min avoidable (Flow sign-out, checking all 16 takes, the edit bug).

## Playbook check (23 Oct 2026) - proposed presenter lines, NOT yet remade
The script checks (slop.py) flag shots 1, 3, 8 as an AI person speaking as a customer (CCPA 2022 endorsements; ASCI AI-content
guidelines from about 29 Dec 2026). Proposed replacements (presenter, not customer), each 8 s:
- s1: "શાકમાં ના રંગ આવે, ના સુગંધ? તો વાંક મસાલાનો છે." (No colour, no aroma in the sabzi? Then the masala is to blame.)
- s3: "આ છે મહાલક્ષ્મી મસાલા, ૧૯૬૦ થી ગુજરાતના રસોડામાં વપરાય છે." (These are Mahalaxmi masalas, used in Gujarati kitchens since 1960.)
- s8: "રંગ અને સુગંધ બંને જોઈએ? તો એક વાર મહાલક્ષ્મી ટ્રાય કરો!" (Want both colour and aroma? Try Mahalaxmi once!)
Also add the on-screen label "Video created using AI". Remaking s1, s3, s8 costs about 72 Flow credits; waiting on Harsh.
