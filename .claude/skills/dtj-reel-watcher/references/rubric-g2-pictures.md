# G2 Pictures (ChatGPT / Codex) before Flow credits are spent (100 points for the set, pass/fix per picture)

Look at every picture next to its cleaned reference frame (`watch/g2_pairs.jpg`) and read `watch/g2.json`: per picture
`layout_similarity` (0-1, edges/structure vs the reference frame), `pack_text` (OCR words found vs the real pack's words),
`foreign_marks` (other brands' words found by OCR), `grade` (colour distance to the neighbouring shots).

| # | Check | Points |
|---|---|---|
| 1 | Matches its reference frame: same angle, crop, props, light, depth of field (layout_similarity >= 0.55 and it looks the same) | 25 |
| 2 | Real-photo look, no AI slop: no glossy/HDR sheen, no plastic skin, no extra props, embers or clutter the reference lacks, no warped hands or cutlery | 25 |
| 3 | Pack exactly the real one: logo, name, words in the right script, colours, proportions (pack_text match >= 0.6; zoom to check small packs). Compare with the REAL pack picture (`inputs/` / the request's product pictures), never with how you think the name is spelled: the pack's own printing wins even when it looks like a typo (Mahalaxmi's box prints "MAIHALAXMI®"). No pack picture in the job = say so, do not judge spelling | 20 |
| 4 | No other brand anywhere (foreign_marks empty; their logo corner, "Available on" strips, store names) | 15 |
| 5 | One look across the set: bright shots match each other, red/stylised shots match each other (grade distance small) | 15 |

Blocking (that picture goes back): another brand's mark; garbled pack text the viewer can read (fix: paste the real pack,
tools/remake/fixpack.py); slop look Harsh would call AI; a picture that does not match its reference frame. Ideas: a picture
the reference does not have but would help (a pack close-up for the end), a lighting fix that would make the set feel shot
on one day.
