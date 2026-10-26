# Audience intelligence: a living playbook per target audience

Harsh (25 Oct 2026): "if our target audience is genZ for example then we have to analyze what type of content holds them the
longest, whats the trend going on insta, the type of scripting needed". So before references are chosen (G0), the watcher
makes sure the reel's audience has a FRESH playbook (14 days or newer) in `audiences/<slug>.md`; if not, it builds or refreshes
it first. Every claim in a playbook comes from data or a named source; nothing is assumed from stereotypes.

## What a playbook holds (template below)
1. Who: the audience in one line as the brief gives it (age band, region/city tier, language(s), what they buy, price tier).
2. What holds them longest (measured): from the top reels this audience watches - pick 20-40 from creators/hashtags/brands
   they follow (Apify: Instagram hashtag + creator reels, Meta Ad Library ads aimed at them), rank by views per follower and
   comments per view, then run `reel_factory.library analyze` + `aggregate` on the top ones for the numbers: length, first
   word / first cut time, words per second, cuts per 10 s, on-screen text share, faces vs product, humour/POV/skit vs polished
   ad, creator voice vs brand voice, captions on/off. Keep the numbers as p20 / median / p80 (like style.json).
3. What is trending now (last 30 days): formats (POV, "get ready with me", before/after, skit, ASMR, voiceover montage),
   trending audio on Reels, memes or phrases, hashtags; festivals and seasons in the next 30-45 days for the region.
4. How to script for them: language mix and script (e.g. Hinglish in Roman for urban Gen Z; Gujarati for Gujarati home
   cooks), slang they use and words that sound "uncle/ad-like" to them, tone, the first line pattern that works, length.
5. What to avoid: what reads as an ad and gets skipped, claims they distrust, visual looks that read as AI.
6. Our results: per reel made for this audience, the hook rate and hold rate once the ad has run (filled from Meta later).
7. Sources and date of every part.

## Refresh
- Weekly with the reference refresh (n8n "Reel Factory: Find References"), or when a reel is requested for an audience
  whose playbook is older than 14 days.
- A playbook changes the rubrics' "audience fit" points (G0 #4, G1 #4) for reels made for it: judge against the playbook,
  not against general taste.
- Brainstorm from it: a trend in the next 30 days the reel could use, a format this audience holds on that the client has
  never tried, a language variant.

## Template (`audiences/<slug>.md`)
```
# <audience name> (refreshed <date>, from <N> reels)
Who: ...
Holds them (p20 / median / p80): length ..., first cut ..., words/s ..., cuts/10 s ..., text on screen ...; works: ...; skips: ...
Trending now (<date range>): formats ..., audio ..., phrases ..., festivals ahead ...
Script for them: language ..., tone ..., first-line patterns ..., words to avoid ...
Avoid: ...
Our results: <reel> hook ...% hold ...% (Meta, <date>)
Sources: ...
```
