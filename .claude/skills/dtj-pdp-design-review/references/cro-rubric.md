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
| Product picture shows the product clearly | 4 | the FIRST gallery picture is the product (not the founder, not a stats card); pack or product fills most of it; no gallery picture prints a claim the facts do not support (Alpha Arbutin on a serum without it, before/after without proof). 0 when a gallery picture prints a contradicted claim |
| Title says benefit + product name | 4 | not a placeholder ("gomint" = 0); at most 2 lines |
| Price with the real saving | 4 | price visible; compare-at and saving shown only when real |
| Real rating / proof line above the title | 4 | stars + count from a real source (0 when none exists: report as content needed, not as a design fault) |
| Buy button visible without scrolling, loudest element | 4 | visible in the first screen; highest contrast and saturation in view |

## 2. Story and voice: problem, solution, outcome, the feeling (15)
| Check | Points | Full marks when |
|---|---|---|
| The problem is named in the shopper's words | 3 | a slot states the pain or the situation (tired by the afternoon, dull skin...) |
| The mechanism: HOW the product solves it | 3 | ingredient / process / design explained in one or two sentences with a source |
| The outcome: what the shopper's day looks like after | 3 | concrete, sourced, no medical promise |
| The order follows the wireframe | 1 | slots in W-order; omissions only by the omit rules |
| Voice: the copy makes the shopper feel it | 3 | the buy-box short description and the section headings pass `../dtj-pdp-factory/references/copywriting.md` section 8: a sensation or picture (1), a verb doing the work and a rhythm (1), a line no competitor could say word for word (1). Plain-but-true copy scores 1 |
| Buy-box points are benefits | 2 | `design_checks` H06 passes: no dose or measure; each point is a result for the shopper (1 point off per spec line, min 0) |

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
| Each section has one job and is not thin | 3 | no section with fewer than its minimum items; no wall of text over 3 lines on a phone; story cards within `design_checks` H05 (fail = at most 1) |

## 6. Calls to action (10)
| Check | Points | Full marks when |
|---|---|---|
| A CTA at least every 1.5 phone screens | 4 | `longest_gap_px` <= 1300 at 390 px (about 1.5 screens) |
| One action, each label named after its section | 3 | `labels` has as many wordings as buttons (no repeats, lint L16); each is a buying action that echoes its section; all do the same thing (Harsh, 10 Oct 2026, replaced "one label") |
| CTA contrast and size | 3 | 4.5:1 text, at least 44 px tall, the most saturated colour in its view |

## 7. Vibe and visual quality (15)
| Check | Points | Full marks when |
|---|---|---|
| Palette fits the vibe | 5 | `palette_report` fit_score: >= 80 = 5, 60-79 = 3, 40-59 = 2, < 40 = 0 |
| Rhythm and dark weight | 3 | no two neighbours share a background (1); at most 2 dark sections, the closing banner counted (`design_checks` H08) (1); dark used for cards and boxes on light ground, not as the default ground (1) |
| Motion fits the vibe | 2 | per `motion-by-category.md`; at most one self-moving element per screen |
| Typography and spacing | 2 | headings at the vibe's weight and in the brand's font; consistent radius |
| Figure and ground | 3 | 1 point each for `design_checks` H01 (cards stand apart), H02 (words on cards read at 4.5:1), H03 (icons stand apart from their words); minus 1 per section H10 flags (one colour on the card, words, ticks and button, nothing white), minimum 0 |

## 8. Mobile craft (5)
| Check | Points | Full marks when |
|---|---|---|
| Pictures first and whole, text short, carousels show a partial next card | 3 | as in the wireframe's mobile frames; no single picture cropped (`design_checks` H07; 1 point off per cropped picture) |
| Tap targets and legibility | 2 | 1 point: `text_under_12px` <= 2 and `small_tap_targets` only in theme chrome; 1 point: `text_near_edge` empty |

## Verdict
- 80-100 and no blocking finding: PASS (ready for Harsh's approval).
- 65-79: FIX (list the fixes; rebuild; review again; at most 3 rounds).
- Below 65 or any blocking finding: FAIL (redesign the plan, or stop and ask for content).
Points lost only because the client has not sent content (reviews, UGC, guarantee) are listed separately as "content-limited"
so Harsh can see how far design alone can go.
