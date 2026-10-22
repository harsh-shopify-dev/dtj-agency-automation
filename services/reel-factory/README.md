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

## VPS picture route (store pictures from ChatGPT on the VPS)
Harsh, 22 Oct 2026: "we will use chatgpt cli which will be hosted on our hostinger vps". The store factory's pictures (sample
products, banners, our product in a new scene) are made by `reel_factory/chatgpt_cli.py` in the same logged-in reel Chrome, one
fresh chat per picture, with photos of OUR product attached as the reference. The laptop calls it over ssh
(`services/store-builder/provision/ai_images.py`, backend `vps`); no API key.

Once on the VPS (as user `ai`):
1. The repo checked out at `~/dtj-agency-automation` (or set `DTJ_IMAGE_VPS_DIR` on the laptop to the reel-factory folder used).
2. `bash setup_vps.sh` (it installs playwright in `~/dtj/reel-venv`; the command uses that Python, else `python3` with
   `pip install playwright`).
3. The reel Chrome open with `~/dtj/reel-chrome.sh` (DevTools on 127.0.0.1:9222 only) and ChatGPT signed in once by a person.
4. The laptop's PUBLIC key (`~/.ssh/id_ed25519.pub` on the laptop) added as one line to `/home/ai/.ssh/authorized_keys`.
   Never the private key.

Check by hand on the VPS: `cd ~/dtj-agency-automation/services/reel-factory && ~/dtj/reel-venv/bin/python -m reel_factory.chatgpt_cli
image --prompt-file p.txt --out /tmp/test.png --ref product.jpg`: one JSON line, `"ok": true` (exit 1 = ChatGPT said no or needs a
person, 2 = the reel Chrome is not open).

On the laptop (Windows user variables, no secrets): `DTJ_IMAGE_VPS` = the ssh target, e.g. `ai@srv2048145.hstgr.cloud`; optional
`DTJ_IMAGE_VPS_DIR` = the reel-factory folder on the VPS (default `~/dtj-agency-automation/services/reel-factory`). Then
`python -m provision.ai_images --kind product --prompt "..." --ref <photo> --out <file> --dry-run` (from `services/store-builder`)
shows `"route": "vps"`. Each picture uses a fresh `/tmp/dtj-img-<id>` folder on the VPS, and only that folder is removed afterwards.
Tests (no browser, GPU or video): `python -m unittest discover -s tests -t .`
