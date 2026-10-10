# CRO rubric for a DTJ product page (score out of 100, plus blocking findings)

Score each check from the evidence (screenshots at 390 and 1280, `page_audit.js` output on the live page, `template_audit.py`
output on the build, `palette_report.py` output, the facts and the wireframe plan). Write the evidence next to every score: a
number, a quote or a screenshot region. No evidence = 0 for that check, never a guess. Same evidence must give the same score:
use the thresholds as written.

## Blocking findings (any one = FAIL, whatever the score)
- B1 Anything invented: a review, rating, count, quote, guarantee, study or claim without a source in `facts.json`.
- B2 The buy button says "Sold out" or is missing on the first phone screen (unless Harsh knows and accepts it).
- B3 Price wrong: compare-at not real, savings badge maths wrong, price different from the store.
- B4 Body text or the buy button below 4.5:1 contrast; any text below 3:1.
- B5 The page scrolls sideways on a phone (`overflowing_sideways: true`).
- B6 Test pictures or demo content on a CLIENT store page.
- B7 A broken picture, an empty heading, or editor-only text visible to shoppers.

## 1. First phone screen, 390 x 844 (20 points)
| Check | Points | Full marks when |
|---|---|---|
| Product picture shows the product clearly | 4 | pack or product fills most of the picture; no text wall on the picture that duplicates the page |
| Title says benefit + product name | 4 | not a placeholder ("gomint" = 0); at most 2 lines |
| Price with the real saving | 4 | price visible; compare-at and saving shown only when real |
| Real rating / proof line above the title | 4 | stars + count from a real source (0 when none exists: report as content needed, not as a design fault) |
| Buy button visible without scrolling, loudest element | 4 | visible in the first screen; highest contrast and saturation in view |

## 2. Story: problem, solution, proof, outcome (15)
| Check | Points | Full marks when |
|---|---|---|
| The problem is named in the shopper's words | 4 | a slot states the pain or the situation (tired at 3 pm, dull skin...) |
| The mechanism: HOW the product solves it | 4 | ingredient / process / design explained in one or two sentences with a source |
| The outcome: what the shopper's day looks like after | 4 | concrete, sourced, no medical promise |
| The order follows the wireframe | 3 | slots in W-order; omissions only by the omit rules |

## 3. Proof and trust (15)
| Check | Points | Full marks when |
|---|---|---|
| Real reviews / UGC on the page | 5 | at least 3 real items (0 when none exist: content needed) |
| Numbers with sources (customers, results, studies) | 3 | each number traceable |
| Guarantee and policies visible near the buy button | 4 | returns, shipping time, COD, guarantee: whichever are real |
| Credentials (FSSAI, certifications, Made in India, press) | 3 | shown where they exist |

## 4. Objections answered (10)
| Check | Points | Full marks when |
|---|---|---|
| FAQ covers price/value, use, safety, results time, shipping/COD, returns | 6 | 1 point per topic covered with a real answer |
| How to use is clear | 4 | steps or a one-line routine near the top or in the FAQ |

## 5. Repetition and density (10)
| Check | Points | Full marks when |
|---|---|---|
| No claim more than twice | 4 | `template_audit` repeated_text and near_duplicates empty beyond home + recap; minus 1 per extra repeat |
| No picture more than twice | 3 | `images_used_3plus` empty (demo pages: still counts) |
| Each section has one job and is not thin | 3 | no section with fewer than its minimum items; no wall of text over 3 lines on a phone |

## 6. Calls to action (10)
| Check | Points | Full marks when |
|---|---|---|
| A CTA at least every 1.5 phone screens | 4 | `longest_gap_px` <= 1300 at 390 px (about 1.5 screens) |
| One label, one action | 3 | `labels` has one wording (plus the buy button) |
| CTA contrast and size | 3 | 4.5:1 text, at least 44 px tall, the most saturated colour in its view |

## 7. Vibe and visual quality (15)
| Check | Points | Full marks when |
|---|---|---|
| Palette fits the vibe | 6 | `palette_report` fit_score: >= 80 = 6, 60-79 = 4, 40-59 = 2, < 40 = 0 |
| Rhythm: neighbouring sections differ, strong bands paced | 3 | no two neighbours share a background; electric pages have 3-5 strong bands |
| Motion fits the vibe | 3 | per `motion-by-category.md`; at most one self-moving element per screen |
| Typography and spacing | 3 | headings at the vibe's weight; nothing under 12 px; consistent radius |

## 8. Mobile craft (5)
| Check | Points | Full marks when |
|---|---|---|
| Pictures first, text short, carousels show a partial next card | 3 | as in the wireframe's mobile frames |
| Tap targets and legibility | 2 | `small_tap_targets` only in theme chrome; `text_under_12px` <= 2 |

## Verdict
- 80-100 and no blocking finding: PASS (ready for Harsh's approval).
- 65-79: FIX (list the fixes; rebuild; review again; at most 3 rounds).
- Below 65 or any blocking finding: FAIL (redesign the plan, or stop and ask for content).
Points lost only because the client has not sent content (reviews, UGC, guarantee) are listed separately as "content-limited"
so Harsh can see how far design alone can go.
