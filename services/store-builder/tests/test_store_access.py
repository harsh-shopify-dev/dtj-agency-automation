"""The collaborator login (no Theme Access password) and the draft copy of the live theme (theme_target, 21 Oct 2026), and the store
reader behind "send the brand's store link" (store_scan). Stand-ins play the Shopify CLI and the store's public pages: nothing here
reaches Shopify."""
import json
import subprocess
import unittest

from page_builder import store_scan
from page_builder import theme_target as tt
from provision.theme import ThemeError

STORE = "royal-dosa.myshopify.com"


class FakeThemes:
    """`shopify theme list|duplicate`: a live theme and whatever duplicate makes."""

    def __init__(self, refuse=None, copy_role="unpublished"):
        self.themes = [{"id": 101, "name": "Horizon", "role": "live"}, {"id": 102, "name": "Old test", "role": "unpublished"}]
        self.calls, self.refuse, self.copy_role = [], refuse, copy_role

    def __call__(self, cmd, env):
        self.calls.append((list(cmd), dict(env)))
        if self.refuse:
            return subprocess.CompletedProcess(cmd, 1, "", self.refuse)
        verb = cmd[2]
        if verb == "list":
            got = list(self.themes)
            for flag, field in (("--role", "role"), ("--name", "name")):
                if flag in cmd:
                    got = [t for t in got if t[field] == cmd[cmd.index(flag) + 1]]
            return subprocess.CompletedProcess(cmd, 0, json.dumps(got), "")
        if verb == "duplicate":
            name = cmd[cmd.index("--name") + 1]
            self.themes.append({"id": 200 + len(self.themes), "name": name, "role": self.copy_role})
            return subprocess.CompletedProcess(cmd, 0, "Theme duplicated", "")
        raise AssertionError(cmd)


class Login(unittest.TestCase):
    def test_no_password_means_the_cli_login_and_never_a_browser_prompt(self):
        fake = FakeThemes()
        access = tt.open_access(STORE, runner=fake, environ={}, registry=False)
        self.assertTrue(access.login)
        access.themes(role="live")
        env = fake.calls[0][1]
        self.assertNotIn("SHOPIFY_CLI_THEME_TOKEN", env)
        self.assertEqual(env["SHOPIFY_FLAG_NO_INPUT"], "1")
        self.assertIn("login=True", repr(access))

    def test_a_saved_password_is_still_used_first(self):
        fake = FakeThemes()
        access = tt.open_access(STORE, runner=fake, environ={"DTJ_THEME_ACCESS_ROYAL_DOSA": "shptka_x"}, registry=False)
        self.assertFalse(access.login)
        access.themes(role="live")
        self.assertEqual(fake.calls[0][1]["SHOPIFY_CLI_THEME_TOKEN"], "shptka_x")

    def test_a_login_without_access_says_what_to_do(self):
        access = tt.open_access(STORE, runner=FakeThemes(refuse="Error: You are not authorized to access this store (403)"),
                                environ={}, registry=False)
        with self.assertRaises(ThemeError) as stop:
            access.themes(role="live")
        text = str(stop.exception)
        for must in ("collaborator", f"shopify theme list --store {STORE}", "DTJ_THEME_ACCESS_ROYAL_DOSA"):
            self.assertIn(must, text)
        self.assertNotIn("[redacted]r", text)  # no empty-password replace mangling the text

    def test_the_draft_copy_is_the_live_theme_duplicated_unpublished(self):
        fake = FakeThemes()
        access = tt.open_access(STORE, runner=fake, environ={}, registry=False)
        made = access.duplicate_live("DTJ Draft 21 Oct 2026")
        self.assertEqual((made["role"], made["from_live"], made["from_live_name"]), ("unpublished", "101", "Horizon"))
        dup = next(c for c, _ in fake.calls if c[2] == "duplicate")
        self.assertEqual(dup[dup.index("--theme") + 1], "101")
        self.assertIn("--force", dup)
        for never in ("--publish", "--live", "--allow-live"):
            self.assertNotIn(never, dup)

    def test_the_draft_copy_refuses_a_taken_name_a_bad_name_and_a_copy_that_is_not_unpublished(self):
        fake = FakeThemes()
        access = tt.open_access(STORE, runner=fake, environ={}, registry=False)
        with self.assertRaises(ThemeError):
            access.duplicate_live("Old test")
        with self.assertRaises(ThemeError):
            access.duplicate_live("x; rm")
        self.assertFalse([c for c, _ in fake.calls if c[2] == "duplicate"])
        odd = tt.open_access(STORE, runner=FakeThemes(copy_role="live"), environ={}, registry=False)
        with self.assertRaises(ThemeError):
            odd.duplicate_live("DTJ Draft 21 Oct 2026")


