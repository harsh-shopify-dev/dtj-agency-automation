# G3 Flow clips (pass / redo per clip, 100 points for the set)

Read each clip's 4 fps sheet and `watch/g3.json`: `product_visible_pct` and `drift` (checks.ProductTracker), `flicker`
(mean frame-to-frame change outside motion), `sparkle_left` (watermark.residual), `start_match` (first frame vs the start
picture), `black_or_flash` frames.

| # | Check | Points |
|---|---|---|
| 1 | The action is right and natural (the pour pours, the flame bursts, the hand places the plate), in the window the edit uses | 25 |
| 2 | Product continuity: one product state, no drop, float, teleport, smear or a different pack (drift small, visible where planned) | 25 |
| 3 | Hands and objects: no extra or melted fingers, no bending cutlery, no objects merging | 20 |
| 4 | Clean: no Flow sparkle left, no flicker, no sudden exposure jump, no black/flash frame | 15 |
| 5 | Starts on the start picture (start_match high) and the camera does what the prompt said (locked-off when asked) | 15 |

Blocking (redo that clip, at most 3 rounds then "needs a look"): wrong or different product; hand/object horrors in the used
window; sparkle left. Ideas: a prompt change that would have avoided the problem (write it), a still with edit motion
instead of a clip when the clip keeps failing (cheaper, Harsh 24 Oct: stylised shots are stills).
