# Reel factory

A product picture + 1-5 winning reels in, one finished 9:16 UGC ad reel out. Made the way DTJ made book-01 and senso-01 by hand
(20-21 Oct 2026), now in code: ChatGPT and Google Flow in a logged-in Chrome on the reel VPS (no API), every take checked,
Flow's sparkle removed with LaMa, edited with FFmpeg, captioned with Remotion. The runbook is the skill `dtj-ugc-reel`.

```
n8n "Reel Factory: New Reel" (form)  ->  dtj_reel_jobs row  ->  waits for Claude Code
reel VPS: listen.py --workflow "Reel Factory: New Reel"  ->  Claude Code runs reel_factory.job stages  ->  reply.py
```

| Module | What it does |
|---|---|
| `job.py` | The stages: new, refs, lint, character, images, pick, clips, check, edit, result |
| `breakdown.py` | A reference reel's cuts, words, pace, loudness, 4 fps sheets |
| `chatgpt.py` | Character (fresh chat, text only) and product in hand (fresh chat) |
| `flow.py` | Google Flow over CDP: settings, upload, attach by asset id, generate, download |
| `checks.py` | Words said, product tracker (drops, floats, jumps), caption placement, claims in a line |
| `watermark.py` | Flow sparkle removal (LaMa) and the final-corner check |
| `beats.py`, `captions.py`, `edit.py` | Beat cuts, caption pages, the edit and loudness |
| `remotion.py` + `captions-remotion/` | Animated captions (Remotion: free for up to 3 people; the libass version is the fallback) |

Set up a VPS: `bash setup_vps.sh` (Ubuntu with a desktop), then a person signs in to Google and ChatGPT once in `~/dtj/reel-chrome.sh`.
Tests (no browser, GPU or video): `python -m unittest discover -s tests -t .`
