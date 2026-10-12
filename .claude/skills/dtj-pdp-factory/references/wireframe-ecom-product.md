# DTJ Standard Product Page v1: the fixed sections (from the ThrillX wireframe)

Source: Figma file "Public Landing Page - ThrillX", page "LANDING Page Public", frames **Home - Desktop** (node `2460-4368`,
1440 x 8382) and **Frame 176** (mobile, node `2460-5367`, 414 wide). Read on 10 Oct 2026. Screenshots of every part are in
`../assets/wireframe/` (desktop-01..06, mobile-01..12): open them when a section below is unclear.

**Harsh's decision (10 Oct 2026): every product page uses exactly these sections, in this order, built with exactly this block,
whatever the product.** No section is chosen, dropped or reordered per product or category. What changes per brand is only the
content (words, numbers, pictures) and the colours (the vibe). When a brand grows, a human CRO expert customises from this base.
New sections are added to this list only by building them (see section 3) and with Harsh's yes; then they are used every time.

## Contents
1. The fixed set (the authority)
2. Rules for every section, including sample content
3. Each section in detail (purpose, content, desktop, mobile, settings)
4. What is not built yet (gaps)

---

## 1. The fixed set

| # | Wireframe | Section | Block (always this one) | Ready today |
|---|---|---|---|---|
| 0 | W00, W01 | Announcement bar, header with anchor links | theme (recommend in `theme_todo`, never pushed with the page) | theme |
| 1 | W02 | Buy box: rating line, title, price + saving, one-line benefit, 4 benefits, options, bundles, add to cart, trust icons, accordions | `dtj-social-proof`, theme title, `dtj-price`, `dtj-hero-points`, theme variant picker, `dtj-addons`, theme buy buttons, (G2 trust icons), (G7 theme accordions) | yes, except G2 / G7 |
| 2 | W03 | Customer photos and videos strip | `dtj-shoppable-reels` | block yes, builder no (G9) |
| 3 | W04 | Benefit strip | `dtj-marquee` | yes |
| 4 | W05 | Big benefit #1, picture LEFT | `dtj-split-story` (image_side start) | yes |
| 5 | W06 | Big benefit #2, picture RIGHT, 3 sub-benefits | `dtj-split-story` (image_side end) | second copy: builder no (G9); accordion form G4 |
| 6 | W07 | Reviews | `dtj-testimonials-slider` | yes |
| 7 | W08 | Why us: 6 differentiators (3 x 2) | `dtj-whats-inside` (columns 3) | builder mapping no (G9) |
| 8 | W09 | Benefit strip #2 | `dtj-marquee` (second copy) | builder no (G9) |
| 9 | W10 | Big benefit #3: 4 benefits with icons + picture | `dtj-feature-showcase` | yes |
| 10 | W11 | Money-back guarantee | `dtj-cta` style banner (NEW, G1) | no: being built |
| 11 | W12 | Proof in numbers | `dtj-stat-cards` | partly |
| 12 | W13 | FAQ | `dtj-faq` (picture beside it: G3) | yes |
| 13 | W14 | Customer stories (photo + quote) | `dtj-stories` | builder no (G9) |
| 14 | W15 | Final push: photo, reason to buy today, button | `dtj-slideshow-pro` with ONE slide | builder no (G9) |
| + | after 2, 4, 5, 6, 7, 9, 11, 12, 13 | "Shop now" button | `dtj-cta` style button (NEW, G1) | no: being built |

Not in v1 (not in the wireframe): how-to steps, "what's not inside", comparison table, science stats, measured results.
How to use and safety go into the FAQ. A CRO expert may add the others later for a grown brand.

## 2. Rules for every section

- **Fill every section, always.** During design every section is filled completely so Harsh sees the whole page. Content comes
  from, in this order: the client's facts, the brand's own public pages (product page, FAQ, policies, review widgets: with the
  URL and date as the source), the pack and product pictures, and finally **sample content** for whatever is still missing.
