# Designing one section: analyse the whole section first, then design it

Harsh's rule: "whenever a section is designed, first analyse the full section and then start designing it". The sections are
fixed (`wireframe-ecom-product.md`); what you design is their CONTENT and LOOK. Without this method a page comes out like the
first Go Mints page: the same four claims in five places, one picture eleven times, every section pale. Do the analysis for EVERY
section, write it down (section notes in `wireframe-plan.md`, template at the end), and only then fill the builder inputs.

## Step 0, once per page: gather all the material, then the claim ledger

1. **Material, in this order:** the client's facts; the brand's own public pages (product page, FAQ, refund / shipping policy,
   review widget: write the URL and the date as the source, e.g. "gomints.in product page, 10 Oct 2026"); the pack and product
   pictures (read what they actually print); then sample content for what is still missing (rules in `wireframe-ecom-product.md`
   section 2). Note anything suspicious you find (a policy page still holding Shopify's template text, a picture that prints an
   unconfirmed claim) for Harsh.
2. **Claim ledger:** list every claim with its source and give it ONE home section and at most one recap:

| Claim | Source (or SAMPLE) | Home section | Recap |
|---|---|---|---|
| Natural caffeine keeps you going | pack print | W05 | W02 f |
| 4,000+ happy customers | SAMPLE: replace before live | W12 | W02 b badge |

A claim appears at most twice (home + recap). The buy box may recap up to 4 claims. When the real claims run out before the
sections do, write a NEW angle for the section (a use moment, a sensation, a routine, a reason it is different) and, if it needs
a fact you do not have, make it a marked sample. Never fill a section by repeating another section's words.

## The eight steps for each section

1. **Read its spec** in `wireframe-ecom-product.md` section 3 and open its screenshot in `../assets/wireframe/`.
2. **Assign the material:** the claims the ledger gave it, pictures (what each shows), numbers (each with source or SAMPLE).
   Count against the section's item numbers (e.g. W08 needs 6 cards, W07 4-8 reviews). Fill shortfalls with marked samples;
   never with repeats.
3. **Read the block's real settings** (its `{% schema %}` in `services/<app>/extensions/<ext>/blocks/dtj-<block>.liquid`, or
   the catalog). Know the item limits, select values and ranges. Never plan a setting the block does not have.
4. **Write the words:**
   - Headline: a benefit, at most 8 words, sentence case, the brand's voice; not a bare feature or label.
   - Body: at most 2 lines on a 390 px phone (about 90 characters per line), one idea.
   - Items: the same grammatical shape for every item; icon labels 2-5 words.
   - Samples: believable and modest (a new D2C brand has hundreds or a few thousand customers, a 4.5-4.8 rating, reviews that
     mention one concrete moment). Never the forbidden kinds (medical claims, "clinically proven", competitor names, licences,
     prices, offers).
   - Check every line against the ledger.
5. **Choose the look:** background role from the vibe (`colour-and-vibe.md`), never the same as the section above; whether this
   is a signature (loud) section; picture side per the wireframe; picture fit `adapt` so packs are never cropped; motion only as
   `motion-by-category.md` allows.
6. **Check the phone form:** picture first, short text, sideways lists show part of the next card, tap targets 44 px, nothing
   wider than the screen.
7. **CTA:** the page's single label; scroll to the buy box (several variants or bundles) or add to cart (one variant).
8. **Self-check** (write "ok" or the fix): answers its one question in 3 seconds? anything said elsewhere? every number has a
   source or SAMPLE mark? contrast passes? understandable on a phone without the desktop picture?

## Copy rules that keep pages from sounding generated
- No superlatives without proof ("best", "No. 1"), no exclamation marks, no ALL CAPS sentences (a short uppercase eyebrow or
  marquee is fine), no emoji in headings. Indian rules: ASCI on claims; FSSAI licence number on food and nutraceutical pages when
  the brand gives it.
- Accent words: at most 2 headlines per page with a highlighted word (1 for premium).
- Prices as the store shows them; "inclusive of all taxes" only when the store says so.
- Use the product's real name; propose a title in `product_todo` when the store's is a placeholder.

## `wireframe-plan.md` (write this before building)

```markdown
# Page plan: <brand> <product> (<date>), DTJ Standard Product Page v1
Vibe: <electric | fresh | calm | premium | playful | editorial | appetite | natural> (why, one line)
CTA label: "<label>"  Action: scroll-to-buy-box | add-to-cart
Signature section(s): <W..>
Store checks: title <ok | propose ...>, stock <ok | SOLD OUT>, pictures <n, which>, policies <found | missing>

## Claim ledger
| Claim | Source or SAMPLE | Home | Recap |

## Sections (every one, in order)
| # | Section | Block | Background | Headline | Items (count) | Samples in it | Ready? (block / builder gap) |

## Section notes (steps 1-8, one paragraph per section)
## Samples to replace before live (section, setting, sample value, what the real one should be)
## Theme / product / content to-dos
```
