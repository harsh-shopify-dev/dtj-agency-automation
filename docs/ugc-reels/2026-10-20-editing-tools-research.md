# UGC reel editing tools: what pros use, what we can automate, what to add first (research, 20–21 Oct 2026)

Scope: tools and techniques for AI-generated UGC video ads (Meta Reels, 9:16, Hindi / Hinglish / English) that we can run
on a VPS later. Companion to `2026-10-20-reference-ads-analysis.md` (our 11 winning reference ads) and
`2026-10-20-build-plan.md` (the factory plan).

**How to read this.** Every price and fact has a link. "Not verified" means we could not confirm it from a first-party page.
Prices change often; anything from a third-party pricing blog is marked as such. Nothing here was tested on our own footage yet.

**Important limit on the review check.** Reddit and X/Twitter could not be read by our research tools in this session
(Reddit is blocked for our web reader and the built-in browser; X returned "payment required"). So the "real user opinion"
check uses Trustpilot (counts, star spread, invited vs unprompted labels), Hacker News, vendor community forums, the press, and
each tool's affiliate programme. **No Reddit or X opinion in this report is verified.** If we want that layer, a person
should read the threads by hand (search terms are listed at the end).

---

## 1. Executive summary (plain English)

1. Top ad editors do not win because of a magic app. They win on the hook in the first seconds, a real-sounding voice,
   clean audio, and restraint. Our own winning reference ads have only 1–9 cuts in 32–50 s and start talking at 0 s.
2. Our current stack (FFmpeg + Python, Whisper, Demucs, LaMa, Remotion, HyperFrames) already covers most of what pro
   editors do. The gaps are audio finishing, licensed music and sound effects, Hinglish caption timing, and quality checks.
3. **Urgent:** Google says Veo 3.1 shuts down on **22 Oct 2026**; do not build on it. Gemini Omni Flash only claims full
   support for **English** speech, so Hindi/Hinglish dialogue from Flow is a real risk to test now.
4. **Compliance flag:** Google Flow puts a visible watermark on videos for users in **India** unless on the AI Ultra 20x
   plan. Erasing it with LaMa is a terms and labelling risk (India's 2026 IT Rules, ASCI's draft AI-ad rules, Meta's
   "AI info" labels). The hidden SynthID mark stays anyway.
5. Remotion is free only for teams of up to 3 people. If DTJ has 4+ people, automated renders need a company licence
   (from $100/month). HyperFrames is Apache-2.0 with no fees, so it can take over the caption work.
6. Best paid add-ons that have a real API: ElevenLabs Scribe v2 (Hinglish transcription, $0.22/hour), sync.so
   lipsync-2-pro (Hindi lip sync onto clips, about $0.07–0.08/second), Epidemic Sound Business (music and sound effects
   cleared for online ads, with a partner API).
7. Submagic has a good caption API ($0.10–0.23/min) but its templates are the look everyone already uses. Use it as a
   benchmark, not the core.
8. Skip for the pipeline: CapCut (no official API, broad content licence, library music not cleared for ads), Premiere
   and DaVinci (need the app running), Opus Clip and Vizard (they cut long videos, which we do not have).
9. Treat review hype with care: Higgsfield pays creators per video posted about it, and the AI-UGC tool space is full of
   competitors writing each other's "pricing" pages. Arcads has a 2.5/5 Trustpilot score.
10. Add first: (a) loudness and mix finishing, (b) licensed music + SFX, (c) script-timed Hinglish captions in our own brand
    styles, (d) automatic quality gates, then (e) the Hindi voice + lip-sync fallback.

---

## 2. Ranked shortlist

Ranked for **DTJ's automated pipeline** (scriptable, Hindi/Hinglish, Meta Reels ads), not for a human editor at a desk.

