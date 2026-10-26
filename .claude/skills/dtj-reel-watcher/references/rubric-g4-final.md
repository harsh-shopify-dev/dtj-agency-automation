# G4 Final reel before the person's last Approve (100 points)

Watch the reel at full speed with sound, once with sound OFF, and the 30 fps sheets around every cut next to the reference.
Read `watch/g4.json`: `motion_gap` per shot (our measured zoom/shift/blur vs the reference's, from measure_motion.py on both),
`cuts_vs_beats` (each cut's distance to the nearest music onset, ms), `lufs`, `black_or_flash`, `safe_zone` (logo/text
inside top 14 % / bottom 35 % / sides 6 %), `spec` (1080x1920, h264/aac, fps, size), `pack_share` (share of time the pack is
visible), `duration` vs the reference, `realism` (realism.measure for UGC).

| # | Check | Points |
|---|---|---|
| 1 | Edit matches the reference: same cut times, the same arrivals/exits/effects on the same frames (motion_gap small on every shot) | 20 |
| 2 | Hits on the beat: cuts and effects within ~40 ms of the music's hits; no hit missing where the reference has one | 10 |
| 3 | First 3 s stop the scroll (the reference's hook kept; pack or dish clear by 3 s) | 10 |
| 4 | Every frame clean: no slop look, garbled pack, other brand's mark, sparkle, black or flash frame | 20 |
| 5 | Sound: music level -14 LUFS +-1, no clipping, VO over music audible (UGC), no silent gaps | 10 |
| 6 | Text and logo in the safe zones; captions readable with sound off (UGC: script spelling, never on a face) | 10 |
| 7 | Brand: our logo where theirs sat, end card, the product named right, no burned-in AI line (added at posting) | 10 |
| 8 | Spec: 9:16 1080x1920, h264 + aac, length within 10 % of the reference (15-30 s typical for Reels ads) | 10 |

Blocking: any other brand's mark; a garbled or wrong pack readable; a black/flash frame; LUFS outside -16..-12; a missing
reference effect Harsh would notice; wrong spec. Ideas: SFX the reference implies (whoosh on zoom cuts) if we have a licensed
source; a hook-only variant for testing; a cutdown (6-10 s) for Stories; a regional caption version.
