# Vibe calibration log

Every time Harsh (or a client) gives a verdict on a page's look, add a row. When a verdict and the metrics disagree twice in the
same direction, adjust `scripts/vibe_profiles.json` and note the change here. This is how the numbers stay honest.
Always record BOTH the full-page fit and the `ui_only` fit (pictures masked with `--mask`): our design is the `ui_only` number.

| Date | Page | Profile | Full page (white / dark / vivid / colourfulness, fit) | UI only (fit) | Human verdict | Action |
|---|---|---|---|---|---|---|
| 2026-10-10 | Go Mints Energy + Focus, Test Store `products/gomint?view=dtj-gomint`, 1280 px, header skipped, blank stretches removed | electric | 0.364 / 0.017 / 0.152 / 77.7, fit 60 (all of the colour comes from the pack banner photo, used 11 times) | 0 (about 60% white + 35% pale tint #E6F2F5, about 1% vivid, 1% dark; measured by the review test run) | Harsh: "ultra light cyan ... looks dull and doesn't give much vibe" | Agrees with the targets when judged on UI only. First entry (fit 40, 74% white) was wrong: the tall headless window added blank space; `palette_report.py` now drops blank stretches over 300 px. |
