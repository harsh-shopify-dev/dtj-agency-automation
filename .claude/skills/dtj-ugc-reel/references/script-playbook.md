# Script playbook (read before writing ANY reel script)

Source: DTJ's research of 23 Oct 2026, full report with every source: `docs/ugc-reels/research/2026-10-23-short-form-ad-script-playbook.md`
(notes in `docs/ugc-reels/research/2026-10-23-notes/`). Blue Tea numbers are DTJ's own measurements (`docs/ugc-reels/libraries/blue-tea/`).

How to use it:
1. Pick a beat template below (or a kept format from the brand's library) and fill it ONLY from the client's claims file.
2. Write each line to be said aloud by that character in that language; read it aloud in your head.
3. Run `python -m reel_factory.slop script.json --style <library>/style.json` (it automates the checks it can: AI tells, claim
   words, body/disease outcomes, "you" + body condition, AI-customer testimonials, fake urgency, "No. 1", hook length).
4. Walk the 22-point pre-flight below for what a computer cannot judge, then send the script for the person's Approve.

**AI people (ASCI synthetically generated content guidelines, in force about 29 Dec 2026; CCPA 2022 endorsement rules apply now):**
an AI character is a presenter, demonstrator or cartoon, NEVER a customer telling results ("I used it for years, now only this");
every reel with an AI person or AI scene carries the on-screen label "Video created using AI". Set `"ai_label": true` in script.json.

## The DTJ playbook: rules, beat templates, wording and pre-flight

### Twelve rules every DTJ script follows

| # | Rule | Why (source) |
|---|---|---|
| 1 | Speech starts on frame one; the hook is one sentence of 9-11 words inside 3 s, with the product or drink visible in frame | Blue Tea first word 0.0 s, 9.5 words in 3 s ([DTJ style.json](file:///D:/CODE%20CONTAINERR/WEB%20DEV/dtj-reel-engine/docs/ugc-reels/libraries/blue-tea/style.json)); TikTok proposition by 3 s ([TikTok](https://ads.tiktok.com/help/article/creative-best-practices)) |
| 2 | Write the hook as three layers (line + visual + text) and check one of Motion's four triggers fires | [Motion](https://motionapp.com/library/frameworks/hook-analysis) |
| 3 | Budget about 2.8 words/s: 40 words for 15 s, 80-85 for 30 s, 95-100 for 36 s | Blue Tea median 2.77 w/s ([DTJ style.json](file:///D:/CODE%20CONTAINERR/WEB%20DEV/dtj-reel-engine/docs/ugc-reels/libraries/blue-tea/style.json)) |
| 4 | Hindi or Gujarati grammar with the English words people use; captions in 1-4-word chunks, Roman script or English by default | Blue Tea house style ([DTJ Senso playbook](file:///D:/CODE%20CONTAINERR/WEB%20DEV/dtj-reel-engine/docs/ugc-reels/brands/senso/blue-tea-playbook.md)) |
| 5 | Something new on screen every 1-2 s; a new reason to watch every 5-15 s | Blue Tea presenter reels; [UGC Social](https://ugcsocial.substack.com/p/hook-stacking-the-secret-to-longer) |
| 6 | Name an enemy that is a habit or category (the 10-minute boil, bitter tea), never a named rival or a body | Blue Tea #1, #3, #8, #23; [Motion mechanics](https://motionapp.com/library/creative/mechanics/) |
| 7 | One ingredient = one job = one title, and only jobs the client's claims file clears | Blue Tea #2/#5, #6; DTJ rule 5 |
| 8 | Each proof answers one named objection; show it (demo, tear-open, warehouse) rather than claim it | [SideShift](https://sideshift.app/blog/ugc-script-template); [Runneth](https://runneth.com/blog/how-to-create-effective-ugc-ads) |
| 9 | CTA twice: a soft mention after the first proof, a hard specific ask at the end; offers in the caption unless real and dated | [Billo](https://billo.app/creative-insider/inspiration-ideas/cta-examples/); Blue Tea #21 |
| 10 | AI characters are presenters, demonstrators or cartoons, never customers reporting results; label "Video created using AI" | [ASCI SGC guidelines](https://foxmandal.in/wp-content/uploads/2026/09/Guidelines-for-Responsible-Labelling-of-Synthetically-Generated-Content-in-Advertising.pdf) |
| 11 | No "you" + a health or body condition; no body before/after; no disease, weight, period or immunity outcome | [Meta](https://transparency.meta.com/policies/ad-standards/objectionable-content/privacy-violations-personal-attributes); [DMR Act](https://www.indiacode.nic.in/indiacode/bitstream/123456789/1412/1/A1954-21.pdf) |
| 12 | Each batch ships 3-5 genuinely different concepts; hooks are iterated only on a body with signal, and the opening visual changes too | [Meta Dec 2025](https://www.facebook.com/business/news/demystifying-creative-diversification?locale=en_US); [TikTok](https://ads.tiktok.com/help/article/creative-best-practices) |

### Beat templates (timed for about 2.8 words a second)

Lines in quotes show the *register*, not approved claims. Anything in [brackets] is filled only from the client's claims file.

| Template (Blue Tea model) | Best for | Beats and timing | Words |
|---|---|---|---|
| **Situation-first problem** (#10, made compliant) | Cold, problem-aware | 0-3 s a situational scene line, third person or first person, no diagnosis ("Shaadi ka khaana, teen plate, aur phir..."); 3-8 s two or three *situations* as tilted cards (late dinner, rush, office chai); 8-12 s "Toh kya karein?" plus the hero brew shot; 12-25 s one ingredient = one [cleared job] each with a slam title; 25-32 s one shown proof; 32-36 s habit CTA | 95-100 |
| **3D ingredient characters** (#2/#5, 152 d) | Cold, scroll-stop, any language | 0-3 s character self-intro plus a non-medical call-out ("Main haldi hoon..."); 3-20 s one character per 5-7 s, each with one [cleared job] and a sight gag; 20-30 s all together, pack rises; 30-34 s packshot plus BUY NOW click | 75-90 |
| **Villain begs** (#3, 152 d) | Cold, category with an old habit | 0-3 s the old habit as a villain begs "please Senso mat lo..."; 3-8 s it lists the viewer's failed tries; 8-15 s it admits why it is losing (time, taste, mess); 15-20 s whoosh to the hero cup; 20-30 s product plus [cleared] ingredients; 30-36 s "choice simple hai" plus CTA | 90-100 |
| **Fake bad news** (#8, 121 d) | Warm and cold; 1 April or evergreen | 0-4 s serious "announcement" with a red slam title; 4-8 s "Ban gaye na fool?"; 8-15 s the truth, the bad words struck through; 15-20 s jab at the category, not a named brand; 20-26 s two USPs as titles; 26-30 s a pun CTA | 75-85 |
| **Founder or expert Q&A** (#17, #19; real person only) | Warm, trust, deadline moments | 0-3 s name called, "ek sawaal", a *real* named customer question (with consent); 3-8 s question with a deadline (wedding, travel); 8-25 s "do reasons", counted on fingers, red/green slams; 25-30 s CTA tied to the deadline | 80-85 |
| **Tear-open breakdown** (#6, 121 d) | Warm, "what's inside?" objection | 0-3 s "Andar kya hai? Dekhiye." with the sachet tearing; 3-12 s contents into a glass bowl; 12-45 s each ingredient raw in hand, title plus one [cleared] line; 45-52 s how it differs from the category; 52-57 s sip plus CTA | 140-155 |
| **Experience timeline** (#9/#20, no body results) | Cold, habit swap | 0-4 s "7 din, [old habit] ki jagah [product]"; one location and one *experience* per day (taste, time saved, someone asks what it is); final 5 s "switch" CTA | 95-100 |
| **Creator wow moment** (#14, 89 d) | Cold; partnership ads | 0-3 s shocked face, "you won't believe"; 3-6 s the visual trick (colour change, hot to iced); 6-15 s how it happened; 15-25 s why, from [cleared] facts only; 25-35 s "comment 'link'" CTA; Ad label for one third of the length; an AI creator needs the AI label and must not claim results | 90-100 |
| **Old way vs new way race** (Senso hero shot) | Cold and warm | 0-3 s split screen, a 10:00 timer against a 1:00 timer; 3-20 s two or three criteria, each with visual proof; 20-28 s verdict; 28-32 s CTA | 80-90 |
| **5-second bumper** (#22-#24) | Retargeting, reminders | 0-2 s problem word as a slam ("Bitter office chai?"); 2-4 s one promise; 4-5 s pack plus SHOP NOW | 8-12 |
| **Three reasons** ([SideShift](https://sideshift.app/blog/ugc-script-template)) | Warm, feature-rich products | 0-3 s numbered promise; one reason per 6-8 s, strongest last; product answers at least two; CTA | 75-90 |
| **Real testimonial or podcast sceptic** (#11, #13; never AI) | Warm, trust | 0-3 s the verdict or the doubt ("I thought it was a scam"); timeframe of use; one unexpected benefit; one honest drawback; verdict plus CTA; only real, consenting people with proof on file | 85-120 |

### Wording: do and don't

| Don't write | Write instead (only if true and on file) | Rule behind it |
|---|---|---|
| "Charbi jad se khatam", "burns belly fat", "weight kam karega" | "Heavy khaane ke baad ek halka cup" | DMR Act (obesity); Meta weight-loss rules |
| "Kya aapka pet phool jaata hai?", "Are you overweight?" | "Late dinner ke baad kuch halka chahiye?" / "Shaadi ka khaana, teen plate..." | Meta personal attributes |
| "100% natural", "100% pure" | "Sirf [haldi, kesar, kali mirch], aur kuch nahi" | FSSAI May 2025 advisory |
| "Natural" on a flavoured blend | "Made from [named] ingredients" (only if each one qualifies) | FSSAI "natural" conditions |
| "Freshly ground masala" (packed) | "Chhote batch mein pisa" with the real process | FSSAI "fresh" |
| "Traditional recipe" (new blend) | "Ghar jaisa recipe" | FSSAI "traditional" needs 30+ years |
| "Immunity badhata hai", "detox karta hai" | Taste, ritual, origin, process, convenience | ASCI decisions; FSSAI health-claim rules |
| "Periods ko banao easy", "hormonal balance" | No period or hormone claims | DMR Act Section 3; ASCI health rules |
| "No. 1 in India" | A specific, independently sourced fact, dated | ASCI "No. 1" decisions |
| AI person: "Maine 5 kg kam kiya" | AI presenter showing how to make it, labelled "Video created using AI" | ASCI SGC (banned even with a label) |
| "Only 3 packs left, offer ends tonight" (untrue) | The real stock or real deadline, or no urgency | CCPA dark patterns 2023 |
| "Free gift!" with a hidden condition | "[Condition] par free [gift]", spoken and on screen | CCPA 2022 "free" rules |
| "As seen on Shark Tank" with show clips | No show footage or logos in paid ads | [YourStory](https://ts.yourstory.com/2024/05/beyond-shark-tank-india-mintree-allter-quirksmith-turms-d2c-brands) |
| "Elevate your mornings", "game-changer", "unlock", "seamless", "not just a chai, it's an experience" | "Subah ki chai, 1 minute mein" | AI tells ([Wikipedia](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing)); [Sanchez](https://motionapp.com/library/expert/savannah-sanchez/) |
| "Shuddh", "adbhut", "jaadui", "aapki zindagi badal dega" | Words a person says to a friend: "ekdum", "bas", "sach bolu toh" | DTJ inference: spoken register |
| "Delve", "testament", "vibrant", "crucial", stacked triplets of adjectives | One concrete detail: a time, a number, a place | [Wikipedia](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing) |
| "#ad" buried in the caption only | On-screen "Ad" / "Collaboration" for 3 s (15 s or less) or one third of the length | [ASCI influencer rules](https://www.ascionline.in/social/wp-content/uploads/2025/04/ASCI-Influencer-Guidelines.pdf) |

### Pre-flight checklist (every script must pass all 22)

| # | Check | Passes when |
|---|---|---|
| 1 | First frame | Speech or a strong visual on frame one; no logo card, black frame or fade |
| 2 | Hook length | 9-11 spoken words inside 3 s |
| 3 | Hook layers | Line, visual and text written as one unit and aligned |
| 4 | Hook trigger | At least one of: open loop, about the viewer, pattern interrupt, clear promise |
| 5 | Relevance | The viewer knows who it is for, or what it is, by second 3 |
| 6 | Word budget | Total words within about 2.8 x length in seconds (plus or minus 15%) |
| 7 | Spoken register | Read aloud; no line you would not say to a friend; no banned AI or Sanskritised words |
| 8 | Questions and "you" | About one real question per 30 s; "you" used, never with a health or body condition |
| 9 | Screen change | Something new on screen every 1-2 s; a new reason to watch every 5-15 s |
| 10 | Bridge | The line after the hook pays part of the hook and opens a second loop |
| 11 | Captions | Burned in, 1-4-word chunks, inside the safe zone, language and script chosen for the audience |
| 12 | Proof | Every proof is shown, answers one named objection and comes from the client's file |
| 13 | Numbers | Every number traces to one dated source; the same figure in every variant |
| 14 | CTA | One soft mention mid-video, one specific ask at the end, spoken and on screen |
| 15 | Offers and urgency | Any offer, "free" or deadline is real and stated with its condition |
| 16 | Claim words | No "100%"; "natural", "pure", "fresh", "traditional", "original" only where the FSSAI meaning fits |
| 17 | Disease and body | No cure, treat, prevent, weight, fat, sugar control, period, immunity or detox outcome |
| 18 | Before/after | No body before/after; no AI image that exaggerates a result |
| 19 | AI people | AI characters present, demonstrate or act a cartoon role; none poses as a customer or founder |
| 20 | Labels | "Video created using AI" on AI people or scenes; "Ad/Collaboration" on creator posts for the ASCI time window |
| 21 | Targeting | Supplement-like or wellness products set to 18+; no audience or conversion named after a condition |
| 22 | Batch diversity | This script differs from its siblings in persona, format or storyline, not just the first line |

DTJ's existing script checker covers several of these automatically: `python -m reel_factory.slop script.json --style <library>/style.json` ([DTJ Senso playbook](file:///D:/CODE%20CONTAINERR/WEB%20DEV/dtj-reel-engine/docs/ugc-reels/brands/senso/blue-tea-playbook.md)). Checks 12-21 need a person reading against the client's claims file.
