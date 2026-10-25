# Tools radar: what we have, what each replaces, what to look for next

Before anyone hand-builds a step, the watcher checks this list, then searches. Update it when a tool is added or dropped.

| Need | Tool we have | Notes |
|---|---|---|
| Effects, transitions, text, motion graphics | HyperFrames CLI (`npx hyperframes`, 448 catalog moves incl. shader zoom blur, light, glitch) | search `npx hyperframes catalog --query "<effect in plain words>"` before coding an effect |
| Copy a reference edit's camera moves exactly | `tools/remake/measure_motion.py` + `recut.py` ("move": "ref") | measured replay beats hand-built effects |
| Reference videos (Instagram, Pinterest, Meta Ad Library) | Apify actors via n8n "Reel Factory: Find References" | ~$1.5-2.7 per 1,000 results; free $5 credit for tests |
| Pictures from references + our pack | Codex on the VPS (`tools/vps/codex_image.sh`, DTJ's ChatGPT login) | ChatGPT in a browser only when Codex cannot |
| Motion clips | Google Flow (Omni 1.1 Flash), Frames mode, 6/8 s | in the VPS Chrome via the Playwright MCP |
| Remove Flow's sparkle | `reel_factory.watermark.Remover` (LaMa) | Harsh's decision 21 Oct |
| Paste the real pack over a garbled small pack | `tools/remake/fixpack.py` | boxes measured on a grid |
| Erase another brand's marks from a frame | `tools/remake/clean_brand.py` (LaMa) | edit BOXES per reference |
| Captions | Remotion (`captions-remotion`, free for teams of 3 or fewer) or libass | HyperFrames is the licence-free option |
| Beat / music onsets | `reel_factory.beats` | |
| Speech timing | Whisper (`reel_factory.media.words`) | CPU on the VPS: slow; consider faster-whisper |

Look for (not decided, propose with evidence when the need shows up):
- Licensed SFX (whoosh, impact, riser) library for zoom-blur cuts.
- Depth-based 2.5D parallax for stills (e.g. Depth Anything) when a reference moves inside a still.
- faster-whisper / whisper.cpp for CPU speed on the VPS.
- OCR with Indian scripts: tesseract eng+hin+guj (installed on the VPS by setup_reel.sh when the watcher needs it).
