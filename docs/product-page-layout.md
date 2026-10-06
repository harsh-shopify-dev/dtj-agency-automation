# Product page layout: reference image mapped to blocks (5 Oct 2026)

**Status 6 Oct 2026: partly stale.** The blocks it names for offer pill, callout, urgency, bullets, highlighted text, secure checkout and Trust Row were removed from the app. Current app blocks: Hero Points, Rotating Text, Social Proof Line, Testimonials, Shoppable Reels, Option Picker, Add-ons (`docs/HANDOFF.md` section 8). The `@app` placement inside the product column is still unproven.

Reference: Harsh's screenshot of a "buy box" (rating, title, highlighted description, offer pill, price, callout, bullets, variant pills, urgency line, add to cart, shipping/guarantee line, payment icons, "trusted by" line). Design reference only: write original copy, never copy its text, never invent numbers (reviews count, "6,000+", prices, guarantees).

Verified in the master theme (Horizon 4.2.0, commit 5acd1b6): the product details column (`blocks/_product-details.liquid`) accepts `@theme` AND `@app` blocks, so our app blocks can sit between native blocks in the column. **Still to prove in the editor** (Details > Add block > Apps).

| # | In the reference | Use | Notes |
|---|---|---|---|
| 1 | Star rating + "12 Reviews" | NATIVE `review` (6 settings: stars_style, show_number, text_color, type_preset, width, alignment) | Reads `product.metafields.reviews.rating` and `reviews.rating_count` (written by a review app). With no review data nothing real shows; in the editor it previews 4 stars / 3 reviews. We never fabricate ratings. |
| 2 | Title | NATIVE `product-title` (18 settings) | As is. |
| 3 | Short description with a highlighted phrase | NATIVE `text` (richtext + 18 style settings) | Richtext gives bold/italic/links, not a colour highlight. Coloured highlight would need a small custom block (option). |
| 4 | Dark pill with a small round image and text | NEW app block (offer A) | Text + optional image + colours. |
| 5 | Price, compare-at price, "-22%" badge | NATIVE `price` (16 settings: show_sale_price_first, installments, tax info, type preset...) | Check in preview whether the native sale badge looks like "-22%"; if not, add a savings-percent option in a new block. |
| 6 | Green label "One jar replaces three" | NEW app block (offer B) | Callout tag, optional pointer. |
| 7 | Bullet points with icons | NEW app block (bullets). Source to adapt: `dtj-bullet-points` (supersenior pack) | Fixed slots (suggest 6), icon + text each. |
| 8 | Variant pills (Complex - Daily) | NATIVE `variant-picker` (16 settings) | As is. |
| 9 | Amber dot + "Restock batches sell out in under a week" | NEW app block (offer C, urgency line) | Text must be brand-supplied and true; never an invented scarcity claim. Native `product-inventory` shows real stock counts: possible alternative. |
| 10 | Add to cart | NATIVE `buy-buttons` (22 settings) | As is. |
| 11 | Shipping and guarantee line + payment icons | NEW app block: Secure Checkout | Text line(s) from brand facts + payment icons. Native `payment-icons` already prints the store's real enabled payment methods (`shop.enabled_payment_types`); the new block reuses that approach so it never shows a method the store does not accept. |
| 12 | "Trusted by 6,000+ daily takers" + 5 stars | Optional row inside Secure Checkout | Brand-supplied text only. |
| 13 | Shoppable reels | NEW app block. Source to adapt: `dtj-food-shoppable-videos` + `assets/dtj-food-reels.js` (food pack) | Needs uploaded videos and product links. |
| 14 | Testimonial slider | NEW app block. Sources: `dtj-testimonials-slider` (supersenior), `dtj-food-testimonials` (food) | Fixed slots (suggest 6), neutral defaults. |

## "Full settings"
- Native blocks already ship with their full Horizon settings.
- Every new app block gets the same standard controls as the native ones: alignment, text and background colours, font size, corner radius, padding on all four sides, plus its own content slots. Defined once in the library and added by the block builder, so no block is missing them.
- Library rules still apply: no default copy, no hard-coded colours, licence-gated, tests, Theme Check.

## To build, in this order
1. Block builder: manifest + shared standard controls -> generated `{% schema %}`.
2. Offer A, Offer B, Offer C, Bullets, Secure Checkout (product page essentials).
3. Testimonial slider, Shoppable reels (list data and media).
4. Product template recipe: native blocks + app blocks in the order above, applied with `add_app_block` (new: insert inside `_product-details`, not only at section level).
