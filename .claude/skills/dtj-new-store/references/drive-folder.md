# The Google Drive folder for a new store

A new store's products come from one Google Drive folder (Harsh, 22 Oct 2026). The store job reads it with no login
(`services/store-builder/provision/drive_assets.py`), so the folder must be shared:
**right-click the folder > Share > General access: "Anyone with the link", Viewer**. Then send its link to the bot when it asks.

## The layout
```
<Brand name>/
  1 Brand/
      logo.png             the main logo (png, jpg, svg or webp; the file name has "logo" in it)
      logo-white.png       optional: the logo for dark backgrounds ("white" or "light" in the name)
      Brand details        a Google Doc (or .txt)
  2 Products/
      <Product name>/      one folder per product; the folder name is the product's name in the store
          Details          a Google Doc (or .txt)
          1.jpg, 2.jpg ... the pictures in the order to show; 1 = the main picture (jpg, png, webp; up to 10)
          video.mp4        optional: listed, not added to the store
  3 Banners/               optional: wide pictures for the home page; empty = ChatGPT makes them
  4 Policies/              optional: Google Docs named Refund, Shipping, Privacy, Terms; missing = left empty for the client
```
Names are matched loosely: any case, the number in front is optional ("Products" works too).

## "Details" (one per product)
One field per line, `Name: value`. Only Price and Description matter most; everything else is optional.
```
Price: 499
Compare at price: 699
Sizes: 250 g = 499, 500 g = 899
Collection: Snacks, Best sellers
SKU: SN-250
Description:
Everything after this line is the product's description, as many lines as needed.
```
- Prices may be written as `Rs. 1,299/-` or `₹ 250`; MRP works for "Compare at price".
- Sizes with one price for all: `Size = S, M, L` (and one `Price:` line). Also Colour, Flavour, Pack.
- **No price = the product goes in ACTIVE at 0.00 with the tag `dtj-price-needed`.** Nobody guesses a price: the bot asks
  for the missing ones before adding the products ("name = price", one per line), or they are set later in Shopify.

## "Brand details"
```
Name: Senso Foods
Tagline: Fresh tea, every cup
Colours: #1F3A2D, #F2E8D5, #C8102E
Fonts: Playfair Display, Inter
About: Two lines about the brand, in the founder's words.
Email: hello@brand.com
Phone: +91 98765 43210
Address: Shop 4, Main Road, Rajkot
Instagram: https://instagram.com/brand
```
The header, footer and pages use these as they are. Nothing missing is made up: a missing logo shows the store name, missing
colours get a DTJ proposal the client confirms.

## What the bot says back
Right after the link it lists what it found ("12 products, 3 collections, 2 banners") and every problem: a product with no
pictures, no Details doc, a price that is not a number, a picture over 20 MB or in another format (heic). Fix the folder and send
the link again, or go on: nothing is added to the store before the Approve tap.