def page(shop="royal-dosa.myshopify.com", theme='{"name":"Horizon","id":101,"schema_name":"Horizon","schema_version":"4.2.0","role":"main"}'):
    return (f'<html><head><title>Royal Dosa – Home</title><meta property="og:site_name" content="Royal Dosa">'
            f'<script>Shopify.shop = "{shop}";Shopify.theme = {theme};</script></head><body></body></html>')


def store(pages):
    def get(url):
        for key, body in pages.items():
            if url.startswith(key):
                return 200, url, body.encode() if isinstance(body, str) else body
        return 404, url, b""
    return get


PRODUCTS = {"products": [{"handle": "masala-dosa-mix", "title": "Masala Dosa Mix", "product_type": "Mix"},
                         {"handle": "idli-mix", "title": "Idli Mix", "product_type": "Mix"},
                         {"handle": "podi", "title": "Gunpowder Podi", "product_type": "Spice"}]}


class Scan(unittest.TestCase):
    def test_one_link_gives_the_original_address_the_theme_and_the_best_sellers(self):
        base = "https://royaldosa.com"
        got = store_scan.scan("royaldosa.com/collections/all?x=1", store({
            base + "/products.json": json.dumps(PRODUCTS),
            base + "/collections/all?sort_by=best-selling": '<a href="/products/podi?v=1">x</a><a href="/collections/all/products/idli-mix">'
                                                            '</a><a href="/products/podi">again</a>',
            base + "/collections.json": json.dumps({"collections": [{"handle": "all"}, {"handle": "mixes"}]}),
            base + "/": page(),
        }))
        self.assertEqual((got["myshopify_domain"], got["name"], got["product_count"], got["collection_count"]),
                         ("royal-dosa.myshopify.com", "Royal Dosa", 3, 2))
        self.assertEqual(got["live_theme"]["schema_name"], "Horizon")
        self.assertEqual([p["handle"] for p in got["best_sellers"]], ["podi", "idli-mix", "masala-dosa-mix"])
        self.assertIn("best-selling", got["best_sellers_from"])
        self.assertEqual(got["best_sellers"][0]["url"], base + "/products/podi")

    def test_without_a_best_selling_page_the_list_order_is_used_and_said(self):
        base = "https://royaldosa.com"
        got = store_scan.scan(base, store({base + "/products.json": json.dumps(PRODUCTS), base + "/": page()}))
        self.assertEqual([p["handle"] for p in got["best_sellers"]], ["masala-dosa-mix", "idli-mix", "podi"])
        self.assertIn("product list order", got["best_sellers_from"])

    def test_a_site_that_is_not_shopify_or_does_not_answer_is_refused_plainly(self):
        with self.assertRaises(store_scan.NotShopify):
            store_scan.scan("https://example.com", store({"https://example.com/": "<html>WordPress</html>"}))
        with self.assertRaises(store_scan.NotShopify):
            store_scan.scan("https://gone.example", store({}))
        with self.assertRaises(store_scan.NotShopify):
            store_scan.scan("not a link", store({}))

    def test_a_password_store_or_an_admin_link_is_read_by_dtjs_own_access(self):
        # every dev store sits behind its password page (22 Oct 2026, dtj-testing): the public page shows nothing to read
        seen = []
        private = lambda domain, link: seen.append((domain, link)) or {"myshopify_domain": domain}  # noqa: E731
        locked = store({"https://dtj-testing.myshopify.com/": '<form action="/password" method="post">Shopify</form>'})
        self.assertEqual(store_scan.scan("https://dtj-testing.myshopify.com/", locked, private)["myshopify_domain"], "dtj-testing.myshopify.com")
        never = lambda url: (_ for _ in ()).throw(AssertionError("an admin link is never fetched"))  # noqa: E731
        store_scan.scan("https://admin.shopify.com/store/dtj-testing", never, private)
        self.assertEqual([d for d, _ in seen], ["dtj-testing.myshopify.com", "dtj-testing.myshopify.com"])
        with self.assertRaises(store_scan.NotShopify) as no:  # a custom domain behind a password names no store
            store_scan.scan("https://brand.com", store({"https://brand.com/": '<form action="/password">shopify</form>'}), private)
        self.assertIn("<name>.myshopify.com", str(no.exception))
        with self.assertRaises(store_scan.NotShopify):  # without DTJ's access: refused with the public address to send
            store_scan.scan("https://admin.shopify.com/store/dtj-testing", never)

    def test_the_product_page_options_fit_the_store_size(self):
        self.assertEqual(store_scan.product_choices(1), [("The 1 product", "all:1"), ("I'll pick them", "pick")])
        self.assertEqual([v for _, v in store_scan.product_choices(4)], ["all:4", "top:3", "pick"])
        self.assertEqual([v for _, v in store_scan.product_choices(12)], ["all:12", "top:3", "top:5", "pick"])
        self.assertEqual([v for _, v in store_scan.product_choices(246)], ["top:3", "top:5", "top:10", "pick"])
        self.assertEqual(store_scan.product_choices(0), [("No product pages", "none")])


if __name__ == "__main__":
    unittest.main()