- **Sample content (Harsh's decision, 10 Oct 2026):** realistic but modest values that make the design complete, which Harsh
  replaces or signs off before the page goes live. Rules:
  - Every sample value is marked: its `source` starts with `SAMPLE` (e.g. `"SAMPLE: replace before live"`). The build report
    lists every sample by section; that list is Harsh's checklist.
  - Allowed as samples: customer counts, ratings and review counts, reviews (Indian first name + city, believable everyday words),
    UGC captions, stat numbers, guarantee days, delivery days, differentiators phrased as the brand's own promise.
  - NEVER samples, even in a draft: medical or disease claims, "clinically proven" / "doctor recommended", comparisons naming a
    competitor, certifications or licence numbers (FSSAI, ISO, GMP), prices, discounts and offers (prices come live from the store).
    For these, leave the setting empty and list the content needed.
  - Pages with samples go only to a DRAFT theme (or our own test store with Harsh's yes). Never to a client's live theme until
    every sample is replaced or Harsh signs each one off.
- **Pictures:** use the client's real pictures first, each at most twice. When there are not enough, a product picture may fill
  a slot as a sample picture (listed in the graphics brief with what the real picture should show).
- **One job per section.** Each section answers one shopper question (below). No claim in the same words in two sections
  (the claim ledger in `section-design-method.md`); the buy box may recap up to 4 claims.
- **One action, a label per section** (Harsh, 10 Oct 2026: "every CTAs have the same text, they should be named accordingly with
  what the section says"). Every button does the same thing: it scrolls to the buy box when there are several variants or
  bundles, and adds to cart when there is one variant. Each label is a buying action in its section's words, for example "Make the
  switch" after "What people say after the switch" or "Feel it in 4 minutes" after the numbers. Labels are 2-5 words, at most 24
  characters, verb first, never a reading label ("Learn more"). No two buttons say the same thing (lint L16). The last button
  (W15) keeps the brand's main label. The builder gives every section a neutral default; the copy step renames it (`copy_contract.py`).
- **Backgrounds alternate** (lint L04) using the vibe's roles (`colour-and-vibe.md`): white, surface, brand colour, dark band.
- **Picture side:** W05 left, W06 right, W10 right, W13 left (desktop). On mobile the picture is always first.
- **Pictures keep their own shape** (Harsh, 10 Oct 2026: "the section should adapt to image size"). Every single picture uses
  the block's adapt option (split story `image_fit adapt`, science stats `adapt`, final banner `ratio adapt` on phone and
  desktop), so a pack shot is never cut at the edges. Card rows (W03 reels, W14 stories) need one shape per row, so the graphics
  brief asks for that shape instead: W03 tall 9:16, W14 square 1:1, W15 wide (about 21:9) with calm space in the middle and no
  printed text. A square picture in W15 gives a square banner: fine on a phone, very tall on desktop.
- **Story cards are short** (Harsh, 10 Oct 2026: "keep the content short and to the point"; lint L17): W05 / W06 paragraph at
  most 20 words, 4 points of at most 32 characters each.
- **Buy box points are benefits** (Harsh, 10 Oct 2026; lint L18): what the shopper gets ("Fast-acting energy", "Fits in your
  pocket"), never a spec ("Natural caffeine 50 mg"). Doses and measures belong in W06, W08 and W12.
- **Mobile first:** about 80 percent of Indian D2C traffic is on phones. Design and review at 390 px first.
- **Headlines are benefits** (the wireframe's "Value prop and Big Benefit (WIIFM)"): what the shopper gets, at most 8 words.

## 3. Each section

### 0. W00 / W01 Announcement bar and header (theme)
Announcement: ONE true line: free-shipping threshold, COD, money-back days or a real sale. Header: logo, 4 anchor links to page
sections (Benefits, Reviews, FAQ...), account, search, cart. Both are theme-wide: write them in `theme_todo`, never push them
with the page.

### 1. W02 Buy box (desktop-01, mobile-01..04)
Desktop: gallery left (about 45 percent), buy column right. Mobile: gallery first. In this order:
| # | Element | Block | Content |
|---|---|---|---|
| a | Gallery + product tag ("Best Seller", "New") | theme gallery (tag: G5) | clean pack shot first (no picture with printed claims as the first picture) |
| b | Stars + "Rated X/X by XXX+ customers" above the title | `dtj-social-proof` | badge 2-3 words (L15), 5 round photos (L14), rating: real or SAMPLE |
| c | Title "{Biggest benefit} - {Product name}" | theme title | the store's product title: propose the new one in `product_todo` |
| d | Price, struck compare-at, "You save Rs X (Y%)" | `dtj-price` | live from the store; compare-at only if real |
| e | One sentence: the biggest benefit and how the shopper gains | `dtj-hero-points` subheading | 2 lines on a phone |
| f | 4 benefits (wireframe: icons; Harsh's rule: always exactly 4): what the shopper gets, never a dose or measure (L18) | `dtj-hero-points` ticks (icon row: G2) | |
| g-h | Divider; colour / size options; size guide (apparel) | theme variant picker (`dtj-shade-picker` across products; size guide G6) | |
| i | Bundles: 3 tiers, "MOST POPULAR", total with saving | `dtj-addons` | only bundles that exist in the store (never sampled) |
| j | ADD TO CART, full width, loudest colour | theme buy buttons | |
| k | 3 trust icons: returns, shipping, guarantee | G2 `dtj-icon-row` | real or SAMPLE policy words |
| l | Accordions: details, FAQ, how it works, shipping and returns | theme accordions (G7) | |

### 2. W03 Customer photos and videos strip (desktop-02, mobile-03/04)
Answers "do real people like me use it?". 3-6 photos or short videos of customers or creators, heading, CTA. Desktop: full-width
band, 3 cards visible, more scroll sideways. Mobile: about 1.3 cards visible. Block `dtj-shoppable-reels` (image or video per card).
Sample: product pictures as sample cards, listed in the graphics brief ("UGC video: customer opening the pack"). Background:
white on every page (Harsh, 10 Oct 2026), so the photos carry the colour. Cards are tall (9:16): ask for vertical pictures.

### 3. W04 Benefit strip (desktop-02, mobile-04)
Answers "what do I get, at a glance?". 5-7 benefits of 2-3 words with an icon each, not the buy-box 4 in the same words. Block
`dtj-marquee`: moving on electric and playful vibes, slow on others (`motion-by-category.md`).

### 4. W05 Big benefit #1 (desktop-02/03, mobile-06)
Answers "what is the main thing it does for me, and how?". Headline (the biggest benefit), ONE sentence on how it works
(mechanism, ingredient, process; at most 20 words), 4 points of at most 32 characters, a picture that shows it, CTA. Desktop
picture LEFT; mobile picture on top. Block `dtj-split-story` (image_side start, image_fit adapt). Go Mints v2 was too long
(23 words + points of up to 38 characters under a full picture, measured by `design_checks.py`); v3: "Caffeinated mints that melt in your mouth, anytime, anywhere."

### 5. W06 Big benefit #2 (desktop-03, mobile-07)
Answers "what else does it do?". Headline, 3 sub-benefits (title + one line each; the wireframe shows them as an accordion, G4),
CTA, picture RIGHT (mobile: on top). Block `dtj-split-story` (image_side end). Same length limits as W05 (lint L17).

### 6. W07 Reviews (desktop-03, mobile-05)
Answers "can I believe it?". 4-8 reviews (stars, a short headline, 2-3 lines, name and city), the overall rating, CTA. Block
`dtj-testimonials-slider`. Real reviews first (reviews app export, the brand's public widget); SAMPLE reviews otherwise.

### 7. W08 Why us (desktop-04, mobile-08)
Answers "why this and not the usual alternative?". Benefit-driven headline ("how you do it and what makes you different"),
6 cards (title + one line) in 3 x 2, CTA. Mobile: stacked (or 2 columns when short). Block `dtj-whats-inside` (columns 3,
pictures or icons optional). Never name a competitor (even as a sample).

### 8. W09 Benefit strip #2 (desktop-04, mobile-09)
Same form as W04 with DIFFERENT items: ingredients, origin, certifications the brand really has, COD, delivery. Block
`dtj-marquee` (second copy), the other direction or speed from W04.

### 9. W10 Big benefit #3 (desktop-04/05, mobile-09/10)
Answers "what will I notice day to day?". Headline, 2 sentences, 4 benefits (icon + title + one line), CTA, picture right.
Block `dtj-feature-showcase` (4 features, heading_align left, mobile_image top). Icons sit in round badges so they stand apart
from the words: white badges on a band, brand-colour badges on white (`icon_bg`; Harsh, 10 Oct 2026).

### 10. W11 Money-back guarantee (desktop-05, mobile-10)
Answers "what if it doesn't work for me?". Headline ("Love it or your money back"), 1-2 sentences with the terms (days, how to
claim), CTA, a seal. Block `dtj-cta` banner (G1). Terms: the brand's policy page, or SAMPLE days.

### 11. W12 Proof in numbers (desktop-05)
Answers "how many people / how much difference?". 3-4 big numbers with a label and a one-line note each (customers, repeat
buyers, rating, units sold). Block `dtj-stat-cards`. Real or SAMPLE numbers (never study results as samples). Electric /
playful: a white section with ink cards and accent figures (Harsh, 10 Oct 2026).

### 12. W13 FAQ (desktop-06, mobile-11)
The last doubts: price/value, how to use, safety and who should not use it, time to results, shipping/COD, returns. 5-8
questions, CTA; picture on the LEFT (desktop) / top (mobile) once G3 exists. Block `dtj-faq`.

### 13. W14 Customer stories (desktop-06)
Answers "people like me, in their own words": 3-6 cards with a photo, name, tags and a quote, CTA built in. Block `dtj-stories`.
Different people and words from W07.

### 14. W15 Final push (mobile-12; desktop: the dark band under the frame)
Answers "why today?". A background picture under a dark overlay, headline ("the final value prop and reason to buy today"), one
sentence, CTA. Block `dtj-slideshow-pro` with ONE slide (overlay solid or side, autoplay off, ratio adapt on phone and desktop).
The reason must be true (the main benefit, the guarantee, a real offer). The picture: wide, calm in the middle, no printed text
(the words sit on it on desktop).

## 4. Gaps: what must be built before every section works (build order by impact)

| Gap | What is missing | Needed by | Plan |
|---|---|---|---|
| G1 | `dtj-cta` block: style `button` (after a section) and `banner` (heading, text, seal, button) | W11 and every section CTA | built; released to the Test Store copy (10 Oct) |
| G9 | The fixed set as the builder's recipe (`recipes/dtj-standard-v1.json`) + builders for W03, W06, W08, W09, W14, W15 and the CTAs | everything | built (10 Oct) |
| V1 | `vibe` in `direction.py` (bold colours for electric / playful) | every energetic brand | built (10 Oct) |
| S1 | Sample-content tracking in the builder + the push gate (drafts only) | Harsh's sample rule | built (10 Oct) |
| G2 | `dtj-icon-row` block (buy-box icons, trust icons) | W02 f, k | later |
| G3 | FAQ with a picture beside it | W13 | later |
| G4 | Split story sub-benefits as an accordion | W06 | later |
| G5-G8 | gallery tag, size-guide pop-up, theme accordions from facts, show-on-mobile-only | W02 | later |
| D1 | Built-in shadows in Slideshow Pro, FAQ and the Split Story review card (brands with a no-shadow rule) | design fit | add a `shadow` on/off setting |
| D2 | FAQ heading always heavy uppercase | calm / editorial vibes | add a heading-case setting |