| # | Tool | Best for | Automatable? | Cost model | Review signal | Verdict for DTJ |
|---|---|---|---|---|---|---|
| 1 | FFmpeg + our Python (have) | Cuts, loudness, ducking, LUT/grain, encode | Yes, CLI | Free | Organic (industry standard) | Core. Extend it, don't replace it |
| 2 | HyperFrames (have) | Captions, titles, motion graphics from HTML | Yes, CLI, Apache-2.0 | Free, no render fees | Early, organic dev chatter (HN); little ad-editor track record | Core. Move caption rendering here if Remotion licence is an issue |
| 3 | Remotion (have) | TikTok-style word captions, React motion | Yes, CLI/Lambda | Free ≤3 people; else $0.01/render, $100/mo minimum | Organic (devs since 2021) | Keep if licence is fine; else migrate captions to HyperFrames |
| 4 | ElevenLabs Scribe v2 | Hinglish/Hindi speech-to-text with word times | Yes, API | $0.22/hour of audio | Benchmarks mostly vendor-run | Add. Use as checker next to script-timed captions |
| 5 | Epidemic Sound (Business) | Music + SFX cleared for online ads, client work | Partner API (agreement needed) | Subscription; price not on plan page; Business Plus from $100/mo | Not verified (heavy creator sponsorship likely, not checked) | Add for music/SFX licensing |
| 6 | Meta Sound Collection | Free music/SFX for Meta-only ads | No API (download) | Free | Not verified | Use per track only when marked ad-eligible in Ads Manager |
| 7 | sync.so lipsync-2-pro | Put a Hindi voice-over onto a generated face | Yes, API | ~$0.067–0.083 per second | Not verified | Add as the Hindi fallback if Omni's Hindi speech fails |
| 8 | Submagic | One-call captions, zooms, b-roll, silence cut | Yes, API | $19–69/mo plans; API minutes $0.10–0.23/min | Mixed: 4.5 Trustpilot but 30% recurring affiliate, SEO-farm blog | Optional benchmark; templates look generic |
| 9 | Runway Aleph 2 (API) | Remove/replace objects in a video by text | Yes, API | $0.28/second (28 credits/s) | Not checked | Use for hard clean-ups only |
| 10 | ProPainter / DiffuEraser / MiniMax-Remover | Open-source video object removal | Yes, Python (GPU) | Free (GPU cost) | Research-grade, organic | Upgrade from frame-by-frame LaMa for moving objects |
| 11 | Topaz (Starlight) | Upscale soft 720p AI clips | API (first-party, metering unclear) or via fal.ai | API $50/mo for 500 credits; fal $1.20 per 10 s ≤1080p | Mostly organic, mixed (3.6 Trustpilot, subscription anger) | Test only if our clips look soft |
| 12 | FlashVSR / SeedVR2 | Open-source upscaling | Yes (GPU-heavy) | Free (SeedVR2 Apache-2.0) | Vendor tests + forum users | Cheaper upscaling option on a GPU VPS |
| 13 | HeyGen Avatar IV API | Talking avatar from a photo | Yes, API | $3/min (photo avatar) | Mixed: 4.2 Trustpilot, many invited; 25–35% affiliate | Only if we need full avatar ads |
| 14 | Creatify API | URL-to-ad, avatars, ad clone | Yes, API | $99/mo 500 credits; $299/mo 2,000 | Paid/mixed: polarised 3.7, 25% affiliate, SEO farm | Not needed now |
| 15 | Captions / Mirage API | Captions, Mirage avatars | Yes, API | Captions $0.15/min; Mirage Avatar X $0.15/s | Mixed: 4.5 Trustpilot, 25% affiliate | Not needed now |
| 16 | Kling 3.0 / Kling lip sync | Video with native audio, lip sync | API (official + resellers) | ~$0.08–0.14/s official (conflicting) | Not checked | Second generator to compare with Omni |
| 17 | Shotstack / Creatomate | Cloud render from JSON templates | Yes, API | Shotstack $0.05–0.20/min | Not checked | Not needed; we render locally |
| 18 | Arcads | AI actors reading scripts | Pro plan only, MCP server | No public pricing; Pro reported $385–550/mo | Mostly negative organic (2.5 Trustpilot), promotional newsletters | Skip |
| 19 | Higgsfield | Wrapper over many models | API wallet | Pay-as-you-go from $5 | Paid/astroturf signals (pays per post; X suspension) | Skip |
| 20 | CapCut | Fast manual edits, templates | No official API | Free / Pro | Organic, huge user base; ToS backlash | Skip in pipeline; manual only, no library music in ads |
| 21 | DaVinci Resolve Studio | Colour grading | Python API, Studio only, app must run | $295 one-time (third-party sources) | Organic | Only to build a LUT once; apply it with FFmpeg |
| 22 | Premiere Pro | Manual editing | UXP scripting, app must run | Subscription | Organic | Skip |
| 23 | Descript | Edit by transcript | API (early access/beta) | Uses plan minutes/credits | Not checked | Skip (English-first, not verified for Hindi) |
| 24 | Opus Clip / Vizard | Cut long videos into shorts | Yes, API | Plan-based | Mixed (Opus 4.0 Trustpilot) | Skip: wrong job for us |

---

## 3. Per-tool notes

### (a) Captions and kinetic text

