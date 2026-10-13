"""DTJ Best Sellers: collection tabs, tag badges, Judge.me ratings, variant swatches and the cart button."""
import json
import os
import re
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
os.environ["DTJ_APP_ROOT"] = str(HERE)
sys.path.insert(0, str(HERE.parent / "block-library" / "tests"))
import test_generated_blocks as tg  # noqa: E402

render = tg.render
MANIFEST = json.loads((HERE / "manifests" / "best-sellers.json").read_text(encoding="utf-8"))
ASSETS = HERE / "extensions" / "dtj-commerce" / "assets"
JM = "<div style='display:none' class='jdgm-prev-badge' data-average-rating='{avg}' data-number-of-reviews='{n}' data-number-of-questions='0'><span class='jdgm-prev-badge__stars'></span></div>"


def variant(vid, option1="Default Title", price=2500, compare=0, available=True, image=None):
    return {"id": vid, "price": price, "compare_at_price": compare, "available": available, "option1": option1,
            "featured_image": {"src": image, "width": 600, "height": 750} if image else None}


def product(pid=1, title="Tee", price=2500, compare=0, tags=(), variants=None, options=1, available=True, image="pic", images=1, judgeme="", standard=None):
    v = variants or [variant(pid * 10, price=price, compare=compare, available=available)]
    meta = {"judgeme": {"badge": judgeme}}
    if standard:
        meta["reviews"] = {"rating": {"value": {"rating": standard[0]}}, "rating_count": {"value": standard[1]}}
    return {"id": pid, "handle": title.lower().replace(" ", "-"), "title": title, "url": f"/products/{title.lower().replace(' ', '-')}", "price": price, "compare_at_price": compare,
            "featured_image": {"src": image, "width": 600, "height": 750} if image else None, "images": [{"src": f"{image}{i}", "width": 600, "height": 750} for i in range(images)],
            "tags": list(tags), "available": available, "has_only_default_variant": len(v) == 1, "variants": v, "options": ["Color", "Size"][:options],
            "selected_or_first_available_variant": v[0], "metafields": meta}


def coll(title, *products):
    return {"title": title, "url": f"/collections/{title.lower()}", "products": list(products)}


def only(**extra):
    base = {"heading": "", "collections": [], "badge_tags": ""}
    return {**base, **extra}


