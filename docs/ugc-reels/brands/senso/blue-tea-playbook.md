# Blue Tea playbook for Senso reels (21 Oct 2026)

Harsh (21 Oct 2026): "the blue tea ads are crazy and we can blindly copy them... just go with the blue tea india".
So Senso reels copy Blue Tea India's winning ads: their formats, pacing, captions, graphics and hooks. We never copy their
people, voices, footage, words or health claims; Senso's claims come only from `claims.md` in this folder.

Evidence, all in `Downloads/dtj-reel-library/tea-wellness/`:
- The ads: Blue Tea India's active video ads in Meta Ad Library (India), each running 36-154 days, collected 21 Oct 2026.
  25 files = 21 unique videos (#5 = #2, #20 = #9, #25 = #11; #22-#24 come from one shoot).
- `manifest.json`, `analysis/<id>/` (transcript, words, frame sheets), `style.json` (the numbers below).
- The shot-by-shot breakdown of every reel: `analysis/breakdown_01_13.md` and `analysis/breakdown_14_25.md`.

## 1. The numbers every Senso script must hit (measured, `style.json`, the 20 reels with speech)
| What | Blue Tea (middle value, 20-80 % range) | Rule for Senso |
|---|---|---|
| First spoken word | 0.0 s in every reel | Talking starts on frame one. No logo, no silent build-up. |
| Words in the first 3 s | 9.5 (8-11) | The hook is one full sentence inside 3 s. |
| Speaking speed | 2.8 words/s (1.7-3.5) | Brisk; a 35 s reel has about 90-100 words. |
| Language | 99 % Hindi | Hindi voiceover with English product words (metabolism, cravings, caffeine free), captioned in English or Roman Hindi. English-only is the exception (1 of 21). |
| Questions to the viewer | ~1 per 30 s | One real question ("Kuch khaate hi pet phool jaata hai?"). |
| Fillers | 0 | Scripted voiceover, not rambling creator talk. |
| Cuts | 2.5 per 10 s (1.4-5.8) | Presenter reels cut slowly but change a graphic every 1-2 s; montage and animation reels 6-9 cuts per 10 s. |
| Length | 36 s (29-51) | 30-40 s; plus 5 s bumpers. |
Check a script with: `python -m reel_factory.slop script.json --style <library>/style.json`.

## 2. The look Blue Tea repeats in every format
- **Captions:** 1-4 word chunks on a rounded pill at the lower centre, the spoken word highlighted (word by word). White pill
  with black text is the default. Hindi speech is captioned in English or Roman Hindi, never in Devanagari.
- **Slam titles:** the key idea in huge condensed caps at the top, with a pop or slam motion. Colours carry meaning: red = the
  problem (CAFFEINE, BITTER, 93 KG), green = the good news (76 KG, CONTINUOUSLY, ADAPTOGENS), yellow = proof (17 LAKH+,
  SO THIS ISN'T NORMAL).
- **The hero is the drink, not the pack:** a clear glass cup of the blue drink is in almost every shot; the pouch mostly
  appears at the end. The brew moment (hot water poured in, the colour spreading, top-down) is the signature shot. Senso's
  version: the sachet torn and poured in, hot water, the stir; the golden haldi swirl, the dark kahwa, the chai turning
  milky-brown, in a glass cup.
- **Picture-in-picture cards:** rounded photo or 3D cards slide in over the presenter for each point (a wedding photo, a
  bloated belly, a gut render, a food plate).
- **3D anatomy inserts:** gut, fat cells, x-ray runners (7 of 21 videos). For Senso: the stomach, a warm glow, a calm gut. Never
  melting fat; Senso does not claim weight loss.
- **A clear enemy:** green tea, bitter tea, caffeinated tea, celebrity ads. For Senso the enemy is the 10-minute boil, the dirty
  pan, "no milk at home", the bitter office-vending chai, the bloated feeling after a heavy meal, the late-night caffeine coffee.
- **One ingredient = one job:** each ingredient gets its own title or character (ginger = digestion, butterfly pea =
  metabolism, dandelion = water retention). For Senso: haldi, kesar, kali mirch; adrak, laung, dalchini, tulsi, elaichi, hing.
- **Habit-style CTA:** "din mein teen baar", "never skip", "switch today", "start today", sometimes an animated "BUY NOW" button
  with a cursor click. No prices or offers in the video (Blue Tea's 30 % offer is only in the caption text).

## 3. The formats, ranked by how long Blue Tea has run them, with the Senso version
Claims marked * are Senso's own words (see `claims.md`). Every format below can be made in Flow (AI) unless it says otherwise.

| # | Blue Tea format (their reels, days running) | Senso version | Product | Made with |
|---|---|---|---|---|
| A | **Founder brand story** "How did we get 25 lakh customers? No celebrity, no TV ad" + a 3 s burst of creators shouting the name (#1, 154 d) | "2 million cups of Senso every day, and you've never seen our ad. Why?" Rajkot, 2009, airlines*, the Gulfood award*. Ends: "khud try karke dekho". Opens with a 3 s burst of 6 people each saying "Senso!" with a sachet. | brand / masala chai | Needs a real Senso person on camera (never an AI face posing as the founder) or a voiceover over the factory line; the "never seen our ad" line needs Senso's confirmation |
| B | **3D ingredient characters** in the stomach, each saying its job (#2/#5, 152 d) | "Main haldi hoon..." Haldi, Kesar and Kali Mirch as Pixar-style characters in a warm kitchen or tummy world. Kali Mirch: "mere bina haldi body mein jaati hi nahi" (pepper helps turmeric absorb*). Ends on the Turmeric Latte pack + BUY NOW click. A kahwa version: Adrak, Laung, Tulsi and Hing clean up after a heavy-meal party (bloating*). | Turmeric Latte; Detox Kahwa | Flow, fully AI: Blue Tea's own is clearly AI |
| C | **Villain begs you not to drink it** "Suno, tum bas Blue Tea mat peena please" (#3, 152 d) | The 10-minute boiling pot (or the dirty chai pan) begs: "Please Senso mat lo... phir mujhe koi nahi poochega." | Masala / Ginger chai | Flow, AI character |
| D | **Cartoon short: the craving monster** (#15, 77 d) and **organ courtroom** (#16, 77 d) | Courtroom: the Stomach in the dock, "Late-night biryani, My Lord!" The Brain judge: "Khaane ke baad Senso Kahwa." "Three weeks later" card; the happy Stomach holds the box. Monster: a "SLEEPY" monster at 4 pm in the office meets the cardamom chai sachet. | Kahwa; Cardamom chai | Flow, AI (17-30 s) |
| E | **Fake bad news / April Fool** "Ab Blue Tea mein caffeine hoga aur kadwi bhi" then "Ban gaye na fool?" (#8, 121 d) | "Ab Senso chai banane ke liye 10 minute ubaalna padega..." then "Fool mat bano, 1 minute mein chai piyo." Or for the Turmeric Latte: "Ab haldi doodh mein caffeine..." then "Kabhi nahi*." | any; Turmeric Latte | Presenter (real person or AI creator) + slam titles |
| F | **Ingredient breakdown at a desk** (tears the tea bag open) (#6, 121 d) | Tears a Turmeric Latte sachet into a glass bowl: "haldi, kesar, kali mirch*; aur sirf yahi." Each ingredient raw in hand with a slam title. Kahwa: 7 spices, hing, tulsi*, "zero sugar*". | Turmeric Latte; Kahwa | Presenter + ingredient B-roll (Flow) |
| G | **Problem first** "Kuch khaate hi pet gubbare jaisa phool jaata hai? Ye normal nahi hai" (#10, 107 d) | Same opening, then "Bhaari khaana, late dinner...": the causes as tilted cards. "Khaane ke baad ek cup Senso Detox Kahwa: adrak, hing, tulsi, kali mirch*." No cure claim: "Senso ke hisaab se bloated stomach mein faydemand*". | Detox Kahwa | UGC-style AI clips + titles |
| H | **Timeline** "Drink it 14 days continuously and this is what happens" (#9/#20, 107 d) | A swap with no body promises: "7 din, shaam ki coffee ki jagah Senso Haldi Latte". Day 1: "caffeine free*, 4 baje ki craving gayi"; Day 3: "office mein sab poochne lage"; Day 7: "nani wala haldi doodh, 1 minute mein". Each day is about the experience, never a body result. | Turmeric Latte | Presenter, new location per day |
| I | **Myth-buster with numbers** "Blue Tea kaam nahi karega... 17 lakh customers pe kaam kiya" (#12, 104 d) | "Instant chai mein asli chai nahi hoti?" Assam tea*, real elaichi*, 2 million cups a day*, airlines*. | Masala / Cardamom | Presenter cut-out over AI scenes |
| J | **Creator wow-moment** (lemon turns it purple) + "comment link" (#14, 89 d) | Senso's wow: cold Turmeric Latte, blended with ice (it works hot or cold*); or hot chocolate going hot to iced. "Comment 'link'." | Turmeric Latte cold; Hot Chocolate | Real creator preferred; AI creator possible |
| K | **Fast VO explainer montage** with a 1.5 s burst of 10 people sipping (#18, 71 d) | "Yeh Senso Turmeric Latte, haldi, kesar aur kali mirch se bana*..." with pour, swirl and 3D cards. | Turmeric Latte | Flow montage + VO |
| L | **Founder Q&A in the warehouse** "Shalini from Mumbai asks..." (#17, #19, 71 d) and the wedding-season tip (#21, 62 d) | Senso's factory is its best set (2 million sachets a day*). "Riya from Pune asks: hostel mein kettle hai, gas nahi, chai kaise?" "Travel pe chai?" Seasonal: "Shaadi ka season, ghar mein 50 mehmaan - chai kaun banayega?" | Masala chai; travel sachets | Needs a real Senso person and the real factory |
| M | **Meme glow-up** "Tera kuch nahi hoga / Or ab??" (#7, 121 d) and the before/after text montage (#4, 121 d) | "Tera kuch nahi hoga" (a hostel kid with burnt chai pans), then "Or ab??" with Senso, 1-minute chai. No body before/after. | Masala chai | UGC-style AI + trending audio (needs a licence) |
| N | **5 s bumpers** (one model shoot, 3 messages) (#22-#24, 44 d) | "Bitter office chai?" then "Ghar jaisi elaichi chai, 1 minute*"; "Shaadi season, 50 mehmaan, 1 minute"; "Kahwa, zero sugar*". Pack PNG + SHOP NOW. | any | One AI shoot, 3 cuts |
| X | **Podcast sceptic** (#11/#25) and **customer walk-and-talk 93 to 76 kg** (#13) | Not as AI. A testimonial with an invented customer would be a fake review. Only with a real Senso customer or a real podcast. | - | Real people only |

Run first (strongest proof plus easiest to make in Flow): **B** (3D ingredient characters, Turmeric Latte), **D** (the
courtroom, Kahwa), **C** (the boiling-pot villain, Masala chai), **E** (fake bad news). Each one copies a Blue Tea ad that has run
77-152 days.

## 4. Senso's hero shots (the equivalent of Blue Tea's blue-cup brew)
1. Sachet torn at the top notch, poured into a clear glass cup (the powder visible).
2. Hot water from a steel kettle, then a spoon stir; for the latte, a golden swirl spreading; steam.
3. Top-down: the cup on a wooden table next to the box (front facing camera, steady: one product state per shot).
4. The race: a pan of boiling chai with a "10:00" timer next to Senso with a "0:60" timer.
5. Cold version (latte, hot chocolate): ice, a hand blender, a tall glass.

## 5. Never (on top of the DTJ house rules)
- No weight-loss, fat, "detox your body", cure or immunity promises, even though Blue Tea uses them. Senso's allowed lines are in `claims.md`.
- No invented customers, customer counts, reviews or before/after bodies; no AI face presented as Senso's founder or as a customer.
- No copy of Blue Tea's words, voice, characters' exact designs or footage. Same format, new Senso story.
- No airline names, "Belgian chocolate", "pure coconut" or "100 % natural" until `claims.md` says they are cleared.
