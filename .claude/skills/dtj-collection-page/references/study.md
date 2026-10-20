# Collection page study (20 Oct 2026)

12 public collection pages opened in a clean headless Edge at 390 and 1280 px (`scripts/study_capture.py`; screenshots and raw numbers stay private in
`.work/collection-page-reference/`). 8 measured cleanly; Plum, Jones Road and Kylie gave no product cards to the reader (blocked or built
differently), The Whole Truth and KittySpout only on one width. The numbers below come from the metrics files, not from judgement.

Pages: blueland (https://www.blueland.com/collections/all), boat (https://www.boat-lifestyle.com/collections/true-wireless-earbuds), bombay-shaving (https://www.bombayshavingcompany.com/collections/all), gymreapers (https://gymreapers.com/collections/all), jones-road (https://www.jonesroadbeauty.com/collections/shop-all), kittyspout (https://www.kittyspout.com/collections/all), kylie (https://kyliecosmetics.com/collections/all), minimalist (https://beminimalist.co/collections/skin), plum (https://plumgoodness.com/collections/skin-care), proeffex (https://www.proeffex.com/collections/all), sugar (https://in.sugarcosmetics.com/collections/lips), whole-truth (https://thewholetruthfoods.com/collections/all)

| Brand | View | Cols | Gap px | First picture at px | H1 px | Banner | Collection links above | Controls | Rating on card | Swatches | Card button | Badge |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| blueland | phone | 2 | 16 | 413 | 24 |  | 14 | featured, filter, sort by | yes |  |  |  |
| blueland | desktop | 4 | 32 | 519 | 40 |  | 9 | featured | yes |  | QUICK ADD |  |
| boat | phone | 2 | 11 | 282 | 26 |  | 2 | - | yes | yes | ADD | yes |
| boat | desktop | 3 | 18 | 443 | 24 |  | 5 | featured, filter by, sort by  | yes | yes |  | yes |
| bombay-shaving | phone | 2 | 10 | 345 | 30 |  | 2 | filters, sort by | yes |  | Add to Cart |  |
| bombay-shaving | desktop | 4 | 15 | 473 | 40 |  | 2 | filters, sort by | yes |  | Add to Cart |  |
| gymreapers | desktop | 3 | 24 | 384 | 32 |  | 31 | featured, filters, sort by | yes | yes |  | yes |
| kittyspout | desktop | 4 | 20 | 1360 | 63 | yes | 3 | filters & fo | yes |  | ADD TO CART | yes |
| minimalist | phone | 2 | 16 | 379 | 34 |  | 0 | filter | yes |  | Add to cart | yes |
| minimalist | desktop | 3 | 26 | 375 | 50 |  | 0 | featured, sort by | yes |  | Add to cart | yes |
| proeffex | phone | 2 | 12 | 377 | - | yes | 0 | filter | yes | yes | Add to cart |  |
| proeffex | desktop | 4 | 16 | 533 | - | yes | 0 | availability, price, sort | yes | yes | Add to cart |  |
| sugar | phone | 2 | 10 | 336 | 20 | yes | 0 | filter, sort by | yes | yes | ADD TO CART | yes |
| sugar | desktop | 3 | 48 | 617 | 27 | yes | 29 | availability, sort by | yes | yes | ADD TO CART | yes |

First product picture, phone: 282-413 px (median 361); laptop: 375-1360 px (median 496; 375-617 without KittySpout, whose tall banner pushes its products to 1360).


## What every strong page does

- **Ratings on the card**: every measured page (8 of 8). Stars and the review count sit right above or below the title.
- **Sort**: every page has it; most have Filter too. Most print the product count ("17 items", "44 products").
- **Compact title**: the H1 is 24-50 px on a laptop (KittySpout 63) and 20-34 px on a phone; a description, when there is one, is one or two short lines.
- **First products in the first screen**: the first product picture starts well inside the first phone screen (844 px tall).
- **Grid**: 2 columns on every phone; 3 or 4 on a laptop; 10-16 px between phone cards.
- **Card**: picture, rating, title, price (with the offer when there is one), and an Add to cart button on most; shade swatches on the beauty pages.
- **Optional**: a slim promo banner (3 of 8), a row of collection links above the grid (4 of 8), a free-shipping strip.

## What this means for DTJ (the targets in `assemble_collection.COLLECTION_TARGETS`)

- First product picture at most 420 px down a 390 px phone and 620 px down a 1280 px laptop.
- 2 phone columns, 4 laptop columns (the Proeffex card was measured at 4 across a 1200 px page).
- Count and Sort above the grid; ratings only from real reviews; the title band compact on the brand's soft tint.
- Filters: NOT built yet (an open decision for Harsh: DTJ clients usually have small collections; filters matter above about 20 products).