@unittest.skipIf(tg.Environment is None, "python-liquid not installed (use .work/.venv)")
class BestSellersTests(unittest.TestCase):
    m = MANIFEST

    def r(self, design_mode=False, **extra):
        return render(self.m, only(**extra), design_mode=design_mode)

    def one(self, p, **extra):
        return self.r(collections=[coll("A", p)], **extra)

    # ---- tabs and rows
    def test_nothing_renders_without_a_collection(self):
        self.assertEqual(render(self.m, {"collections": []}), "")
        html = self.one(product())
        for part in ("dtj-bs__heading", 'role="tablist"', "dtj-bs__badge", "dtj-bs__rating", "dtj-bs__swatches", "dtj-bs__heart", "dtj-bs__dots"):
            self.assertNotIn(part, html)

    def test_each_collection_is_a_tab_with_its_own_panel_and_only_the_first_is_visible(self):
        html = self.r(collections=[coll("One", product(1)), coll("Two", product(2)), coll("Three", product(3))])
        self.assertEqual(html.count('role="tab"'), 3)
        self.assertEqual(html.count('role="tabpanel"'), 3)
        self.assertEqual(html.count(" hidden>"), 2)
        self.assertEqual(html.count('aria-selected="true"'), 1)

    def test_one_collection_is_just_the_row_and_tab_names_can_be_overridden(self):
        html = self.one(product())
        self.assertNotIn('role="tablist"', html)
        self.assertIn("dtj-bs--one", html)
        named = self.r(collections=[coll("Shirts", product(1)), coll("Hoodies", product(2))], tab_2="Cosy")
        self.assertIn(">Shirts</button>", named)
        self.assertIn(">Cosy</button>", named)
        self.assertNotIn(">Hoodies</button>", named)

    def test_products_per_tab_is_a_limit(self):
        many = coll("A", *[product(i, f"P{i}") for i in range(1, 11)])
        self.assertEqual(self.r(collections=[many], products_per_tab=4).count('class="dtj-bs__card"'), 4)

    # ---- badges come from the product's own tags
    def test_the_badge_is_the_products_own_tag_in_its_own_words_and_the_first_wanted_tag_wins(self):
        html = self.one(product(tags=["Cotton", "Trending", "BestSeller"]), badge_tags="bestseller, trending")
        self.assertEqual(html.count('class="dtj-bs__badge"'), 1)
        self.assertIn(">BestSeller</span>", html)  # the list order decides, the product's capitalisation is shown
        self.assertNotIn(">Trending</span>", html)
        self.assertIn(">Trending</span>", self.one(product(tags=["Trending"]), badge_tags="bestseller, trending"))

    def test_no_wanted_tag_means_no_badge_and_the_list_tolerates_spaces_and_empty_items(self):
        self.assertNotIn("dtj-bs__badge", self.one(product(tags=["Cotton"]), badge_tags="bestseller"))
        self.assertNotIn("dtj-bs__badge", self.one(product(tags=["Cotton"]), badge_tags=""))
        self.assertIn(">New</span>", self.one(product(tags=["New"]), badge_tags=" , bestseller ,  new , "))

    def test_a_sale_badge_appears_only_without_a_tag_badge_and_only_on_a_reduced_product(self):
        sale = product(price=1500, compare=2500, tags=[])
        self.assertIn("dtj-bs__badge--sale", self.one(sale))
        self.assertNotIn("dtj-bs__badge--sale", self.one(sale, sale_badge=False))
        self.assertNotIn("dtj-bs__badge--sale", self.one(product(price=1500, compare=2500, tags=["Trending"]), badge_tags="trending"))
        self.assertNotIn("dtj-bs__badge--sale", self.one(product()))

    # ---- ratings
    def test_the_rating_is_read_from_the_judgeme_badge(self):
        html = self.one(product(judgeme=JM.format(avg="4.70", n=27)))
        self.assertIn('data-source="judgeme"', html)
        self.assertIn("<span>4.7</span>", html)
        self.assertIn("(27)", html)
        double = self.one(product(judgeme=JM.format(avg="4.00", n=4).replace("'", '"')))
        self.assertIn("<span>4.0</span>", double)
        self.assertIn("(4)", double)

    def test_zero_reviews_or_no_judgeme_shows_no_rating_to_shoppers(self):
        self.assertNotIn("dtj-bs__rating", self.one(product(judgeme=JM.format(avg="0.00", n=0))))
        self.assertNotIn("dtj-bs__rating", self.one(product()))
        # even with the sample-ratings setting on, the storefront never shows a made-up rating
        self.assertNotIn("dtj-bs__rating", self.one(product(), demo_ratings=True))
        self.assertNotIn("dtj-bs__rating", self.one(product(judgeme=JM.format(avg="0.00", n=0)), demo_ratings=True))

    def test_sample_ratings_exist_only_in_the_theme_editor_and_are_marked(self):
        shown = self.one(product(), design_mode=True, demo_ratings=True)
        self.assertIn("dtj-bs__rating--demo", shown)
        self.assertIn('data-source="demo"', shown)
        self.assertIn("shown only in the theme editor", shown)
        self.assertNotIn("dtj-bs__rating", self.one(product(), design_mode=True, demo_ratings=False))
        stable = re.findall(r"<span>(\d\.\d)</span>", self.one(product(pid=7), design_mode=True, demo_ratings=True))
        self.assertEqual(stable, re.findall(r"<span>(\d\.\d)</span>", self.one(product(pid=7), design_mode=True, demo_ratings=True)))  # not random: the same every render
        self.assertTrue(4.0 <= float(stable[0]) <= 4.9)

    def test_a_real_rating_is_never_replaced_by_a_sample_one_in_the_editor(self):
        html = self.one(product(judgeme=JM.format(avg="3.50", n=12)), design_mode=True, demo_ratings=True)
        self.assertIn('data-source="judgeme"', html)
        self.assertNotIn("dtj-bs__rating--demo", html)

    def test_the_standard_review_ratings_are_the_fallback_and_the_rating_can_be_switched_off(self):
        html = self.one(product(standard=(4.4, 31)))
        self.assertIn('data-source="standard"', html)
        self.assertIn("(31)", html)
        self.assertNotIn("dtj-bs__rating", self.one(product(judgeme=JM.format(avg="4.70", n=27)), show_rating=False))

    # ---- variants
    def test_a_product_with_variants_shows_one_swatch_per_value_of_the_first_option(self):
        p = product(variants=[variant(1, "Red", image="r1"), variant(2, "Red", image="r2"), variant(3, "Blue", image="b1"), variant(4, "Green", image="g1")])
        html = self.one(p)
        self.assertEqual(html.count('<button type="button" class="dtj-bs__sw'), 3)
        self.assertIn('role="radiogroup"', html)
        self.assertEqual(html.count('aria-checked="true"'), 1)
        self.assertEqual(html.count(' data-img="'), 3)  # a picture swatch carries the variant picture to swap in
        self.assertIn('data-price="Rs. 2500"', html)

    def test_a_variant_without_a_picture_is_a_word_chip_and_a_product_without_variants_shows_nothing(self):
        chips = self.one(product(variants=[variant(1, "S"), variant(2, "M")]))
        self.assertIn("dtj-bs__sw--text", chips)
        self.assertIn("<span>M</span>", chips)
        self.assertNotIn("data-img=", chips)
        self.assertNotIn("dtj-bs__swatches", self.one(product()))
        self.assertNotIn("dtj-bs__swatches", self.one(product(variants=[variant(1, "S"), variant(2, "M")]), swatches=False))

    def test_at_most_six_swatches(self):
        p = product(variants=[variant(i, f"C{i}", image=f"i{i}") for i in range(1, 10)])
        self.assertEqual(self.one(p).count('<button type="button" class="dtj-bs__sw'), 6)

    def test_a_reduced_variant_carries_its_old_price_only_when_asked(self):
        p = product(variants=[variant(1, "Red", price=1500, compare=2500, image="r"), variant(2, "Blue", price=1500, image="b")])
        self.assertIn('data-compare="Rs. 2500"', self.one(p, show_compare_price=True))
        self.assertIn('data-compare=""', self.one(p, show_compare_price=False))

    # ---- the cart button
    def test_a_one_variant_product_gets_a_cart_form_with_its_variant_id(self):
        html = self.one(product(pid=5))
        self.assertIn('<form class="dtj-bs__form" action="" method="post">', html)  # the address comes from the routes object (empty in the test engine)
        self.assertIn('name="id" value="50"', html)
        self.assertIn("Quick add", html)

    def test_a_product_with_two_options_opens_its_page_unless_told_to_add_the_first_variant(self):
        two = product(variants=[variant(1, "Red", image="r"), variant(2, "Blue", image="b")], options=2)
        page = self.one(two)
        self.assertNotIn("<form", page)
        self.assertIn('<a class="dtj-bs__add dtj-bs__add--page" href="/products/tee">', page)
        self.assertIn("Choose options", page)
        self.assertIn("<form", self.one(two, multi_option="first"))
        one_option = product(variants=[variant(1, "Red", image="r"), variant(2, "Blue", image="b")], options=1)
        self.assertIn("<form", self.one(one_option))  # a colour-only product adds in place

    def test_a_sold_out_product_cannot_be_added(self):
        html = self.one(product(available=False))
        self.assertNotIn("<form", html)
        self.assertIn("dtj-bs__add--off", html)
        self.assertIn("Sold out", html)

    def test_the_cart_button_modes(self):
        bar = self.one(product())
        self.assertIn("dtj-bs--add-bar", bar)
        self.assertIn('class="dtj-bs__amount"', bar)
        button = self.one(product(), quick_add="button")
        self.assertIn('class="dtj-bs__price"', button)
        self.assertNotIn('class="dtj-bs__amount"', button)
        none = self.one(product(), quick_add="none")
        self.assertNotIn("<form", none)
        self.assertIn('class="dtj-bs__price"', none)

    def test_the_button_words_have_fallbacks_and_can_be_changed(self):
        self.assertIn("Add To Cart", self.one(product(), add_label="Add To Cart"))
        self.assertIn("Quick add", self.one(product(), add_label=""))

    # ---- picture details
    def test_the_heart_and_the_picture_dots_are_options(self):
        self.assertIn('class="dtj-bs__heart"', self.one(product(), wishlist=True))
        gallery = self.one(product(images=5), gallery=True)
        self.assertEqual(gallery.count('class="dtj-bs__slide"'), 4)  # at most four pictures
        self.assertEqual(gallery.count("<i class=\"dtj-bs__dot"), 4)
        self.assertNotIn("dtj-bs__gallery", self.one(product(images=1), gallery=True))  # one picture: nothing to swipe
        self.assertNotIn("dtj-bs__gallery", self.one(product(images=5)))

    def test_pictures_are_sized_lazy_and_decorative_links_are_out_of_the_tab_order(self):
        html = self.r(collections=[coll("A", product(1), product(2, "B"))])
        for img in re.findall(r"<img [^>]*>", html):
            self.assertRegex(img, r'width="\d+" height="\d+"')
            self.assertIn('loading="lazy"', img)
        self.assertIn('class="dtj-bs__imglink" href="/products/tee" tabindex="-1" aria-hidden="true"', html)
        self.assertNotIn("<img", self.one(product(image=None)))

    def test_layout_choices_become_classes_and_sizes_and_text_is_escaped(self):
        html = self.r(collections=[coll("A", product(1)), coll("B", product(2))], tab_style="pill", arrows="circle", card_style="soft", visible_desktop=4.5, visible_mobile=2,
                      button_shape="rounded", heading_tag="script", heading="<u>H</u>")
        for part in ("dtj-bs--tabs-pill", "dtj-bs--arrows-circle", "dtj-bs--card-soft", "--bs-n: 4.5", "--bs-nm: 2", "dtj-bs--btn-rounded", "<h2"):
            self.assertIn(part, html)
        for bad in ("<u>H", "<script"):
            self.assertNotIn(bad, html)

    # ---- the script and the styles
    def test_the_script_is_small_polite_and_keeps_favourites_in_the_visitors_browser_only(self):
        js = (ASSETS / "dtj-best-sellers.js").read_text(encoding="utf-8")
        self.assertLess(len(js.encode("utf-8")), 10000)  # Shopify's limit for an app block script
        self.assertEqual(js.count("fetch("), 1)
        self.assertIn("/cart/add", js)
        self.assertIn("cartAdd", js)  # the address comes from the page (the routes object), with a fallback
        for banned in ("innerHTML", "setInterval", "document.write", "eval(", "XMLHttpRequest"):
            self.assertNotIn(banned, js)
        self.assertIn("passive: true", js)
        self.assertIn("form.submit()", js)
        self.assertIn("ArrowRight", js)
        self.assertIn("localStorage", js)
        self.assertIn("catch (error)", js)  # private mode must not break the card

    def test_the_css_is_a_native_scroll_row_and_the_picture_swap_is_a_fade(self):
        css = (ASSETS / "dtj-best-sellers.css").read_text(encoding="utf-8")
        self.assertIn("scroll-snap-type: x mandatory", css)
        self.assertIn("transition: opacity", css)
        self.assertRegex(css, r"(?m)^\.dtj-bs \{[^}]*width: 100%")

    def test_the_block_has_a_sane_number_of_settings_and_headers(self):
        interactive = [s for s in self.m["settings"] if s["type"] not in ("header", "paragraph")]
        headers = [s for s in self.m["settings"] if s["type"] in ("header", "paragraph")]
        self.assertLessEqual(len(interactive) + 8, 75)
        self.assertLessEqual(len(headers) + 1, 6)


if __name__ == "__main__":
    unittest.main()
