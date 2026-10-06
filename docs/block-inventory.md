# Block inventory (5 Oct 2026) - what exists before Harsh's reference images

Source: file lists and PORTING.md notes on the four pack branches of `harsh-shopify-dev/dtj-master-theme`, plus the GOMINT mockups. **Nothing here has been opened in a browser or converted.** Sizes are lines added on the branch (a rough effort signal). "App block" means a theme app extension block in `services/block-library`.

**Status update 6 Oct 2026:** this inventory was written before the conversions. The app now has 7 blocks (Hero Points, Rotating Text, Social Proof Line, Testimonials, Shoppable Reels, Option Picker, Add-ons); the first-built Trust Row and six others were removed. The remaining pack items stay in the master theme (decision in `docs/HANDOFF.md` section 7; open item C). The 100 KB cap, 6-header limit, one picker per type and no child blocks are confirmed by Shopify's deploy checks.

Built so far in the library: see `services/block-library/README.md`.

## Hard limits of app blocks that shape every conversion
- An app block cannot contain child blocks. Lists (FAQ items, testimonials, bullet points) need either fixed numbered slots (like Trust Row's 4 items), or data from metafields/metaobjects written by the installer.
- Only a subset of setting types works; each existing block must be checked (font_picker is the known risk).
- No default copy and no hard-coded colours (library rules 2 and 4); the licence gate wraps all output (rule 3, 8).
- Placement: top level of a section that accepts `@app`; in-column placement is unproven.

## Food pack (`block/food-product-blocks`, Horizon theme blocks, product page)
| Existing | Lines | Depends on | Conversion note |
|---|---|---|---|
| dtj-food-usp-badges | 227 | none noted | Easy. Overlaps Trust Row: decide whether it is a second block or merged. |
| dtj-food-faq | 204 | metafield `custom.product_faqs` (metaobjects: question, answer) | Medium. List data: installer must create the metaobject definition and entries, or use fixed slots. |
| dtj-food-info-card | 277 | optional `custom.delivery_days` | Easy to medium. |
| dtj-food-rotating-text | 168 + JS 53 | none | Easy. Framework-free custom element. |
| dtj-food-testimonials | 393 + JS 87 | none | Medium. List data again. |
| dtj-food-shoppable-videos | 277 + JS 71 | video assets | Medium. Needs uploaded media. |
| dtj-food-social-proof | 197 | none (Judge.me injection and fake review count already removed) | Easy. Must never show an invented count. |
| dtj-food-fbt (bundle) | 346 + JS 143 | metafield `custom.bundle_products`; Horizon `CartLinesUpdateEvent` | **Hard.** Cart add logic is Horizon-specific; needs a `/cart/add.js` rewrite. |

## Beauty pack (`section/beauty-proeffex-pack`)
Blocks: hero-highlights (302), mua-badge (279), price-highlight (383), shade-picker (476), upsell (996), video-testimonials (593).
Sections: banner-slideshow (345), customer-stories (508), faq (521), guarantee (346), marquee (205), problem-solution (675), product-list (1494), sticky-atc (333), video-wall (692).
Note: no PORTING.md detail read. Largest: product-list and upsell (cart logic risk). Sections that are full-width bands can become app blocks inside an Apps wrapper section, but should be checked for size limits (Liquid across the extension is capped at 100 KB total, 30 blocks max).

## Supersenior / health pack (`section/supersenior-pack`)
| Existing | Lines | Conversion note |
|---|---|---|
| dtj-hero-promo | 3428 | **Hard.** Horizon-only constructs (content_for 'blocks', spacing/overlay snippets). Rewrite, do not port. |
| dtj-comparison-table | 667 | Self-contained. Medium. |
| dtj-root-cause / dtj-root-science | 481 / 854 | Self-contained; root-science uses font_picker. |
| dtj-science-stats | 1147 | Very large settings list; split before converting. |
| dtj-testimonials-slider | 2633 + JS 133 | Large; list data. |
| dtj-bullet-points, dtj-cost-comparison (blocks) | 415 / 575 | cost-comparison uses font_picker. |

## Supplements pack (`section/supplements-gomint-pack`)
hero-rotating (600), how-to-take (156), no-fuss (231), trust-marquee (134), whats-inside (256), whats-not-inside (149). All sections. Defaults carry one brand's copy (mints): must be emptied. The `how-to-take` schema was read: video/image pickers, richtext, several colours.

## GOMINT mockups (audit tool) and known gaps
Mockups exist for: rating row, trust badges, price offer, offer panel, add-on upsell, pincode checker, shop-by grid, testimonial, FAQ, accordions, sticky bar, WhatsApp, stock bar. Known missing (GOMINT HANDOFF): four-icon benefits, pack cards with "Most popular", trust row (now built).

## Suggested build order (to confirm once the images arrive)
1. Product-page essentials with simple data: USP badges, rating row, price/offer panel, sticky add-to-cart, WhatsApp button.
2. List-based blocks, after deciding the list-data approach: FAQ, testimonials, accordions, comparison table.
3. Heavy or cart-touching blocks last: bundle (FBT), upsell, hero promo, shade picker.

## Decisions needed before bulk conversion
- List data: fixed slots (simple, limited count) or metaobjects (flexible, needs extra scopes and an installer step)? Suggest fixed slots for the first version.
- Whether duplicates across packs (three FAQs, four testimonial variants) are merged into one neutral block per purpose.
- Which blocks must exist for the first full store build.
