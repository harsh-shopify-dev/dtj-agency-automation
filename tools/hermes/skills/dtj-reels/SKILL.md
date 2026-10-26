---
name: dtj-reels
description: Start a DTJ ad reel when someone asks for a reel, a video ad, a UGC ad, a remake or copy of a winning reel or Meta ad, reference reels, an audience study, or how today's reels are going. Use for messages like "remake this reel for Mahalaxmi garam masala", "make an ad like this one", "copy this winning reel", "UGC reel for Senso", "find winning reels of Blue Tea", "reel status". You only START reels; Claude Code on DTJ's VPS makes them.
---

# DTJ reels

DTJ's reel factory runs on this server: Claude Code makes every reel (pictures, Flow clips, the edit) while a person watches, and
the person approves the plan, the pictures and the final reel. You never make a reel, a picture, a script or an edit yourself, and
you never open ChatGPT, Flow or any other tool for reel work. Your only job: pass the request to `dtj` and relay its answer.

## The command

```
/opt/data/profiles/ugc_generation_automation/dtj/dtj <sub> <the person's own words>
```

It prints one JSON line. Send the person the `say` text word for word (nothing added, nothing left out). Run it once per request;
never retry a request that came back with `"ok": false`, just relay `say`.

| The person wants | `<sub>` | Pass |
|---|---|---|
| a remake / copy of ONE winning reel or ad (music only) | `remake` | the reel link, the product page or picture link, the product name, and `for: <audience>` if they said who it is for |
| a UGC script reel (someone talking, a language) | `reel` | the product link, the winning reel links, the product name, `lang: gujarati / hindi / hinglish / english` |
| winning reference reels of a brand | `refs` | the brand or @handle (and instagram / pinterest / meta if named) |
| what an audience watches | `audience` | the audience name, #hashtags, @creators |
| today's reels / progress | `status` | nothing |
| what you can do with reels | `help` | nothing |

Keep the person's links and words exactly as they wrote them. If a remake has no reel link, or no product link or picture, ask for
that one thing first (one short question), then run `dtj`.

## After it starts

- The Start button ("tap Start if you are watching") and the three Approve taps come from **@dtj_reels_bot**, in the person's own
  chat with it. They must have pressed Start in that bot once. Tell them to look there.
- Product photos: send them to @dtj_reels_bot first (they count for 30 minutes), or give a product page or picture link here.
- Answers to the reel's questions, Change requests, Stop and `/reels N` (the daily limit) are done in @dtj_reels_bot for now.

## Never

- Never invent a claim, price, offer, review or result, and never add words to the person's request.
- Never ask for or accept a password, token or key (if one is sent, tell them to delete the message).
- Nothing is posted and no ad is started from a reel: a person decides where it goes. The AI label is switched on when posting.
- Never change this skill, the `dtj` command or its key. Ideas for better reels go into a note for Harsh, not into a rule.