**Remotion (have).** `createTikTokStyleCaptions()` groups words into "pages"; you build the highlight yourself
([docs](https://remotion.dev/docs/captions/create-tiktok-style-captions), [displaying](https://www.remotion.dev/docs/captions/displaying)).
Licence: free for individuals and companies up to 3 people; 4+ people need a company licence: "Automators" $0.01 per
render with a $100/month minimum, or "Creators" $25 per seat per month ([remotion.pro/license](https://www.remotion.pro/license)).
Review signal: organic developer community on Hacker News since 2021 ([HN search](https://hn.algolia.com/api/v1/search?query=Remotion&tags=story)); this is developer praise, not ad-editor praise.

**HyperFrames (have).** HeyGen's open-source HTML-to-MP4 renderer: Apache-2.0, "no per-render fees or commercial-use
thresholds", needs Node 22+ and FFmpeg, renders in headless Chrome ([GitHub](https://github.com/heygen-com/hyperframes)).
Launched April 2026; HN chatter is small and from developers ([HN](https://hn.algolia.com/api/v1/search?query=hyperframes)). The repo shows
~68k stars, which is very high for its age; whether that is organic is not verified.

**Submagic.** API: create a project from a video URL with a caption template, `magicZooms`, `magicBrolls`,
`removeSilencePace` (natural/fast/extra-fast), `removeBadTakes`, `cleanAudio`, AI hook title, music track and webhook
([create-project docs](https://docs.submagic.co/api-reference/create-project), [templates](https://docs.submagic.co/api-reference/templates)).
Template names in the docs include "Hormozi 1–5" and "Beast", i.e. the styles everyone already uses. Plans $19 / $39 / $69 per
member per month; the pricing page is inconsistent on API minutes (100 min vs 10 min on lower plans); extra API minutes $57 for
250 ($0.23/min) down to $0.10/min at 5,000+ ([pricing](https://www.submagic.co/pricing)). Hindi captions exist in the app
([Hindi page](https://submagic.co/auto-subtitle-generator/hindi)); Hindi via API should be checked with the Get Languages endpoint (not verified).
Review signal **mixed**: Trustpilot 4.5 from 853 reviews, but many short 5-star reviews clustered in weeks, repeated staff
names, templated replies, and billing complaints in the 1-star reviews ([Trustpilot](https://www.trustpilot.com/review/submagic.co));
30% recurring affiliate commission ([Submagic blog](https://www.submagic.co/blog/best-recurring-commission-affiliate-programs)); Submagic's blog
publishes "Shotstack pricing" style pages in 8+ languages ([example](https://www.submagic.co/blog/shotstack-pricing)), a content-farm pattern.

**Captions (company now called Mirage).** Company renamed Mirage in Sept 2025; the app is still Captions
([TechCrunch](https://techcrunch.com/2025/09/04/captions-rebrands-as-mirage-expands-beyond-creator-tools-to-ai-video-research)).
API: captions $0.15 per input minute; Mirage Avatar X video $0.15 per second ([API pricing](https://captions.ai/help/docs/api/pricing)).
Review signal **mixed**: Trustpilot 4.5 from 518, mostly "unprompted", complaints about surprise charges
([Trustpilot](https://www.trustpilot.com/review/captions.ai)); 25% recurring affiliate ([help](https://help.captions.ai/docs/account/affiliate)).

**CapCut.** No official editing/render API; projects named "CapCutAPI" on GitHub only write draft files you still open in the
app ([community repo example](https://github.com/Losering/CapCutAPI), [vendor summary](https://www.wireflow.ai/blog/capcut-api)).
The June 2025 terms added a broad "worldwide, perpetual, irrevocable, royalty-free" licence over user content, which caused
a backlash ([Larry Jordan](https://larryjordan.com/articles/caution-capcut-changed-their-license-and-may-own-your-content/)).
CapCut's own ad guide says to check each template, effect, font and music track against the asset licence, and library music
is not automatically cleared for ads ([CapCut guide](https://www.capcut.com/resource/capcut-product-image-to-video-ads-guide)).
Signal: organic and huge; the ToS concern is organic too.

**Open-source caption engines worth knowing.** PyCaps renders CSS-styled animated subtitles from Whisper word times
([author's tutorial](https://dev.to/francozanardi/adding-animated-subtitles-to-videos-with-python-4hml)). We already have
better (HyperFrames/Remotion), so this is a reference only.

**Hinglish timing.** In Trelis's code-switched benchmarks, ElevenLabs Scribe v2 scored 7.57 WER on read Hindi-English
speech and 12.40 on conversational, Sarvam 11.25 on conversational, while plain whisper-large-v3 was far worse (29.74) in
one listing ([Trelis](https://trelis.substack.com/p/whisper-hinglish), [Friendli listing](https://friendli.ai/models/Trelis/whisper-hinglish-preview)).
These are vendor-run numbers. Scribe v2 costs $0.22/hour ([ElevenLabs API pricing](https://elevenlabs.io/pricing/api)).
Our own reference analysis found Whisper missed 15 s of speech in one ad, and already recommends taking caption text from the
script ([reference analysis](2026-10-20-reference-ads-analysis.md)).

### (b) Pacing, b-roll, zooms, transitions, sound design

What practitioners recommend (mostly agency and vendor blogs, so directional): cut silences longer than about 0.3 s, prefer
jump cuts to dissolves, keep natural breaths, give the strongest lines extra caption weight
([Billo](https://billo.app/blog/ugc-video-editing/), [Editing Machine](https://editingmachine.com/blog/ugc-video-editing-for-ads-scaling-authenticity), [Biddy](https://www.biddyco.com/blog-posts/ultimate-guide-ugc-ads));
a visual reset (cut, zoom, angle, new caption) every 3–5 s; no source supports a strict "every 2 s" rule
([ezUGC](https://www.ezugc.ai/blog/the-ugc-ad-playbook-formats-hooks-edits-scale)). SFX: a whoosh must match the length of the move it
covers; dialogue must stay the clearest sound; overuse sounds "cheesy" ([forum thread](https://www.jeffbullas.com/thread/what-are-some-best-practices-for-using-sound-effects-in-videos/)).
Our winners contradict the "fast cuts" myth: 1–9 visible cuts per 32–50 s ad, speech at 2.8–3.2 words/s, music 15–22 dB
under the voice ([reference analysis](2026-10-20-reference-ads-analysis.md)).

Tools: **Submagic** API does magic zooms, auto b-roll and silence removal (above). For our own pipeline, FFmpeg handles cuts,
zoom-ins (`zoompan`/`crop`+`scale`), and ducking; HyperFrames has a keyframes/punch-in skill. **Descript** API can run its
Underlord edits (filler removal, Studio Sound, captions) but is early access, uses plan minutes, and only lets you download
after publishing ([Descript help](https://help.descript.com/hc/en-us/articles/43370311322509-Descript-API)). **Opus Clip** has
an official API with SDKs, but it is for clipping long videos ([opus.pro/api](https://www.opus.pro/api)); **Vizard** bundles API access in
paid plans for the same job ([Vizard docs](https://docs.vizard.ai/docs/pricing)). Review: Opus Clip Trustpilot 4.0 from 512, billing and
credit-pressure complaints, 25% affiliate reported ([Trustpilot](https://www.trustpilot.com/review/opus.pro)).

**Premiere Pro**: UXP scripting became official in v25.6, but there is no external scripting socket; community bridges still
need Premiere running ([Adobe UXP changelog](https://developer.adobe.com/premiere-pro/uxp/changelog), [prpr](https://pypi.org/project/prpr/)).
**DaVinci Resolve**: the external Python/Lua API and remote rendering are Studio-only; Resolve can start with `-nogui` but must
be running ([Resolve API readme](https://resolvedevdoc.readthedocs.io/en/latest/readme_resolveapi.html), [PostFlow](https://thepostflow.com/post-production/video-editing/resolve-studio-vs-free/)).
Studio is $295 one-time per third-party sources ([Miracamp](https://www.miracamp.com/learn/davinci-resolve/davinci-resolve-pricing)); not verified on Blackmagic's site.

**Cloud render APIs** (only if the VPS can't render): Shotstack $10 pay-as-you-go (20¢/min) to $499/mo (5¢/min), 1080p on
lower plans ([Shotstack pricing](https://shotstack.io/pricing/)); Creatomate API on all plans, credit-based, about 14 credits per
720p minute, dollar prices not shown on the page ([Creatomate pricing](https://creatomate.com/pricing)); Editframe pricing not found.

### (c) AI avatars, UGC generation and lip sync

**Gemini Omni Flash / Google Flow (our generator).** Text/image-to-video, 9:16 supported, soundtrack by default, but "English
is fully supported. Other languages have not been evaluated" ([Omni docs](https://ai.google.dev/gemini-api/docs/omni)).
API price about $0.10 per second of 720p; **Veo 3.1 and Omni Flash Preview are deprecated and shut down 22 Oct 2026**
([Gemini pricing, updated 19 Oct 2026](https://ai.google.dev/gemini-api/docs/pricing)).

**sync.so lipsync-2-pro.** Re-syncs lips on an existing video to new audio; about $0.067–0.083 per second depending on plan,
3 free generations/month ([sync docs](https://sync.so/docs/product/billing), [pricing](https://lp.sync.so/pricing)). This is the cleanest way
to put a natural Hindi voice-over on a Flow clip if Omni's own Hindi speech is weak. Review signal not checked.

**HeyGen.** API wallet from $5, Avatar IV photo avatar $3/min, digital twin $4/min per HeyGen's help centre as summarised
([HeyGen help](https://help.heygen.com/en/articles/10060327-heygen-api-pricing-explained), [G2 summary](https://www.g2.com/articles/heygen-api-pricing)).
Review **mixed**: Trustpilot 4.2 from 4,672, many "Invited" reviews, complaints on credits and glitches
([Trustpilot](https://www.trustpilot.com/review/heygen.com)); affiliate 25–35% recurring plus a 50% bonus for social creators (Aug–Oct)
([affiliate](https://www.heygen.com/affiliate-program), [creator programme](https://www.heygen.com/geniverse/social-creator-program)), so expect lots of affiliate videos.

**Creatify.** API Starter $99/mo for 500 credits, Pro $299 for 2,000; avatar/URL-to-video 5 credits per 30 s; Aurora 2.0
0.4–2.8 credits/s by resolution ([billing docs](https://docs.creatify.ai/billing)). Review **paid/mixed**: Trustpilot 3.7 from 842,
76% 5-star but recent reviews mostly negative about renewals and refunds; one reviewer alleges free credits were offered for
reviews (unverified) ([Trustpilot](https://www.trustpilot.com/review/creatify.ai)); 25% recurring affiliate ([affiliate](https://creatify.ai/affiliate));
Creatify publishes competitor pricing pages (Arcads, HeyGen, Runway, OpusClip) in 8+ languages ([example](https://creatify.ai/blog/arcads-pricing-(2026)-plans-credits-and-what-you-ll-actually-pay)).

**Arcads.** No public pricing page (per a competitor, /pricing returned 404 in July 2026) ([Wireflow](https://www.wireflow.ai/blog/arcads-pricing));
a competitor reports API only on Pro ($385 promo / $550 list) ([Creatify blog](https://creatify.ai/blog/arcads-pricing-(2026)-plans-credits-and-what-you-ll-actually-pay)) — both are
competitor sources. Review **mostly negative organic**: Trustpilot 2.5 from 186 (49% 1-star) citing blurry video, poor lip sync, no support
([Trustpilot](https://www.trustpilot.com/review/arcads.ai)); HN users say it helped "only up to a point" and the shared actor pool blocks a
consistent brand face ([HN](https://hn.algolia.com/api/v1/search?query=Arcads)). Praise found was in promotional newsletters.

**Hedra.** Character-3 3–6 credits/s; plans reportedly $15–75/mo; no official API rate sheet found ([plans](https://www.hedra.com/plans)). Not verified.

**OmniHuman 1.5 (ByteDance).** Portrait + audio → talking video; resellers charge $0.045–0.25/s; language list does not include
Hindi ([RunComfy](https://www.runcomfy.com/models/bytedance/omnihuman), [PiAPI](https://piapi.ai/pt/blogs/omnihuman-1-5-api-guide)). Not verified.

**Kling 3.0 / lip sync.** Native audio and a Lip Sync tool ([Kling blog](https://kling.ai/es/blog/best-lip-sync-video-ai)); official per-second
price conflicts across sources, roughly $0.08–0.14/s ([CloudZero](https://www.cloudzero.com/blog/kling-ai-pricing/)). Not verified.

**Higgsfield.** A wrapper over third-party models with an API wallet ([MindStudio](https://www.mindstudio.ai/blog/higgsfield-api-pricing-pay-per-use/)).
Review **paid/astroturf**: its "Earn" programme pays creators per approved video, up to $2,500 per video ([Higgsfield Earn](https://higgsfield.ai/earn));
its X account was suspended in Feb 2026, reason unconfirmed ([No Film School](https://nofilmschool.com/ai-video)); The Register reports
allegations of undisclosed review astroturfing and throttled "unlimited" plans ([The Register](https://www.theregister.com/2026/02/06/higgsfield_ai_job_loss/));
the co-founder admitted process failures ([Grit Daily](https://gritdaily.com/kazakh-startup-higgsfield-criticism/)). Trustpilot 4.0 from 5,107 with invitations
and 18% 1-star ([Trustpilot](https://www.trustpilot.com/review/higgsfield.ai)).

**Does AI UGC work as well as real creators?** No independent study found. Agency and vendor posts claim AI is close on cold
CTR/CPA but real creators win on conversion for pricier products and retargeting ([Moburst](https://intercept.moburst.com/ai-avatar-ads-vs-real-creators-which-wins-on-meta/),
[inBeat](https://inbeat.agency/blog/ai-ugc-ads-vs-real-ugc)). NIQ's own EEG study (Dec 2024) found AI ads felt more "annoying", "boring" and "confusing"
and produced weaker memory activation even when rated high quality ([NIQ](https://nielseniq.com/global/en/news-center/2024/niq-research-uncovers-hidden-consumer-attitudes-toward-ai-generated-ads/)).

### (d) Object / watermark removal and upscaling

**Video object removal.** LaMa works per frame, so moving objects can flicker. Video-native options: ProPainter (ICCV 2023,
mature), DiffuEraser (diffusion, higher quality), MiniMax-Remover (fast, 6 steps); all need masks, typically from SAM
([MiniMax-Remover paper](https://arxiv.org/abs/2505.24873v1), [ProPainter](https://gittrend.io/repo/sczhou/ProPainter)). Paid: Runway Aleph 2 API
$0.28/s, 56-credit minimum ([Runway API pricing](https://docs.dev.runwayml.com/guides/pricing/)).

**Watermarks — read this before using LaMa on Flow output.** Google's Flow help page: all outputs carry invisible SynthID, and
"a visible watermark is applied automatically for users in India, South Korea, and Vietnam" not on the AI Ultra 20x plan
([Flow help](https://support.google.com/flow/answer/16353333?hl=en)). The page has no explicit rule on removing it; the Terms of
Service apply. India's IT Rules amendment (in force 20 Feb 2026) requires labels and provenance metadata on synthetic content
on platforms ([Hogan Lovells](https://www.hlc.com/en/publications/india-introduces-mandatory-labelling-for-ai-and-3hour-takedown-for-illegal-content));
ASCI's draft AI-ad framework (consultation closed 13 June 2026; final status not verified) wants a "created using AI" label for
synthetic people ([Mondaq](https://www.mondaq.com/india/advertising-marketing-branding/1790884/ai-in-advertising-ascis-new-draft-disclosure-guidelines)).
Meta shows "AI info" labels using C2PA and industry signals ([Meta](https://about.fb.com/news/2026/02/meta-prepares-for-2026-us-midterms/)).
The Omni API page mentions only SynthID, no visible mark ([Omni docs](https://ai.google.dev/gemini-api/docs/omni)). **Recommendation:** get
Harsh's/legal sign-off before any watermark removal; prefer the API route or the Ultra plan over erasing marks.

**Upscaling.** Omni's 1080p and 4K are already upscaled outputs ([Omni docs](https://ai.google.dev/gemini-api/docs/omni)). Topaz has a first-party
API ($50/mo for 500 credits; video metering not stated) ([Topaz API](https://www.topazlabs.com/api)); Starlight via fal.ai costs $1.20 per 10 s up
to 1080p ([fal](https://fal.ai/models/topaz/upscale/video/generative)). Topaz desktop is now subscription-only, local Starlight needs higher tiers
([Topaz docs](https://docs.topazlabs.com/topaz-video/tvai-vs-tv)); Trustpilot 3.6 from 56,634, long-time users angry about the
subscription switch ([Trustpilot](https://www.trustpilot.com/review/topazlabs.com)) — **mostly organic, mixed**. Open source: SeedVR2
(Apache-2.0, natural but slow, ~35 GB peak memory at 1440p, can over-sharpen light 720p AI clips) and FlashVSR (faster, preferred by one vendor test)
([SwiftVR benchmark](https://arxiv.org/pdf/2606.09516), [Sogni test](https://blog.sogni.ai/blogs/minimax-h3-upscaling/), [Topaz forum](https://community.topazlabs.com/t/sls-vs-slm-vs-seedvr2-vs-flashvsr-comparison/98005/1)).
Runway also sells a video upscaler at $0.007/frame at 720p/1k ([Runway](https://docs.dev.runwayml.com/guides/pricing/)).

### (e) Colour grading and the "phone-real" look

Advice found (vendor guides, so treat as starting points): normalise exposure/white balance, apply a film or phone LUT at
50–80% strength, add light grain (~2–3%), a touch of softening to remove the plastic over-sharp AI look, then match all
clips to one reference still ([invideo](https://invideo.io/blog/luts-film-grain-ai-video/)). For "real" UGC the bigger levers are
framing (slight selfie tilt, off-centre) and voice, not grading ([Atlas Cloud guide](https://www.atlascloud.ai/blog/tips/how-to-make-ai-ugc-ads),
[CreaScale](https://creascale.ai/how-to-make-ai-ugc-ads.html)). In our pipeline this is FFmpeg `lut3d` + `noise` + `gblur`/`unsharp`
(parameters not tested yet). DaVinci is only useful to design the LUT once.

### (f) Music and SFX licensed for ads

- **Epidemic Sound Business**: covers "social media campaigns and digital ads"; agencies under $5M revenue may make client work
  for clients under $50M; brands must be under $10M ([Business plan](https://www.epidemicsound.com/our-plans/business-plan/)). Partner
  API needs an agreement; free prototyping tier and an MCP server exist ([developer docs](https://developers.epidemicsound.com/docs/), [help](https://help.epidemicsound.com/hc/en-us/articles/35854988839570-Getting-Started-with-the-API)).
- **Artlist**: the Pro licence covers paid ads and client work; the cheaper Social plan likely does not (third-party, not verified)
  ([Artlist pricing](https://artlist.io/page/pricing) — page blocked our reader; summary via search).
- **Meta Sound Collection**: free, Meta-only; secondary sources say it can be used in ads, but not every track is ad-eligible;
  Instagram's popular music library is not for ads ([Audiodrome](https://audiodrome.net/for-creators/facebook-music-licensing-faqs/), [Third Chair](https://usethirdchair.com/blog/meta-sound-collection-explained-for-brands-and-rights-holders)).
  Meta's own licence text not verified.
- **ElevenLabs Music / SFX**: paid plans carry commercial use; music API ~$0.15/min, SFX ~$0.12/min per a third-party price
  snapshot ([MindStudio](https://www.mindstudio.ai/blog/elevenlabs-music-v2-commercial-content-licensed-ai-music), [Smallest.ai](https://smallest.ai/blog/elevenlabs-pricing-plans-cost-what-you-get-in-2026)). Verify music terms before paid ads.
- **CapCut library music**: not safe for ads by default (see (a)).

---

## 4. Review-signal findings (how much of the praise is real)

| Tool | Signal | What we found |
|---|---|---|
| Remotion, FFmpeg, DaVinci, CapCut | Organic | Long-running communities; CapCut ToS backlash was organic |
| HyperFrames | Early, mostly organic | Small HN threads from developers; very high star count for a 6-month-old repo (not verified) |
| Topaz | Mostly organic, mixed | 56k Trustpilot reviews over years; complaints about subscription switch |
| Submagic | Mixed | 4.5 Trustpilot, clustered short 5-stars, 30% recurring affiliate, multilingual competitor "pricing" pages |
| Captions/Mirage, Opus Clip | Mixed | Mostly unprompted reviews; 25% affiliate programmes; billing complaints |
| HeyGen | Mixed | Many invited reviews; affiliate up to 35% plus 50% creator bonus |
| Creatify | Paid / mixed | Polarised reviews; alleged review incentives (unverified); 25% affiliate; SEO farm of competitor pages |
| Arcads | Mostly negative organic | 2.5 Trustpilot, HN skepticism; positive takes come from promo newsletters |
| Higgsfield | Paid / astroturf | Pays creators per post; X suspension; press reports of astroturfing |

Pattern across the whole category: a search for "best AI UGC tool" or "X pricing 2026" returns mostly pages written by
competing vendors (Creatify, Submagic, Wireflow, Atlas Cloud, Hooked, CostBench). Treat any "ranking" from a tool company as an ad.

---

## 5. Generic "AI slop" vs what top performers do

| Generic output (looks like every other AI ad) | What top performers do (and what our winners show) |
|---|---|
| Logo or slow intro first | Speech starts at 0 s, 7–14 words in the first 3 s, product in hand in frame 0 (our 11 reference ads) |
| One vague hook ("Want better skin?") | A specific hook type: confession, bold claim, relatability, contrast, curiosity (Motion 2026 benchmarks, 550k ads, [Motion](https://motionapp.com/events/2026-creative-strategy-bootcamp/homebase/top-hook-formats)); value lands within ~6 s (TikTok Creative Codes, 2023, via [Superside](https://www.superside.com/blog/tiktok-ad-creative-examples)) |
| Studio light, centred face, plastic skin, over-smooth motion | Phone-native framing (slight tilt, off-centre), real room, light grain; "if it looks like a TV ad, it dies" ([Barry Hott via Practical Ecommerce](https://www.practicalecommerce.com/?p=1539710), [CreaScale](https://creascale.ai/how-to-make-ai-ugc-ads.html)) |
| Non-stop robotic voice-over | Human delivery: pauses, a false start, filler. Our book ads have 3–9 pauses >0.4 s; the "voice-over" beauty ads have 0–1 |
| Cut every 2 s, whoosh on every cut | Cut on meaning; 1–9 visible cuts in our winners; remove dead air but keep "thinking" pauses; SFX only where something moves, sized to the move |
| Stock "Hormozi" template captions | Brand house style: 1–3 words, one keyword in colour, ~55–65% down the frame, inside Meta's safe zone (check with Ads Manager's overlay) |
| Music fighting the voice, peaks above 0 dB | Voice always clearest, music 15–20 dB under, one loudness target (~-14 LUFS, true peak under -1 dB) |
| Product changes shape between clips | Product continuity checked automatically (one product state per clip) |
| Same avatar pool as every competitor | Our own consistent characters per brand (shared pools block a brand face — HN user) |
| AI person presented as a real customer with an invented result | Real claims only; AI disclosure where needed (ASCI draft, Meta "AI info", India IT Rules) |
| Many near-copies of one ad | Many genuinely different angles; Meta's Andromeda update rewards creative diversity ([Motion](https://motionapp.com/releases)) |

The research consensus (mostly vendor-written, so directional): AI ads fail on delivery and script, not pixels
([Linocut](https://linocut.ai/blogs/how-to-make-ai-ugc-ads-not-ai-slop/), [Atlas Cloud](https://www.atlascloud.ai/blog/tips/how-to-make-ai-ugc-ads)).

---

## 6. Recommended stack for the automated pipeline

Note: Harsh's 20 Oct decision is "no APIs" for generation (Flow and ChatGPT in a real browser). Everything in steps 1–4 below
runs locally with no new API. Steps 5–7 are paid APIs to switch on only with Harsh's yes.

**Keep (core):** FFmpeg + Python (cuts, mix, encode), Demucs, Whisper for rough timing, HyperFrames for captions and graphics,
Remotion only if the licence fits our headcount.

**Add first, in this order:**
1. **Audio finishing gate (local, free).** Two-pass loudness to about -14 LUFS, true peak under -1 dB, music 15–20 dB under the
   voice with ducking, optional room tone so AI voices don't sound "studio". Fixes the clipping found in the beauty ads.
2. **Licensed music + SFX.** Epidemic Sound Business (covers online ads and agency client work within its revenue limits) or
   Meta Sound Collection tracks marked ad-eligible. A small, curated SFX set (pops, soft whooshes, paper, cap clicks) used only on
   real on-screen actions. Never CapCut or Instagram library music in ads.
3. **Script-timed Hinglish captions in our own house styles.** Caption text comes from the approved script; timings come from
   forced alignment against the audio (WhisperX-style alignment; Hindi support not verified — test), with ElevenLabs Scribe v2
   ($0.22/hour) as a cross-check. Build 3–4 brand caption presets in HyperFrames from the reference ads (1–3 words, one keyword colour).
4. **Automatic quality gates.** Loudness and peak, safe-zone check, product continuity (frame compare), caption-vs-script diff,
   and an "AI label needed?" flag.
5. **Hindi voice fallback (API, needs yes).** Test Omni's Hindi/Hinglish speech now. If weak: Hindi TTS (provider to choose;
   Sarvam/ElevenLabs not compared here) + sync.so lipsync-2-pro (~$0.07–0.08/s).
6. **Phone-real finishing pass.** FFmpeg LUT at partial strength + light grain + slight softening; A/B test against no grade.
7. **Better video clean-up and upscaling (GPU or API, needs yes).** ProPainter/DiffuEraser with SAM masks for moving objects;
   Runway Aleph only for hard shots; upscale only if clips look soft (FlashVSR/SeedVR2 on a GPU, or Topaz via API).

**Do not add:** CapCut, Premiere, Resolve (beyond making a LUT), Opus Clip, Vizard, Descript, Arcads, Higgsfield.
**Optional benchmark:** run 5 of our clips through Submagic's API once and compare with our own captions, to make sure we beat it.

**Decisions for Harsh:** (1) DTJ headcount vs Remotion licence; (2) watermark policy for Flow output in India; (3) Epidemic
Sound vs Meta Sound Collection; (4) budget to test sync.so for Hindi lip sync.

---

## 7. Not verified / open

- All Reddit and X opinions (tools blocked). Manual search terms: `site:reddit.com Arcads`, `r/FacebookAds AI UGC`,
  `r/editors Submagic`, `r/VideoEditing Topaz Starlight`, `r/aivideo Omni Flash Hindi`, `r/StableDiffusion SeedVR2 FlashVSR`.
- Exact current prices for Arcads, Hedra API, Kling official API, Editframe, Artlist, Epidemic Business monthly price, DaVinci Studio (Blackmagic page).
- Meta Sound Collection licence text; ASCI final AI-ad guideline status; Google ToS wording on removing Flow watermarks.
- Hindi support in: Submagic API, WhisperX alignment, Omni Flash speech, OmniHuman, HeyGen voices.
- Any tool's output quality on **our** footage: nothing in this report was tested hands-on.
