"""The store job: a whole store from the one link a person sends the DTJ bot (Harsh, 21 Oct 2026: "i just share the brand store link
and it starts designing the store and it asks the specific questions it needs along with the app installation"). The laptop side of
n8n's "Store Factory: New Store"; the runbook is the skill dtj-new-store.

    python n8n/store-factory/store_job.py start --link https://store.myshopify.com --chat <telegram id> --by "<name>"
        read the store and ask the questions in Telegram (redesign or new store; where the products come from: this store, the
        brand's current website, a Google Drive folder or sample products; whose store, the client's name, what to design, which
        products, an offer)
    python n8n/store-factory/store_job.py assets --job <job> --file <assets.json>
                                                                   a new store: the sample products the session wrote and their
                                                                   pictures, and the home page banners, made with ChatGPT
    python n8n/store-factory/store_job.py draft --job <job>       Approve tap, then the live theme duplicated as an UNPUBLISHED copy
    python n8n/store-factory/store_job.py copy --job <job>        the products (from the brand's website, the Drive folder or the
                                                                   samples; every one ACTIVE), collections and empty policy pages: a
                                                                   prices question when some have none, a read-only plan kept on the
                                                                   install service, an Approve tap (it starts n8n's Store Factory:
                                                                   Brand Copy, which does the writes), then it waits
    python n8n/store-factory/store_job.py pages --job <job> --file <pages.json>   About, Contact, FAQ (new pages only), its own tap
    python n8n/store-factory/store_job.py menus --job <job>       the main menu and the footer, one tap
    python n8n/store-factory/store_job.py activate --job <job> --approved-by "<name> (<where>)"
                                                                   products an earlier copy left as drafts, switched to ACTIVE
    python n8n/store-factory/store_job.py apps --job <job>        Approve tap for the app copies; prints the add_shop.py command
    python n8n/store-factory/store_job.py installs --job <job>    DTJ's own store: 7 Install buttons, then each app switched on
    python n8n/store-factory/store_job.py approve --job <job> --key <key> --text "<what will be written>"   one write's Approve tap
    python n8n/store-factory/store_job.py step --job <job> <stage> [--done N --total M]                      the progress bar
    python n8n/store-factory/store_job.py record --job <job> --part <part> --preview <url> [--code C] [--note N]   a page written
    python n8n/store-factory/store_job.py finish --job <job> --status "done" | "partly done" | "could not start" [--note N]
    python n8n/store-factory/store_job.py status --job <job>

Exit codes: 0 done, 1 stopped (why is printed), 3 waiting for a person (run the same command again: it keeps what was answered and
never asks twice), 4 the person tapped Skip. State: .work/stores/<job>/job.json (no secret in it). Every Approve tap is the yes of
the person who tapped, for that one action, and is written to the job's action log with their name.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import html
import json
import os
import re
import sys
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "services" / "store-builder"))
from bot_ask import TABLE, Asker  # noqa: E402

STATE_DIR = ROOT / ".work" / "stores"
CATCHER = "https://dtj-install-catcher.ultimateecomwithharsh.workers.dev"  # the install service: POST /copy (src/copy.js)
WAITING, SKIPPED = 3, 4
QUESTION_MINUTES = 60   # each question waits this long, then the job says "waiting" (exit 3) and a rerun keeps waiting
APPROVE_MINUTES = 120
PARTS = {"chrome": "Header and footer", "home": "Home page", "collection": "Collection page", "products": "Product pages",
         "pages": "About, Contact and FAQ pages and the menus"}
SOURCES = {"self": "the products already in this store", "site": "the brand's current website", "drive": "a Google Drive folder",
           "samples": "sample products"}
DRIVE_HOW = ("Send the Google Drive folder link. Share the folder first: Share > General access > Anyone with the link > Viewer.\n"
             "Inside it: <b>1 Brand</b> (logo + a \"Brand details\" doc), <b>2 Products</b> (one folder per product, named as the "
             "product: a \"Details\" doc with Price, Sizes, Collection, Description + pictures 1.jpg, 2.jpg ...), <b>3 Banners</b> "
             "(optional) and <b>4 Policies</b> (optional).")
SAMPLE_COUNTS = (3, 6, 9, 12)
SAMPLE_TAG, SAMPLE_PRICE_TAG, SAMPLE_TEXT_TAG = "dtj-sample", "dtj-sample-price", "dtj-sample-text"
# which pictures ChatGPT may make, per source (Harsh, 22 Oct 2026: "the telegram must ask for the follow up if the assets are needed
# to generate or not"); products already in a store or copied from a website keep their own pictures, banners can always be made
PICTURE_CHOICES = {
    "samples": [("Product pictures and banners", "all"), ("Only product pictures", "products")],
    "drive": [("Banners and extra product pictures", "all"), ("Only banners", "banners"), ("No: the folder's pictures are enough", "none")],
    "site": [("Only banners", "banners"), ("No new pictures", "none")],
    "self": [("Only banners", "banners"), ("No new pictures", "none")],
}
MIN_COMPETITORS = 3  # pictures are made only after at least 3 of the niche's D2C brands were read (Harsh asked for the top 5)
PRICE_LINE = re.compile(r"^(.+?)\s*[=:\-\u2013]\s*(?:rs\.?|inr|\u20b9|\$)?\s*(\d{1,9}(?:\.\d{1,2})?)\s*$", re.I)
CLAIM_WORDS = re.compile(r"\b(clinically|certified|certificate|cure[sd]?|guarantee[d]?|doctor|dermatologist|award|no\.?\s*1|number one|"
                         r"best[- ]selling|bestseller|proven|fda|iso|organic certified|\d+\s*%|reviews?|rated|stars?)\b", re.I)
FULL, PRODUCTS_ONLY = ("chrome", "home", "collection", "products", "pages"), ("products",)
FOOTER_POLICIES = (("Refund policy", "refund-policy"), ("Shipping policy", "shipping-policy"), ("Privacy policy", "privacy-policy"),
                   ("Terms of service", "terms-of-service"))
STORE_STAGES = {
    "questions": ("Your answers", 0, 8),
    "draft": ("The draft copy of the theme", 8, 12),
    "assets": ("Sample products and pictures (ChatGPT)", 12, 18),
    "copy": ("Adding the products and collections", 18, 25),
    "apps": ("The DTJ apps: made, released, installed", 25, 38),
    "intake": ("Collecting the brand's pictures and details", 38, 45),
    "chrome": ("Header and footer", 45, 53),
    "home": ("Home page", 53, 63),
    "collection": ("Collection page", 63, 70),
    "products": ("Product pages", 70, 94),
    "pages": ("About, Contact, FAQ and the menus", 94, 98),
}
STORE_UNITS = {"products": "page"}
STATUSES = ("done", "partly done", "could not start")


def esc(s) -> str:
    return html.escape(str(s if s is not None else ""), quote=False)


def job_id(domain: str) -> str:
    handle = domain.split(".")[0]
    return handle if len(handle) <= 24 else handle[:18] + "-" + hashlib.sha1(handle.encode()).hexdigest()[:5]


def theme_support(schema: str | None) -> str:
    """horizon: every part; dawn: product pages only (assemble.py knows Dawn); none: Horizon must be added first."""
    return {"horizon": "horizon", "dawn": "dawn"}.get(str(schema or "").strip().lower(), "none")


def match_products(lines: list[str], sellers: list[dict]) -> tuple[list[dict], list[str], list[str]]:
    """Typed product links or names -> (the store's products, lines left out with why, notes on what was chosen). A link counts by its
    handle; a name that is exactly a product's title wins over names that only contain the words (21 Oct 2026, first live run:
    "TOILOVA" on a store that also has three "TOILOVA (Copy)" products); several products with that exact title: the best seller
    (`sellers` is in the store's best-selling order), and the note says which."""
    norm = lambda s: re.sub(r"\s+", " ", str(s)).strip().lower()  # noqa: E731
    picked, left, notes = [], [], []
    for line in (ln.strip() for ln in lines):
        if not line:
            continue
        m = re.search(r"/products/([a-z0-9][a-z0-9-]*)", line, re.I)
        hit = None
        if m:
            hit = next((p for p in sellers if p["handle"] == m.group(1).lower()), None)
            if not hit:
                left.append(f"{line[:80]}: not a product of this store")
        else:
            exact = [p for p in sellers if norm(p["title"]) == norm(line)]
            words = [w for w in re.findall(r"[a-z0-9]+", line.lower()) if len(w) > 1]
            loose = [p for p in sellers if words and all(w in p["title"].lower() for w in words)]
            if exact:
                hit = exact[0]
                if len(exact) > 1:
                    notes.append(f"{len(exact)} products are called \"{hit['title']}\": took the best seller, {hit['url']}")
            elif len(loose) == 1:
                hit = loose[0]
            elif loose:
                left.append(f"{line[:80]}: matches {len(loose)} products ({', '.join(p['title'] for p in loose[:4])}): send its link")
            else:
                left.append(f"{line[:80]}: not found in the store")
        if hit and hit not in picked:
            picked.append(hit)
    return picked, left, notes


class Job:
    def __init__(self, job: str, *, send: Callable[[str, dict], dict], rows: Callable[[str], list], progress=None, access=None,
                 log=None, state_dir: Path = STATE_DIR, out=print, sleep=time.sleep, clock=time.monotonic,
                 today: Callable[[], str] = lambda: datetime.now(timezone.utc).strftime("%d %b %Y"), scanner=None, planner=None,
                 copy_status=None, add_row=None, licence=None, org_apps=None, drive=None, picture=None, catcher=None):
        self.licence, self.org_apps, self.catcher = licence or _licence, org_apps or _org_apps, catcher or _catcher
        self.drive, self.picture = drive or _drive, picture or _picture
        self.scanner, self.planner, self.copy_status = scanner or _scan_brand, planner or _copy_plan, copy_status or _copy_status
        self.job, self.dir = job, state_dir / job
        self.path = self.dir / "job.json"
        self.s = json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else {}
        self.out, self.progress, self.access, self.log, self.today = out, progress, access, log, today
        self.ask = Asker(job, self.s.get("chat", ""), send=send, rows=rows, state=self.s, save=self.save, sleep=sleep, clock=clock,
                         add_row=add_row)

    def save(self) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.s, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    def bar(self, stage: str, done: int = 0, total: int = 0) -> None:
        if self.progress:
            self.progress.step(stage, done, total)

    def logged(self, action: str, reason: str, by: str, result: str = "success", **extra) -> None:
        """One action-log row (schemas/action.schema.json): results are success / failed / blocked (a Skip tap is "blocked": the
        action did not happen because the person said no), the tapper goes in approved_by."""
        if self.log:
            self.log.record(tier=2, mode="approve", target=self.s.get("shop", self.job), action=action, reason=reason, result=result,
                            approved_by=by, approved_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), **extra)

    # ---- start: the store, then the questions
    def begin(self, scan: dict, chat: str, by: str) -> None:
        if not self.s.get("shop"):  # a new job (the Asker has already added its empty "asked" / "answers")
            self.s.update({"job": self.job, "link": scan["link"], "shop": scan["myshopify_domain"], "name": scan["name"],
                           "chat": str(chat or ""), "requested_by": by, "scan": scan, "plan": {}, "written": []})
            self.ask.chat = self.s["chat"]
            self.save()

    def plan(self, minutes: float = QUESTION_MINUTES) -> int:
        s, a, sc = self.s, self.ask, self.s["scan"]
        p = s["plan"]
        self.bar("questions", 0, 5)
        theme = sc.get("live_theme") or {}
        intro = (f"<b>{esc(sc['name'])}</b> ({esc(sc['myshopify_domain'])})\n{sc['product_count']}{'+' if sc.get('more_products') else ''} "
                 f"products, {sc['collection_count']} collections, live theme {esc(theme.get('name') or '?')} "
                 f"({esc(theme.get('schema_name') or 'unknown')}).")
        # the link sent is the store to build in (21 Oct 2026). The first question (Harsh, 22 Oct 2026: "it starts and asks if it
        # is a redesign or new store development"): a redesign keeps the brand's own products (already in this store, or scraped from
        # the website it moves from); a new store gets them from a Google Drive folder, or as samples with ChatGPT pictures
        got = a.choose("kind", intro + "\n\nWhat are we building in this store?",
                       [("Redesign an existing brand", "redesign"), ("New store from scratch", "new"), ("Wrong store: stop", "stop")],
                       minutes)
        if not got:
            return WAITING
        if got["value"] == "stop":
            return self.stop("the person said it is the wrong store")
        p["kind"] = got["value"]
        if p["kind"] == "new":
            stopped = self.new_store_source(minutes)
            if stopped is not None:
                return stopped
            got = {"value": "new"}
        else:
            got = a.choose("brand_src", "Where are the brand's products now?",
                           [("Already in this store", "self"), ("On its current website", "send")], minutes)
            if not got:
                return WAITING
            p["source"] = "site" if got["value"] == "send" else "self"
        if got["value"] == "send" and not s.get("brand"):
            link = a.type_in("brand_link", "Send the brand's current website link (Shopify, WordPress, Wix or any other), for example "
                                           "https://brand.com. I copy its products, pictures, prices, collections and policy pages.",
                             minutes, "https://brand.com")
            if not link:
                return WAITING
            try:
                s["brand"] = self.scanner(link["value"])
            except Exception as exc:  # noqa: BLE001 - a link that cannot be read is asked for again, with why (22 Oct 2026)
                if a.forget("brand_link") >= 3:  # three links in a row could not be read: stop and say so (CLAUDE.md self-healing)
                    return self.stop(f"three brand links in a row could not be read (last: {str(exc)[:160]})")
                a.tell(f"I could not read {esc(link['value'])} as a brand: {esc(str(exc)[:200])}. Send another link: the brand's own website.")
                return self.plan(minutes)
            self.save()
            br = s["brand"]
            website = br.get("platform") == "website"
            a.tell(f"Brand: <b>{esc(br['name'])}</b> ({esc(br['base'])}): {br['product_count']} products"
                   + (f", {br['collection_count']} collections" if not website else "") + ". "
                   + ("Its website is not a Shopify store" + (" and shows no price for some products: they go in at 0.00 (never "
                      "guessed) unless you send prices when I ask. " if br.get("prices", 0) < br["product_count"] else ". ") if website else "")
                   + f"Nothing is copied into {esc(sc['name'])} before your Approve tap.")
        elif got["value"] == "self":
            s["brand"] = sc
        br = s["brand"]
        p["brand"] = {"link": br["base"], "name": br["name"], "store": br.get("myshopify_domain"), "currency": br.get("currency"),
                      "product_count": br["product_count"]}
        p["copy"] = p["source"] != "self" and br.get("myshopify_domain") != sc["myshopify_domain"]
        got = a.choose("pictures", "Should ChatGPT make new pictures for this store? First I study 5 D2C brands of this niche that grow "
                                   "on Meta ads (never the big names), then make ours from your own product photos.",
                       PICTURE_CHOICES[p["source"]], minutes)
        if not got:
            return WAITING
        p["pictures"] = got["value"]
        got = a.choose("whose", f"Whose store is <b>{esc(sc['name'])}</b> ({esc(sc['myshopify_domain'])})?",
                       [("A client's store", "client"), ("DTJ's own store", "dtj")], minutes)
        if not got:
            return WAITING
        p["whose"] = got["value"]
        if p["whose"] == "client":
            got = a.choose("label", f"The client's name for the app names: <b>{esc(br['name'])}</b>?",
                           [(f"Use \"{br['name'][:40]}\"", "use"), ("I'll type it", "type")], minutes)
            if not got:
                return WAITING
            if got["value"] == "type":
                got = a.type_in("label_typed", "Send the client's name, as it should appear in the app names.", minutes, "Royal Dosa")
                if not got:
                    return WAITING
                p["label"] = re.sub(r"\s+", " ", got["value"]).strip()[:40]
            else:
                p["label"] = br["name"][:40]
        self.bar("questions", 1, 5)
        support = theme_support(theme.get("schema_name"))
        if support == "dawn":
            got = a.choose("theme", f"The store runs Dawn. DTJ designs product pages on Dawn; the header, footer, home and collection pages "
                                    "need Horizon (Shopify's free theme).",
                           [("Product pages only, on Dawn", "dawn"), ("I'll add Horizon first", "horizon"), ("Stop", "stop")], minutes)
        elif support == "none":
            got = a.choose("theme", f"The store runs {esc(theme.get('schema_name') or 'a theme the builder does not know')}. DTJ's builder "
                                    "designs on Horizon (Shopify's free theme). In the store admin: Online Store > Themes > Add theme > "
                                    "Horizon (do NOT publish it). Then tap Done; the live store stays as it is.",
                           [("Done: Horizon is added", "horizon"), ("Stop", "stop")], minutes)
        else:
            got = {"value": "duplicate"}
        if not got:
            return WAITING
        if got["value"] == "stop":
            return self.stop("the store's theme is not one the builder designs on, and the person stopped")
        p["theme"] = got["value"]  # duplicate (a copy of the live Horizon), dawn (a copy of the live Dawn), horizon (the added one)
        if p["theme"] == "horizon" and support == "dawn":
            a.tell("OK. In the store admin: Online Store > Themes > Add theme > Horizon (do NOT publish it). I find it when I make the draft.")
        self.bar("questions", 2, 5)
        if p["theme"] == "dawn":
            p["parts"] = list(PRODUCTS_ONLY)
        else:
            got = a.choose("parts", "What should I design? Everything goes into a draft copy: the live store does not change.",
                           [("Everything", "all"), ("Only product pages", "products"), ("Everything except product pages", "pages"),
                            ("Choose one by one", "each")], minutes)
            if not got:
                return WAITING
            if got["value"] == "each":
                parts = []
                for key, label in PARTS.items():
                    one = a.choose(f"part_{key}", f"{label}?", [("Yes", "yes"), ("No", "no")], minutes)
                    if not one:
                        return WAITING
                    if one["value"] == "yes":
                        parts.append(key)
            else:
                parts = {"all": list(FULL), "products": list(PRODUCTS_ONLY), "pages": [x for x in FULL if x != "products"]}[got["value"]]
            if not parts:
                return self.stop("nothing was chosen to design")
            p["parts"] = parts
        self.bar("questions", 3, 5)
        if "products" in p["parts"] and p["source"] == "samples":
            n = br["product_count"]
            got = a.choose("products", "Which product pages? The sample products are made right after these questions.",
                           [(f"All {n} samples", f"top:{n}")] + [(f"The first {k}", f"top:{k}") for k in (3, 6) if k < n]
                           + [("No product pages", "none")], minutes)
            if not got:
                return WAITING
            p["product_pages"] = 0 if got["value"] == "none" else int(got["value"].split(":")[1])
            p["products"] = []  # named once the samples are made (store_job.py assets)
        elif "products" in p["parts"]:
            from page_builder.store_scan import product_choices  # noqa: PLC0415
            sellers = br["best_sellers"]  # the brand's products (copied with the same handles)
            top = "\n".join(f"{i}. {esc(x['title'])}" for i, x in enumerate(sellers[:5], 1))
            got = a.choose("products", f"Which product pages? Best sellers first ({esc(br['best_sellers_from'])}):\n{top}",
                           [(lbl, v) for lbl, v in product_choices(len(sellers))], minutes)
            if not got:
                return WAITING
            if got["value"] == "pick":
                got = a.type_in("products_typed", "Send the product links (from the store's website) or exact names, one per line.",
                                minutes, "https://brand.com/products/...")
                if not got:
                    return WAITING
                picked, left, notes = match_products(got["value"].splitlines(), sellers)
                if notes:
                    a.tell("Picked: " + "\n".join(esc(n) for n in notes))
                if left:
                    a.tell("Left out:\n" + "\n".join(esc(x) for x in left))
                if not picked:
                    return self.stop("none of the products sent was found in the store")
            elif got["value"] == "none":
                picked = []
            else:
                n = int(got["value"].split(":")[1])
                picked = sellers[:n]
            p["products"] = [{"handle": x["handle"], "title": x["title"], "url": x["url"]} for x in picked]
        self.bar("questions", 4, 5)
        got = a.choose("offer", "Is there an offer the pages may show? I never make one up.",
                       [("No offer", "none"), ("I'll type it", "type")], minutes)
        if not got:
            return WAITING
        if got["value"] == "type":
            got = a.type_in("offer_text", "Send the offer's exact words as the store runs it now. The pages show it word for word.",
                            minutes, "Flat 10% off on prepaid orders")
            if not got:
                return WAITING
            p["offer"] = got["value"][:300]
        else:
            p["offer"] = ""
        p["asked_by"] = sorted({v["by"] for v in s["answers"].values()})
        self.bar("questions", 5, 5)
        s["planned"] = True
        s.pop("stopped", None)
        self.save()
        products = "; ".join(x["title"] for x in p.get("products", [])) or (
            f"the first {p['product_pages']} samples" if p.get("product_pages") else "none")
        copying = {"site": f"Copy <b>{esc(br['name'])}</b> into it, then design: ",
                   "drive": f"Add <b>{esc(br['name'])}</b>'s products from the Drive folder, then design: ",
                   "samples": f"Make {br['product_count']} sample products for <b>{esc(br['name'])}</b> with ChatGPT pictures, then "
                              "design: "}.get(p["source"], "") if p["copy"] else ""
        a.tell(f"Plan for <b>{esc(s['name'])}</b>: {copying}{esc(', '.join(PARTS[x] for x in p['parts']))}. Product pages: "
               f"{esc(products)}. Offer: {esc(p['offer'] or 'none')}.\nBefore anything is made or written I send an Approve button: "
               "the draft copy, " + ("the products (every one ACTIVE), " if p["copy"] else "") + "the app copies, the header and "
               "footer, the collection page. Product and home pages go to the draft without one (Harsh's standing rule). Nothing is "
               "published.")
        self.out(json.dumps({"job": self.job, "plan": p}, ensure_ascii=False))
        return 0

    def new_store_source(self, minutes: float) -> int | None:
        """A new store's products: a Google Drive folder (read now, so a folder that is not shared is said at once) or sample
        products (the brand's name, what it sells, how many). None = answered, else the exit code (waiting / stopped)."""
        s, a, p = self.s, self.ask, self.s["plan"]
        got = a.choose("ready", "Are the brand's products ready?",
                       [("Yes: I'll send a Google Drive folder", "drive"), ("No: make sample products", "samples")], minutes)
        if not got:
            return WAITING
        p["source"] = got["value"]
        if s.get("brand"):
            return None
        if p["source"] == "drive":
            link = a.type_in("drive_link", DRIVE_HOW, minutes, "https://drive.google.com/drive/folders/...")
            if not link:
                return WAITING
            try:
                s["brand"] = self.drive(link["value"], self.dir / "drive")
            except Exception as exc:  # noqa: BLE001 - a folder that is not shared or not in the layout: said, then asked again
                if a.forget("drive_link") >= 3:
                    return self.stop(f"three Drive links in a row could not be read (last: {str(exc)[:160]})")
                a.tell(f"I could not read that folder: {esc(str(exc)[:300])}. Send the link again once that is fixed.")
                return self.new_store_source(minutes)
            self.save()
            br = s["brand"]
            unpriced = sum(1 for x in br["products"] if x.get("price_needed"))
            a.tell(f"Drive folder: <b>{esc(br['name'])}</b>: {br['product_count']} products, {br.get('collection_count', 0)} collections, "
                   f"{len(br.get('banners') or [])} banners, {len(br.get('policies') or {})} policy pages."
                   + (f" {unpriced} products have no price: they go in at 0.00 unless you send prices when I ask." if unpriced else "")
                   + "".join(f"\n- {esc(x)}" for x in (br.get("problems") or [])[:12])
                   + f"\nNothing is added to {esc(s['name'])} before your Approve tap.")
            return None
        name = a.type_in("brand_name", "The new brand's name, as the store should show it.", minutes, "Senso Foods")
        if not name:
            return WAITING
        sells = a.type_in("sells", "What will the store sell? One line, for example: herbal hair oils for women.", minutes,
                          "herbal hair oils for women")
        if not sells:
            return WAITING
        got = a.choose("sample_count", "How many sample products? Each gets sample details and a sample price from what the niche's "
                                       "D2C brands charge, tagged to change later.", [(str(n), str(n)) for n in SAMPLE_COUNTS], minutes)
        if not got:
            return WAITING
        s["brand"] = {"source": "samples", "link": s["link"], "base": s["link"], "myshopify_domain": None,
                      "name": re.sub(r"\s+", " ", name["value"]).strip()[:60], "currency": None, "live_theme": {},
                      "product_count": int(got["value"]), "more_products": False, "collection_count": 0, "best_sellers": [],
                      "best_sellers_from": "the sample products, in the order they were made",
                      "sells": re.sub(r"\s+", " ", sells["value"]).strip()[:200], "products": [], "banners": []}
        self.save()
        return None

    # ---- the store's assets: sample products, sample prices and texts, and the pictures ChatGPT makes (Harsh, 22 Oct 2026: "if not
    # then it will create some sample products", "you can add any price, compare price, etc. because we will change it later ... add
    # sample details if not available", and pictures only after the niche's D2C brands are studied, from our own product photos)
    def assets(self, path: Path) -> int:
        """The file the session wrote (skill dtj-new-store, step 1b):
            {"research": "<niche.json from provision/niche_assets.py>", "style": "<what the niche's pictures do, and our plan>",
             "products": [{"title", "description", "collection", "price", "compare_at_price", "pictures": [prompt, ...]}],
             "pictures": [{"for": "<handle>", "prompt", "refs": [our product photos], "kind": "lifestyle" | "product"}],
             "banners": [{"prompt", "refs": [...]}, ...],
             "sample_prices": {"<handle>": {"price", "compare_at_price"}}, "descriptions": {"<handle>": "<text>"}}
        Sample products only for a samples store; sample prices and descriptions only for products that have none; everything
        sample is tagged (dtj-sample, dtj-sample-price, dtj-sample-text) so it is found and replaced. Pictures only as far as the
        person's pictures answer allows, and only after the research read at least MIN_COMPETITORS brands; competitors' pictures
        are studied, never uploaded to the picture maker. Each picture is made once (a rerun keeps what is made)."""
        self.need_plan()
        s, p, a = self.s, self.s["plan"], self.ask
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        br, out, want = s["brand"], self.dir / "assets", p.get("pictures", "none")
        items = data.get("products") or []
        if items and p["source"] != "samples":
            raise SystemExit("sample products are only for a store whose products are samples")
        new_samples = p["source"] == "samples" and not br.get("products")
        if new_samples:
            why = sample_problems(items, br["product_count"])
            if why:
                raise SystemExit("the samples file is refused: " + "; ".join(why))
        products = {x["handle"]: x for x in br.get("products") or []}
        extra = [x for x in data.get("pictures") or []] if want == "all" and p["source"] == "drive" else []
        banners = [] if br.get("banners") or want not in ("all", "banners") else [
            b if isinstance(b, dict) else {"prompt": str(b)} for b in data.get("banners") or []][:5]
        jobs = [("product", prompt, out / f"{slug(x['title'])}-{i}.png", []) for x in (items if new_samples and want in ("all", "products") else [])
                for i, prompt in enumerate(x["pictures"][:3], 1)]
        for i, x in enumerate(extra, 1):
            refs = [str(r) for r in x.get("refs") or []]
            if x.get("for") not in products or not str(x.get("prompt") or "").strip() or not all(Path(r).exists() for r in refs):
                raise SystemExit(f"picture {i}: \"for\" must be one of this store's products, with a prompt and refs that exist here")
            jobs.append((x.get("kind") if x.get("kind") in ("product", "lifestyle") else "lifestyle", x["prompt"],
                         out / f"{x['for']}-ai-{i}.png", refs))
        jobs += [("banner", b["prompt"], out / f"banner-{i}.png", [str(r) for r in b.get("refs") or []]) for i, b in enumerate(banners, 1)]
        if jobs:
            why = research_problems(data.get("research"), data.get("style"))
            if why:
                raise SystemExit("no pictures before the niche research: " + "; ".join(why))
            s["research"] = {"file": str(data["research"]), "style": str(data["style"])[:1500]}
        for n, (kind, prompt, f, refs) in enumerate(jobs, 1):
            if not f.exists():
                try:
                    self.picture(kind, prompt, f, [Path(r) for r in refs])
                except Exception as exc:  # noqa: BLE001 - no route, a refused prompt, ChatGPT not answering: said in Telegram
                    a.tell(f"I could not make the pictures: {esc(str(exc)[:300])}")
                    return self.stop(f"a picture could not be made: {str(exc)[:200]}")
            self.bar("assets", n, len(jobs))
        made = s.setdefault("made_pictures", [])
        made += [str(f) for _, _, f, _ in jobs if str(f) not in made]
        if new_samples:
            br["products"] = sample_products(items, br["name"], out, with_pictures=want in ("all", "products"))
            br["best_sellers"] = [{"handle": x["handle"], "title": x["title"], "url": ""} for x in br["products"]]
            br["collections"] = collections_of(items, br["products"])
            br["collection_count"] = len(br["collections"])
            br["product_count"] = len(br["products"])
            p["products"] = [{"handle": x["handle"], "title": x["title"], "url": ""} for x in br["products"][:p.get("product_pages", 0)]]
        for i, x in enumerate(extra, 1):  # ChatGPT's pictures after the brand's own
            f = str(out / f"{x['for']}-ai-{i}.png")
            if f not in [img.get("path") for img in products[x["for"]].get("images") or []]:
                products[x["for"]].setdefault("images", []).append({"path": f, "alt": products[x["for"]]["title"]})
        if banners:
            br["banners"] = [str(out / f"banner-{i}.png") for i in range(1, len(banners) + 1)]
        texts = 0
        for h, text in (data.get("descriptions") or {}).items():
            x = products.get(h)
            if x and not re.sub(r"<[^>]+>|\s", "", x.get("body_html") or "") and 20 <= len(str(text)) <= 2000 and not CLAIM_WORDS.search(str(text)):
                x["body_html"] = "".join(f"<p>{html.escape(t.strip())}</p>" for t in str(text).split("\n") if t.strip())
                x["tags"] = [*(x.get("tags") or []), SAMPLE_TEXT_TAG]
                texts += 1
        sample_prices, refused = {}, []
        unpriced = {x["handle"] for x in products.values() if x.get("price_needed")} if p["source"] == "drive" else {
            x["handle"] for x in br.get("best_sellers") or []}
        for h, v in (data.get("sample_prices") or {}).items():
            price, cap = money(v.get("price")), money(v.get("compare_at_price"))
            if h in unpriced and price and float(price) > 0:
                sample_prices[h] = {"price": price, "compare_at_price": cap if cap and float(cap) > float(price) else None}
            else:
                refused.append(h)
        if sample_prices:
            p["sample_prices"] = sample_prices
        self.save()
        said = [f"{len(items)} sample products" if new_samples else "", f"{len(jobs)} pictures made with ChatGPT" if jobs else "",
                f"sample prices for {len(sample_prices)} products" if sample_prices else "", f"{texts} sample descriptions" if texts else ""]
        a.tell(f"Ready for <b>{esc(br['name'])}</b>: " + (", ".join(x for x in said if x) or "nothing new") + ". Everything sample is "
               "tagged (dtj-sample, dtj-sample-price, dtj-sample-text) and listed in the handover, to replace before launch."
               + (f"\nSample prices refused for: {esc(', '.join(refused[:10]))}" if refused else ""))
        self.out(json.dumps({"products": len(br.get("products") or []), "pictures": len(jobs), "banners": br.get("banners") or [],
                             "sample_prices": len(sample_prices), "descriptions": texts}))
        return 0

    def stop(self, why: str) -> int:
        self.s["stopped"] = why
        self.save()
        self.ask.tell(f"Stopped: {esc(why)}.")  # the person hears why, not only the laptop (first live run, 21 Oct 2026)
        self.out(f"stopped: {why}")
        return 1

    def need_plan(self) -> None:
        if not self.s.get("planned"):
            raise SystemExit(f"no plan for job {self.job} yet: run store_job.py start first")

    # ---- the draft theme
    def draft(self, minutes: float = APPROVE_MINUTES) -> int:
        self.need_plan()
        s, p = self.s, self.s["plan"]
        if s.get("draft"):
            self.out(json.dumps(s["draft"]))
            return 0
        self.bar("draft")
        if p["theme"] == "horizon":  # the person added Horizon in the admin: that unpublished theme is the draft
            found = [t for t in self.access.themes(role="unpublished") if "horizon" in str(t.get("name", "")).lower()]
            if not found:
                self.ask.tell("I cannot find an unpublished theme called Horizon yet. Add it (Online Store > Themes > Add theme > "
                              "Horizon, do not publish), then I look again.")
                return WAITING
            newest = max(found, key=lambda t: int(t.get("id") or 0))
            s["draft"] = {"id": str(newest["id"]), "name": newest.get("name"), "role": "unpublished", "from": "added by a person"}
            self.save()
            self.out(json.dumps(s["draft"]))
            return 0
        live = (s["scan"].get("live_theme") or {}).get("name") or "the live theme"
        name = f"DTJ Draft {self.today()}"
        ok, by = self.ask.approve("ok_draft", f"Make the draft copy: duplicate the live theme <b>{esc(live)}</b> of {esc(s['name'])} as "
                                              f"<b>{esc(name)}</b>. It stays unpublished: shoppers see nothing.", minutes)
        if ok is None:
            return WAITING
        if not ok:
            self.logged("draft copy of the live theme", "skipped in Telegram", by, result="blocked")
            self.out(f"skipped by {by}")
            return SKIPPED
        made = self.access.duplicate_live(name)
        made["approved_by"] = f"{by} (Telegram Approve)"
        s["draft"] = made
        self.save()
        self.logged("draft copy of the live theme (theme duplicate, unpublished)", "the store job designs into a draft copy only",
                    made["approved_by"], after=made, evidence={"commands": getattr(self.access, "commands", [])})
        self.ask.tell(f"Draft copy made: <b>{esc(name)}</b> (theme {esc(made['id'])}, unpublished).")
        self.out(json.dumps(made))
        return 0

    # ---- the brand copy (every store write runs in n8n after the Approve tap: no laptop step, Harsh 21 Oct 2026)
    def copy(self, minutes: float = APPROVE_MINUTES, again: bool = False) -> int:
        """A read-only plan through the install service (DTJ Store Builder), kept there for this job; its Approve tap, which itself
        starts "Store Factory: Brand Copy" in n8n; then waits until the install service says the copy is finished."""
        self.need_plan()
        s, p = self.s, self.s["plan"]
        if not p.get("copy"):
            self.out("nothing to copy: this store is the brand")
            return 0
        if again and s.get("copy_result"):  # a new copy after a finished one (22 Oct 2026: the policy pages): what the store has is skipped
            for k in ("copy_plan", "copy_result", "copy_approved_by"):
                s.pop(k, None)
            self.ask.forget("ok_copy")  # its own Approve tap: the first one never counts twice
            self.save()
        if s.get("copy_result"):
            self.out(json.dumps(s["copy_result"]))
            return 0
        local = p.get("source") in ("drive", "samples")
        if p.get("source") == "samples" and not s["brand"]["products"]:
            raise SystemExit("the sample products are not made yet: run store_job.py assets first")
        if not s.get("copy_plan"):
            waiting = self.prices(minutes)
            if waiting is not None:
                return waiting
        self.bar("copy")
        end = self.ask.clock() + minutes * 60
        while not s.get("copy_plan"):
            try:
                plan = self.planner(p["brand"]["link"], s["shop"], p["brand"].get("currency"), self.dir / "copy", job=self.job,
                                    brand=s["brand"] if local else None, prices=p.get("prices") or {})
            except NotInstalled:
                if not s.get("builder_asked"):
                    self.ask.tell(f"One tap first: install <b>DTJ Store Builder</b> on <b>{esc(s['name'])}</b>. It is the DTJ app that may "
                                  "add the brand's products, collections and policy pages; the block apps never can. Dev Dashboard > Apps > "
                                  f"DTJ Store Builder > Install app > {esc(s['shop'])}. I go on by myself once it is installed.")
                    s["builder_asked"] = True
                    self.save()
                if self.ask.clock() >= end:
                    return WAITING
                self.ask.sleep(60)
                continue
            except Exception as exc:  # noqa: BLE001 - the brand stopped answering, the install service refused: said plainly
                self.ask.tell(f"I could not plan the copy: {esc(str(exc)[:300])}")
                return self.stop(f"the copy could not be planned: {str(exc)[:200]}")
            from provision.brand_copy import summary  # noqa: PLC0415
            s["copy_plan"] = {"summary": summary(plan), "notes": plan["notes"], "status": plan["status"], "products": len(plan["products"])}
            self.save()
        cp = s["copy_plan"]
        notes = "".join(f"\n- {esc(n)}" for n in cp["notes"])
        what = {"drive": "Add the Drive folder's products of", "samples": "Add the sample products of"}.get(p.get("source"), "Copy")
        ok, by = self.ask.approve("ok_copy", f"{what} <b>{esc(p['brand']['name'])}</b> into <b>{esc(s['name'])}</b>: {esc(cp['summary'])}. "
                                             "Nothing the store has is changed or deleted." + notes, minutes)
        if ok is None:
            return WAITING
        if not ok:
            self.logged("brand copy into the store", "skipped in Telegram", by, result="blocked")
            self.out(f"skipped by {by}")
            return SKIPPED
        if not s.get("copy_approved_by"):
            s["copy_approved_by"] = f"{by} (Telegram Approve)"
            self.save()
            self.logged("brand copy into the store (products, collections, empty policy pages): run by n8n, Store Factory: Brand Copy",
                        "the store is built from the brand", s["copy_approved_by"], evidence={"plan": cp})
        while True:  # n8n does the copy now; this only reads how far it is
            try:
                st = self.copy_status(self.job)
            except Exception:  # noqa: BLE001 - the install service did not answer this time: the next look tries again
                st = {}
            done, total = st.get("done") or {}, st.get("total") or {}
            if total:
                self.bar("copy", done.get("products", 0) + done.get("failed", 0), max(total.get("products", 0), 1))
            if st.get("finished"):
                s["copy_result"] = st
                self.save()
                self.out(json.dumps(st))
                return 1 if st.get("stopped") else 0
            if self.ask.clock() >= end:
                return WAITING
            self.ask.sleep(20)

    def prices(self, minutes: float) -> int | None:
        """Products without a price (a website that shows none, a Drive folder without one): the sample prices from the niche's
        prices (Harsh, 22 Oct 2026: "you can add any price, compare price, etc. because we will change it later"; tagged
        dtj-sample-price), the person's typed prices, or 0.00 with dtj-price-needed. Every product ACTIVE. None = go on; else the
        exit code."""
        s, p, a = self.s, self.s["plan"], self.ask
        br = s["brand"]
        if p.get("source") in ("drive", "samples"):
            unpriced = [x for x in br["products"] if x.get("price_needed")]
            sellers = [{"handle": x["handle"], "title": x["title"], "url": ""} for x in unpriced]
        else:
            sellers = br.get("best_sellers") or []
            unpriced = [None] * max(0, br["product_count"] - br.get("prices", br["product_count"]))
        if not unpriced:
            return None
        sample = p.get("sample_prices") or {}
        got = a.choose("prices", f"{len(unpriced)} products have no price."
                       + (f" I have sample prices for {len(sample)} of them, from what the niche's D2C brands charge, tagged "
                          "dtj-sample-price to change later." if sample else "")
                       + " Without a price a product goes in ACTIVE at 0.00 with the tag dtj-price-needed.",
                       ([("Use the sample prices", "sample")] if sample else []) + [("I'll type the prices", "type"),
                                                                                    ("Leave them at 0.00", "later")], minutes)
        if not got:
            return WAITING
        if got["value"] == "later" or "prices" in p:
            return None
        if got["value"] == "sample":
            p["prices"] = {h: dict(v, sample=True) for h, v in sample.items()}
            self.save()
            return None
        got = a.type_in("prices_typed", "One line per product: its name = price, for example\nMasala Chai = 249", minutes,
                        "Masala Chai = 249")
        if not got:
            return WAITING
        prices, left = {}, []
        for line in got["value"].splitlines():
            m = PRICE_LINE.match(line.strip())
            if not m:
                if line.strip():
                    left.append(f"{line.strip()[:80]}: not \"name = price\"")
                continue
            hit, miss, _ = match_products([m.group(1)], sellers)
            if hit:
                prices[hit[0]["handle"]] = {"price": m.group(2), "compare_at_price": None, "sample": False}
            left += miss
        typed = len(prices)
        p["prices"] = {**{h: dict(v, sample=True) for h, v in sample.items()}, **prices}  # typed wins; samples fill the rest
        self.save()
        a.tell(f"Prices noted for {typed} products" + (f", sample prices for {len(p['prices']) - typed} more" if len(p["prices"]) > typed
                                                       else "") + "." + ("".join(f"\n- {esc(x)}" for x in left[:12]) if left else ""))
        return None

    def activate(self, approved_by: str, handles: list[str]) -> int:
        """Products an earlier copy added as drafts, switched to ACTIVE and shown on the Online Store (Harsh, 22 Oct 2026: "all the
        products will stay active none of them will be kept as draft"). Through DTJ Store Builder: only a draft changes, only its
        status; the yes is a person's, by name. The install service does 12 a call and returns the rest in `left`."""
        self.need_plan()
        if not approved_by.strip():
            raise SystemExit("--approved-by is required: the person who said yes, by name")
        done = {"activated": [], "already_active": [], "not_found": [], "failed": []}
        left, total = list(dict.fromkeys(handles)), len(set(handles))
        while left:
            got = self.catcher({"op": "activate", "shop": self.s["shop"], "approved_by": approved_by, "handles": left[:250]})
            for k in done:
                done[k] += got.get(k) or []
            left = (got.get("left") or []) + left[250:]
            self.bar("copy", total - len(left), total)
        self.logged(f"products switched from draft to ACTIVE: {len(done['activated'])}", "every product stays active (Harsh, 22 Oct 2026)",
                    approved_by, result="failed" if done["failed"] else "success", after={k: len(v) for k, v in done.items()})
        self.out(json.dumps({k: len(v) for k, v in done.items()} | {"failed": done["failed"][:10]}))
        return 1 if done["failed"] else 0

    def handles(self) -> list[str]:
        """The products this job added: the samples or the Drive folder's (kept here), else the brand's website read again."""
        br = self.s.get("brand") or {}
        if br.get("products"):
            return [x["handle"] for x in br["products"]]
        from provision.brand_copy import read_brand  # noqa: PLC0415
        return [x["handle"] for x in read_brand(self.s["plan"]["brand"]["link"])["products"]]

    # ---- About, Contact, FAQ and the menus (22 Oct 2026, Harsh: "we have to handover a product ready shopify store so if anything is
    # missed by me you will cover it"); through DTJ Store Builder, each with its own Approve tap
    def pages(self, path: Path, minutes: float = APPROVE_MINUTES) -> int:
        """The pages the session wrote (skill dtj-new-store, step 7): {"pages": [{"handle", "title", "body_html", "template_suffix":
        "contact" for the contact form, "sample": true when the text is DTJ's sample}]}. New pages only: a page the store has stays.
        Sample text never carries a claim word; contact details are the brand's own or left out (the session's rule)."""
        self.need_plan()
        s, a = self.s, self.ask
        if s.get("pages_result"):
            self.out(json.dumps(s["pages_result"]))
            return 0
        items = json.loads(Path(path).read_text(encoding="utf-8")).get("pages") or []
        why = []
        if not 1 <= len(items) <= 6:
            why.append(f"{len(items)} pages: 1 to 6")
        for i, x in enumerate(items, 1):
            if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,99}", str(x.get("handle") or "")) or not str(x.get("title") or "").strip():
                why.append(f"page {i}: a handle (lowercase, dashes) and a title")
            if x.get("sample") and CLAIM_WORDS.search(re.sub(r"<[^>]+>", " ", str(x.get("body_html") or ""))):
                why.append(f"page {i}: a claim word in sample text")
        if why:
            raise SystemExit("the pages file is refused: " + "; ".join(why))
        samples = [x["title"] for x in items if x.get("sample")]
        ok, by = a.approve("ok_pages", f"Add {len(items)} pages to <b>{esc(s['name'])}</b>: {esc(', '.join(x['title'] for x in items))}. "
                                       "New pages only: a page the store already has is left as it is."
                                       + (f" Sample text, to replace before launch: {esc(', '.join(samples))}." if samples else ""), minutes)
        if ok is None:
            return WAITING
        if not ok:
            self.logged("pages (About, Contact, FAQ)", "skipped in Telegram", by, result="blocked")
            self.out(f"skipped by {by}")
            return SKIPPED
        approved = f"{by} (Telegram Approve)"
        self.bar("pages", 0, 2)
        try:
            res = self.catcher({"op": "pages", "shop": s["shop"], "approved_by": approved,
                                "pages": [{"handle": x["handle"], "title": x["title"].strip(), "body": str(x.get("body_html") or ""),
                                           "template_suffix": x.get("template_suffix") or ""} for x in items]})
        except Exception as exc:  # noqa: BLE001 - the app has no pages permission yet, Shopify refused: said in Telegram
            a.tell(f"The pages could not be added: {esc(str(exc)[:300])}")
            self.logged("pages (About, Contact, FAQ)", "the install service refused", approved, result="failed")
            return 1
        s["pages_result"] = res
        s["sample_pages"] = [x["title"] for x in items if x.get("sample") and x["handle"] in res.get("created", [])]
        self.save()
        self.logged(f"pages added: {', '.join(res.get('created') or []) or 'none'}", "a store handed over ready to sell", approved,
                    result="failed" if res.get("failed") else "success", after=res)
        a.tell(f"Pages on <b>{esc(s['name'])}</b>: added {esc(', '.join(res.get('created') or []) or 'none')}"
               + (f"; already there, left as they were: {esc(', '.join(res['skipped']))}" if res.get("skipped") else "")
               + (f"; failed: {esc(', '.join(f['handle'] for f in res['failed']))}" if res.get("failed") else "") + ".")
        self.out(json.dumps(res))
        return 1 if res.get("failed") else 0

    def menu_links(self) -> dict[str, list[dict]]:
        """The main menu and the footer from what the store has now: up to 5 collections (the brand's, else the store's), the pages."""
        s = self.s
        cols = [(c.get("title") or c["handle"], c["handle"]) for c in (s.get("brand") or {}).get("collections") or [] if c.get("handle")]
        if not cols:
            try:
                cols = [(h.replace("-", " ").capitalize(), h) for h in self.catcher({"op": "target", "shop": s["shop"]}).get("collections") or []]
            except Exception:  # noqa: BLE001 - no collections known: the menu has none
                cols = []
        main = ([{"title": "Home", "type": "FRONTPAGE"}, {"title": "Shop all", "type": "CATALOG"}]
                + [{"title": t[:40], "type": "COLLECTION", "handle": h} for t, h in cols[:5]]
                + [{"title": "About us", "type": "PAGE", "handle": "about-us"}, {"title": "Contact", "type": "PAGE", "handle": "contact"}])
        footer = ([{"title": "About us", "type": "PAGE", "handle": "about-us"}, {"title": "Contact", "type": "PAGE", "handle": "contact"},
                   {"title": "FAQ", "type": "PAGE", "handle": "faq"}, {"title": "Search", "type": "SEARCH"}]
                  + [{"title": t, "type": "SHOP_POLICY", "handle": h} for t, h in FOOTER_POLICIES])
        return {"main-menu": main, "footer": footer}

    def menus(self, minutes: float = APPROVE_MINUTES) -> int:
        """The store's main menu and footer set to the store's real collections, pages and policies; one Approve tap for both. A link
        the store does not have is left out by the install service; the old links are kept in its audit row."""
        self.need_plan()
        s, a = self.s, self.ask
        if s.get("menus_result"):
            self.out(json.dumps(s["menus_result"]))
            return 0
        links = self.menu_links()
        ok, by = a.approve("ok_menus", f"Set the menus of <b>{esc(s['name'])}</b>:\nMain menu: {esc(', '.join(x['title'] for x in links['main-menu']))}"
                                       f"\nFooter: {esc(', '.join(x['title'] for x in links['footer']))}\nA link the store does not have is left "
                                       "out; the old menus are kept on record.", minutes)
        if ok is None:
            return WAITING
        if not ok:
            self.logged("menus (main menu, footer)", "skipped in Telegram", by, result="blocked")
            self.out(f"skipped by {by}")
            return SKIPPED
        approved, out = f"{by} (Telegram Approve)", {}
        for handle, items in links.items():
            try:
                out[handle] = self.catcher({"op": "menu", "shop": s["shop"], "handle": handle, "items": items, "approved_by": approved})
            except Exception as exc:  # noqa: BLE001 - one menu refused: the other is still set, and both are said
                out[handle] = {"error": str(exc)[:300]}
        s["menus_result"] = out
        self.save()
        failed = [h for h, r in out.items() if r.get("error")]
        self.logged("menus set: " + ", ".join(h for h in out if h not in failed), "a store handed over ready to sell", approved,
                    result="failed" if failed else "success", evidence={h: {"before": r.get("before")} for h, r in out.items()},
                    after={h: r.get("items") for h, r in out.items()})
        a.tell(f"Menus of <b>{esc(s['name'])}</b>: " + "; ".join(
            f"{h}: " + (f"not set ({esc(r['error'][:150])})" if r.get("error") else esc(", ".join(i["title"] for i in r.get("items") or [])))
            for h, r in out.items()))
        self.out(json.dumps(out))
        return 1 if failed else 0

    # ---- the apps
    def apps(self, minutes: float = APPROVE_MINUTES) -> int:
        self.need_plan()
        s, p = self.s, self.s["plan"]
        if s.get("apps_approved_by"):
            self.out(self.apps_command())
            return 0
        if p["whose"] == "client":
            what = (f"Add the 7 DTJ app copies for <b>{esc(p['label'])}</b>: created and released in DTJ's Shopify account. The store "
                    "sees nothing until its owner taps Install (I send the 7 buttons here).")
        else:
            what = (f"Connect DTJ's own apps to <b>{esc(s['name'])}</b>: register the store with DTJ's install service, update that "
                    "service, then send you 7 Install buttons and switch each app on as soon as it is installed.")
        ok, by = self.ask.approve("ok_apps", what, minutes)
        if ok is None:
            return WAITING
        if not ok:
            self.logged("DTJ apps for the store", "skipped in Telegram", by, result="blocked")
            self.out(f"skipped by {by}")
            return SKIPPED
        s["apps_approved_by"] = f"{by} (Telegram Approve)"
        self.save()
        self.logged("DTJ apps for the store (app copies: create, release; install service deploy)", "the store's pages use DTJ's blocks",
                    s["apps_approved_by"])
        self.out(self.apps_command())
        return 0

    # ---- DTJ's own store: the 7 Install buttons, then each app switched on (Harsh, 22 Oct 2026: "Install buttons in Telegram")
    def installs(self, minutes: float = APPROVE_MINUTES) -> int:
        """One message with an Install button per DTJ app (Shopify's own install page for this store: an install is always a
        person's tap there), then it watches the install service and switches each app on as soon as it is installed, under the
        apps Approve tap. Exit 0 once all are on, 3 while some are still not installed (run it again to keep watching)."""
        self.need_plan()
        s = self.s
        if s["plan"].get("whose") != "dtj":
            self.out("a client's store: add_shop.py sends its Install buttons (skill dtj-add-shop)")
            return 0
        if not s.get("apps_approved_by"):
            raise SystemExit("no apps Approve tap yet: run store_job.py apps first")
        apps = self.org_apps()
        handle = s["shop"].split(".")[0]
        if not s.get("install_buttons_sent"):
            rows = [[{"text": f"Install {label}", "url": f"https://admin.shopify.com/store/{handle}/oauth/install?client_id={cid}"}]
                    for _part, label, cid in apps]
            self.ask.send("sendMessage", {"chat_id": self.ask.chat, "parse_mode": "HTML", "disable_web_page_preview": True,
                                          "text": f"Install DTJ's {len(apps)} apps on <b>{esc(s['name'])}</b>: tap each button while logged in to "
                                                  "its admin and press Install on Shopify's page. I switch each one on as soon as it is installed.",
                                          "reply_markup": {"inline_keyboard": rows}})
            s["install_buttons_sent"] = True
            self.save()
        on = s.setdefault("apps_on", [])
        end = self.ask.clock() + minutes * 60
        while True:
            for part, label, _cid in apps:
                if part in on:
                    continue
                key = f"{self.job}-{part}"
                code, state = self.licence(key, "status", "")
                if code != 200 or not state.get("app_handle"):
                    continue  # not installed yet
                if state.get("licence") != "active":
                    code, change = self.licence(key, "active", s["apps_approved_by"])
                    if code != 200:
                        self.out(f"  {label}: installed, but switching it on failed ({code}): tried again on the next look")
                        continue
                on.append(part)
                self.save()
                self.logged(f"{label} switched on (licence active) after its install", "the store's pages use DTJ's blocks", s["apps_approved_by"],
                            after={"app": key})
            self.bar("apps", len(on), len(apps))
            if len(on) == len(apps):
                self.ask.tell(f"All {len(apps)} DTJ apps are installed and switched on in <b>{esc(s['name'])}</b>.")
                self.out(json.dumps({"apps_on": on}))
                return 0
            if self.ask.clock() >= end:
                self.out(f"{len(on)} of {len(apps)} apps installed and on so far; run store_job.py installs again to keep watching")
                return WAITING
            self.ask.sleep(20)

    def apps_command(self) -> str:
        s, p = self.s, self.s["plan"]
        theme = f" --theme {s['draft']['id']}" if s.get("draft") else ""
        if p["whose"] == "client":
            return (f'python services/install-catcher/tools/add_shop.py --shop {s["shop"]} --label "{p["label"]}" --chat {s["chat"]} '
                    f'--approved-by "{s["apps_approved_by"]}"{theme}')
        return (f'DTJ\'s own store: skill dtj-add-shop, path B (python services/install-catcher/tools/add_client.py --org --shop {s["shop"]} '
                f'--label "{s["name"]}" --name {self.job}, then the deploy), approved by {s["apps_approved_by"]}')

    # ---- one write's Approve tap
    def approve(self, key: str, text: str, minutes: float = APPROVE_MINUTES) -> int:
        self.need_plan()
        ok, by = self.ask.approve(key, text, minutes)
        if ok is None:
            return WAITING
        self.logged(f"approval {key}", "a write that needs a person's yes", by, result="success" if ok else "blocked",
                    evidence={"asked": text[:300]})
        self.out(f"APPROVED_BY={by} (Telegram Approve)" if ok else f"skipped by {by}")
        return 0 if ok else SKIPPED

    def record(self, part: str, preview: str, code: str = "", note: str = "") -> int:
        self.s.setdefault("written", []).append({"part": part, "preview": preview, "code": code, "note": note[:300]})
        self.save()
        return 0

    def finish(self, status: str, note: str = "") -> int:
        if status not in STATUSES:
            raise SystemExit(f"--status must be one of {STATUSES}")
        written = self.s.get("written", [])
        body = {"store_status": status, "shop": self.s.get("shop", ""), "name": self.s.get("name", ""),
                "draft_theme_id": (self.s.get("draft") or {}).get("id", ""),
                "pages": [{"part": w["part"], "preview": w["preview"]} for w in written][:40], "note": note[:700]}
        self.dir.mkdir(parents=True, exist_ok=True)
        (self.dir / "answer.json").write_text(json.dumps(body, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        text = self.handover()
        (self.dir / "handover.md").write_text(text, encoding="utf-8")
        if self.s.get("chat"):
            self.ask.tell(esc(text.split("\n## The store owner")[0].replace("# ", "", 1))[:3500] + "\n\nThe full list (with the owner's "
                          "settings) is in the handover file.")
        if self.progress:
            self.progress.finish(status == "done", f"{self.s.get('name', '')}: {status}" + (f". {note[:200]}" if note else ""))
        self.out(f"answer for n8n: {self.dir / 'answer.json'}; handover: {self.dir / 'handover.md'}")
        return 0

    def handover(self) -> str:
        """What is in the store, what is sample, and what only the owner can set (Harsh, 22 Oct 2026: "we have to handover a product
        ready shopify store so if anything is missed by me you will cover it"). Counts come from this job's own records."""
        s, p = self.s, self.s.get("plan") or {}
        br, done = s.get("brand") or {}, (s.get("copy_result") or {}).get("done") or {}
        prods = br.get("products") or []
        tagged = lambda tag: [x["title"] for x in prods if tag in (x.get("tags") or [])]  # noqa: E731
        sample_priced = sorted(h for h, v in (p.get("prices") or {}).items() if v.get("sample"))
        draft = s.get("draft") or {}
        lines = [f"# {s.get('name', '')}: handover, {self.today()}", "", "## In the store now"]
        if draft:
            lines.append(f"- Draft theme: {draft.get('name')} ({draft.get('id')}), unpublished: the live store has not changed")
        if s.get("copy_result"):
            lines.append(f"- Added: {done.get('products', 0)} products (every one ACTIVE), {done.get('collections', 0)} collections, "
                         f"{done.get('policies', 0)} policy pages")
        lines += [f"- {w['part']}: {w['preview']}" for w in s.get("written") or []] or ["- No page written yet"]
        if s.get("pages_result"):
            lines.append(f"- Pages added: {', '.join(s['pages_result'].get('created') or []) or 'none'}")
        menus_set = [h for h, r in (s.get("menus_result") or {}).items() if not r.get("error")]
        if menus_set:
            lines.append(f"- Menus set: {', '.join(menus_set)}")
        lines += ["", "## Samples to replace before launch"]
        samples = [("Sample products", tagged(SAMPLE_TAG)), ("Sample prices (dtj-sample-price)", sample_priced + tagged(SAMPLE_PRICE_TAG)),
                   ("Sample descriptions (dtj-sample-text)", tagged(SAMPLE_TEXT_TAG)),
                   ("Pictures made by ChatGPT", [Path(x).name for x in s.get("made_pictures") or []]),
                   ("Pages with sample text", s.get("sample_pages") or [])]
        unpriced = [x["title"] for x in prods if x.get("price_needed") and x["handle"] not in (p.get("prices") or {})]
        if unpriced:
            samples.append(("No price yet, at 0.00 (dtj-price-needed)", unpriced))
        for label, names in samples:
            if names:
                lines.append(f"- {label}: {len(set(names))} ({', '.join(sorted(set(names))[:8])}{', ...' if len(set(names)) > 8 else ''})")
        if not any(names for _, names in samples):
            lines.append("- None")
        lines += ["", "## The store owner's settings (Shopify admin; DTJ does not change these)",
                  "- Payments: a payment provider, and Cash on Delivery if the brand takes it",
                  "- Shipping: zones and rates",
                  "- Taxes: the GST details",
                  "- Domain: connect the brand's own domain",
                  "- Store details: the contact email, the sender email, phone and address",
                  "- Policies: refund, shipping, privacy and terms (Settings > Policies), checked by the brand",
                  *([] if len(menus_set) == 2 else ["- Menus: the main menu and footer menu linking the collections (Online Store > Navigation)"]),
                  "- Launch: a test order in test mode, then publish the draft theme and remove the password page (Harsh's yes)",
                  "- Ads: the Meta pixel and the Google channel (DTJ's ads team)"]
        return "\n".join(lines) + "\n"


def _scan(link: str) -> dict:
    from page_builder.store_scan import scan  # noqa: PLC0415
    return scan(link, private=_private_scan)


def _scan_brand(link: str) -> dict:
    """The brand to copy: a Shopify store (its catalogue, best sellers first), else its own website's product pages (22 Oct 2026,
    Senso: a WordPress trade site; Harsh: products without a price go in as hidden drafts)."""
    from page_builder.store_scan import NotShopify, scan  # noqa: PLC0415
    try:
        return scan(link)
    except NotShopify:
        from provision.brand_copy import read_site  # noqa: PLC0415
        site = read_site(link)
        return {"link": link, "base": site["base"], "myshopify_domain": None, "name": site["name"], "currency": None, "live_theme": {},
                "product_count": len(site["products"]), "more_products": False, "collection_count": 0,
                "best_sellers": [{"handle": x["handle"], "title": x["title"], "url": x["source"]} for x in site["products"]],
                "best_sellers_from": "the brand's website, in its own order (not a Shopify store, so there is no sales order)",
                "platform": "website", "prices": sum(1 for x in site["products"] if not x["price_needed"])}


def _private_scan(domain: str, link: str, access=None, catcher=None) -> dict:
    """A store whose public pages show nothing (an admin link, or a store behind its password page, as every dev store is; 22 Oct
    2026, dtj-testing): its live theme through this laptop's Shopify login, and its name, currency, products and collections through
    DTJ Store Builder when it is installed there. Read only."""
    from page_builder import theme_target as tt  # noqa: PLC0415
    access = access or tt.open_access(domain)
    live = next((x for x in access.themes(role="live") if x.get("role") == "live"), {})
    schema, version = None, None
    if live:
        with tempfile.TemporaryDirectory() as tmp:
            access.pull(str(live["id"]), [tt.SCHEMA_FILE], Path(tmp))
            f = Path(tmp) / tt.SCHEMA_FILE
            if f.exists():
                info = next((s for s in json.loads(f.read_text(encoding="utf-8")) if s.get("name") == "theme_info"), {})
                schema, version = info.get("theme_name"), info.get("theme_version")
    try:
        inside = (catcher or _catcher)({"op": "target", "shop": domain})
    except (NotInstalled, CatcherError):
        inside = {}  # Store Builder not installed yet: the name falls back to the handle, the counts to 0
    handles = inside.get("products") or []
    return {"link": link, "base": f"https://{domain}", "myshopify_domain": domain, "name": inside.get("name") or domain.split(".")[0],
            "currency": inside.get("currency"), "live_theme": {"name": live.get("name"), "id": str(live.get("id") or ""),
                                                               "schema_name": schema, "schema_version": version},
            "product_count": len(handles), "more_products": False, "collection_count": len(inside.get("collections") or []),
            "best_sellers": [{"handle": h, "title": h, "url": f"https://{domain}/products/{h}"} for h in handles],
            "best_sellers_from": "the store's product list (it is behind a password, so there is no sales order)", "password": True}


class NotInstalled(Exception):
    """DTJ Store Builder is not installed on the store (or the store is not in DTJ's organization)."""


class CatcherError(Exception):
    pass


def _catcher(body: dict, opener=urllib.request.urlopen, sleep=time.sleep) -> dict:
    """One signed call to the install service's POST /copy (DTJ_CATCHER_CONTROL_KEY, as licence_call.py signs /licence). A dropped
    connection, a 429 or a 5xx is tried again up to 3 times with a growing pause (CLAUDE.md self-healing; 22 Oct 2026: a connection
    reset stopped the Senso policy copy); every try is signed with a fresh time."""
    sys.path.insert(0, str(ROOT / "services" / "install-catcher" / "tools"))
    from deploy import read_var  # noqa: PLC0415
    key = read_var("DTJ_CATCHER_CONTROL_KEY")
    if not key:
        raise CatcherError("DTJ_CATCHER_CONTROL_KEY is not set on this laptop (vault.py pull)")
    for attempt in range(4):
        raw = json.dumps({**body, "ts": int(time.time())}).encode()
        req = urllib.request.Request(f"{CATCHER}/copy", data=raw, method="POST", headers={
            "Content-Type": "application/json", "User-Agent": "dtj-store-job/1",
            "X-DTJ-Signature": hmac.new(key.encode(), raw, hashlib.sha256).hexdigest()})
        try:
            with opener(req, timeout=120) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as exc:
            try:
                why = json.loads(exc.read().decode()).get("error", "")
            except ValueError:
                why = ""
            if (exc.code == 429 or exc.code >= 500) and attempt < 3:
                sleep(2 ** (attempt + 1))
                continue
            if exc.code == 404 and "not installed" in why:
                raise NotInstalled(why) from exc
            raise CatcherError(f"the install service said {exc.code}: {why or 'no reason given'}") from exc
        except (urllib.error.URLError, OSError) as exc:
            if attempt < 3:
                sleep(2 ** (attempt + 1))
                continue
            raise CatcherError(f"the install service did not answer after 4 tries ({exc})") from exc
    raise CatcherError("unreachable")


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-")[:80] or "product"


def money(v) -> str | None:
    s = str(v if v is not None else "").replace(",", "").strip()
    return s if re.fullmatch(r"\d{1,9}(\.\d{1,2})?", s) else None


def research_problems(path, style) -> list[str]:
    """Pictures wait for the niche research (Harsh, 22 Oct 2026: "ensuring you dont generate bad results you will search top 5
    competitors in that brand niche"): its niche.json with at least MIN_COMPETITORS brands read, and the session's written study."""
    why = []
    try:
        niche = json.loads(Path(str(path)).read_text(encoding="utf-8"))
        read = [c for c in niche.get("competitors") or [] if c.get("banners") or any(x.get("pictures") for x in c.get("products") or [])]
        if len(read) < MIN_COMPETITORS:
            why.append(f"{len(read)} competitors read, at least {MIN_COMPETITORS} are needed")
    except (OSError, ValueError, TypeError):
        why.append("no research file: run provision.niche_assets on the niche's D2C brands first")
    if len(str(style or "").strip()) < 80:
        why.append("no \"style\": what the niche's pictures do and how ours will look (a few lines)")
    return why


def sample_problems(items: list, want: int) -> list[str]:
    """Why a samples file cannot be used: the count asked for, a title, a description, a sample price (Harsh, 22 Oct 2026: "you
    can add any price, compare price, etc. because we will change it later") and 1-3 picture prompts each; never a claim word
    (CLAUDE.md rule 5)."""
    why = []
    if not 1 <= len(items) <= want:
        why.append(f"{len(items)} products, the person asked for {want}")
    seen = set()
    for i, x in enumerate(items, 1):
        if not isinstance(x, dict):
            why.append(f"product {i} is not an object")
            continue
        price, cap = money(x.get("price")), money(x.get("compare_at_price"))
        if not price or float(price) <= 0:
            why.append(f"product {i}: a sample price (a number above 0)")
        elif x.get("compare_at_price") not in (None, "") and (not cap or float(cap) <= float(price)):
            why.append(f"product {i}: the compare-at price must be above the price")
        title, text = str(x.get("title") or "").strip(), str(x.get("description") or "").strip()
        if not title or len(title) > 80 or slug(title) in seen:
            why.append(f"product {i}: a title of 1-80 characters, not used twice")
        seen.add(slug(title))
        if not 20 <= len(text) <= 2000:
            why.append(f"product {i}: a description of 20-2000 characters")
        for found in {m.group(0).lower() for m in CLAIM_WORDS.finditer(f"{title} {text}")}:
            why.append(f"product {i} says \"{found}\": no claims on a sample")
        pics = x.get("pictures")
        if not isinstance(pics, list) or not 1 <= len(pics) <= 3 or not all(isinstance(q, str) and q.strip() for q in pics):
            why.append(f"product {i}: 1-3 picture prompts")
    return why


def sample_products(items: list, brand: str, out: Path, with_pictures: bool = True) -> list[dict]:
    """The samples in brand_copy's product shape (as /products.json shows one), with their sample prices and both tags."""
    made = []
    for x in items:
        h = slug(x["title"])
        body = "".join(f"<p>{html.escape(para.strip())}</p>" for para in str(x["description"]).split("\n") if para.strip())
        cap = money(x.get("compare_at_price"))
        made.append({"handle": h, "title": x["title"].strip(), "body_html": body, "vendor": brand, "product_type": "",
                     "tags": [SAMPLE_TAG, SAMPLE_PRICE_TAG], "options": [{"name": "Title", "position": 1, "values": ["Default Title"]}],
                     "variants": [{"option1": "Default Title", "price": money(x["price"]), "compare_at_price": cap, "sku": ""}],
                     "price_needed": False, "source": "sample (made by DTJ for the design)",
                     "images": [{"path": str(out / f"{h}-{i}.png"), "alt": x["title"].strip()}
                                for i in range(1, min(len(x["pictures"]), 3) + 1)] if with_pictures else []})
    return made


def collections_of(items: list, products: list[dict]) -> list[dict]:
    out: dict[str, dict] = {}
    for x, prod in zip(items, products):
        for name in [c.strip() for c in str(x.get("collection") or "").split(",") if c.strip()][:3]:
            c = out.setdefault(slug(name), {"handle": slug(name), "title": name[:80], "description_html": "", "products": []})
            c["products"].append(prod["handle"])
    return list(out.values())


def _drive(link: str, out: Path) -> dict:
    """A new store's products from a Google Drive folder shared with "Anyone with the link" (provision/drive_assets.py)."""
    from provision.drive_assets import read_folder  # noqa: PLC0415
    br = read_folder(link, out)
    br.setdefault("myshopify_domain", None)
    br.setdefault("currency", None)
    br.setdefault("live_theme", {})
    br.setdefault("more_products", False)
    return br


def _picture(kind: str, prompt: str, out: Path, refs: list[Path] = ()) -> dict:
    """One picture made with ChatGPT (provision/ai_images.py: the ChatGPT command on DTJ's VPS, else OpenAI's API with DTJ's key,
    else a local logged-in ChatGPT), with our own product photos uploaded as references."""
    from provision import ai_images  # noqa: PLC0415
    route, why = ai_images.route()
    if not route:
        raise RuntimeError(why)
    out.parent.mkdir(parents=True, exist_ok=True)
    return ai_images.make(kind, prompt, out, backend=route, refs=list(refs))


UPLOADABLE = (".jpg", ".jpeg", ".png", ".webp", ".gif")


def _local_pictures(brand: dict, store: str, upload=None) -> dict:
    """A brand whose pictures are files on this laptop (the Drive folder's, ChatGPT's): each one sent to Shopify's own staged upload
    through DTJ Store Builder (provision/staged_upload.py), then named by its upload address, as a website's picture is by its link.
    A picture in another format, or bigger than Shopify takes, is left out and said in the plan's notes."""
    if upload is None:
        from provision.staged_upload import upload  # noqa: PLC0415
    paths = [img["path"] for x in brand["products"] for img in x.get("images") or [] if img.get("path")]
    ok = [x for x in paths if Path(x).suffix.lower() in UPLOADABLE and Path(x).exists() and Path(x).stat().st_size <= 20 * 2 ** 20]
    urls = upload([Path(x) for x in ok], _catcher, store) if ok else {}
    products = [dict(x, images=[{"src": urls[str(Path(img["path"]))], "alt": img.get("alt") or x["title"]} for img in x.get("images") or []
                                if str(Path(img.get("path") or "")) in urls]) for x in brand["products"]]
    left = len(paths) - len(urls)
    return dict(brand, products=products, collections=brand.get("collections") or [], policies=brand.get("policies") or {},
                left_out_pictures=left)


def priced(brand: dict, prices: dict) -> dict:
    """handle -> {"price", "compare_at_price", "sample"} (a bare price string is a typed price), on every variant; the product loses
    its dtj-price-needed tag, and a sample price adds dtj-sample-price."""
    from provision.brand_copy import PRICE_TAG  # noqa: PLC0415
    out = []
    for x in brand["products"]:
        if x.get("handle") in prices:
            v = prices[x["handle"]]
            v = v if isinstance(v, dict) else {"price": v}
            tags = x.get("tags") or []
            tags = [t.strip() for t in tags.split(",")] if isinstance(tags, str) else tags
            tags = [t for t in tags if t != PRICE_TAG] + ([SAMPLE_PRICE_TAG] if v.get("sample") and SAMPLE_PRICE_TAG not in tags else [])
            x = dict(x, variants=[dict(var, price=v["price"], compare_at_price=v.get("compare_at_price")) for var in x.get("variants") or []],
                     price_needed=False, tags=tags)
        out.append(x)
    return dict(brand, products=out)


def _copy_plan(brand_link: str, store: str, currency: str | None, out: Path, job: str, brand: dict | None = None,
               prices: dict | None = None) -> dict:
    """Read only: the brand's public catalogue (or, for a Drive folder or samples, the products this laptop holds, their pictures
    sent to Shopify's staged upload), and what the store has through DTJ Store Builder; then the plan is kept on the install
    service for this job (nothing reaches the store until the Approve tap)."""
    from provision import brand_copy  # noqa: PLC0415
    b = brand_copy.read_brand(brand_link) if brand is None else _local_pictures(brand, store)
    if prices:
        b = priced(b, prices)
    plan = brand_copy.make_plan(b, _catcher({"op": "target", "shop": store}), currency)
    if b.get("left_out_pictures"):
        plan["notes"].append(f"{b['left_out_pictures']} pictures left out (not jpg, png, webp or gif, or over 20 MB)")
    out.mkdir(parents=True, exist_ok=True)
    (out / "plan.json").write_text(json.dumps(plan, indent=1, ensure_ascii=False), encoding="utf-8")
    kept = _catcher({"op": "plan", "job": job, "shop": store, "plan": plan})
    if kept.get("refused"):
        plan["notes"].append(f"{len(kept['refused'])} products the install service refused to copy: {', '.join(kept['refused'][:5])}")
    return plan


def _org_apps() -> list[tuple[str, str, str]]:
    """DTJ's original apps: (part, name, client id), from their shopify.app.toml files."""
    sys.path.insert(0, str(ROOT / "services" / "install-catcher" / "tools"))
    from add_client import APPS, ORG_APPS, original_client_id  # noqa: PLC0415
    return [(part, APPS[part][1], original_client_id(ROOT / "services", part)) for part in ORG_APPS]


def _licence(app_key: str, state: str, approved_by: str) -> tuple[int, dict]:
    """The install service's /licence (licence_call.py, signed): status, or switch on with the approver's name."""
    sys.path.insert(0, str(ROOT / "services" / "install-catcher" / "tools"))
    from licence_call import call  # noqa: PLC0415
    try:
        if state == "status":
            return call(app_key, "status")
        return call(app_key, state, approved_by=approved_by, reason="store job: switched on after its install (apps Approve tap)")
    except SystemExit as exc:
        return 0, {"error": str(exc)}


def _add_row(row: dict) -> None:
    """One row into dtj_bot_answers (the open / closed mark of a typed question)."""
    from n8n_mcp import call  # noqa: PLC0415
    from setup_n8n import find_tables  # noqa: PLC0415
    tables = find_tables(call, TABLE)
    if tables:
        call("add_data_table_rows", {"dataTableId": tables[0]["id"], "projectId": tables[0].get("projectId"), "rows": [row]})


def _copy_status(job: str) -> dict:
    return _catcher({"op": "status", "job": job})


def _token() -> str:
    from setup_n8n import user_var  # noqa: PLC0415
    return os.environ.get("DTJ_TELEGRAM_BOT_TOKEN") or user_var("DTJ_TELEGRAM_BOT_TOKEN") or ""


def _sender(token: str) -> Callable[[str, dict], dict]:
    from page_builder.progress import _post  # noqa: PLC0415

    def send(method: str, data: dict) -> dict:
        if not token:
            return {}
        for _ in range(2):  # one retry (CLAUDE.md self-healing)
            status, got = _post(f"https://api.telegram.org/bot{token}/{method}", data)
            if status == 200:
                return got.get("result") or {}
        return {}
    return send


def _rows(job: str) -> list:
    from n8n_mcp import call  # noqa: PLC0415
    from setup_n8n import ERRORS, find_tables, table_rows  # noqa: PLC0415
    try:
        tables = find_tables(call, TABLE)
        return table_rows(call, tables[0], [{"columnName": "job", "condition": "eq", "value": job}]) if tables else []
    except ERRORS:
        return []  # n8n did not answer: the next check tries again


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    st = sub.add_parser("start")
    st.add_argument("--link", required=True)
    st.add_argument("--chat", default="")
    st.add_argument("--by", default="")
    st.add_argument("--minutes", type=float, default=QUESTION_MINUTES)
    asf = sub.add_parser("assets")
    asf.add_argument("--job", required=True)
    asf.add_argument("--file", required=True, type=Path, help='{"products": [{"title", "description", "collection", "pictures": [..]}], '
                                                             '"banners": [..]}')
    pg = sub.add_parser("pages")
    pg.add_argument("--job", required=True)
    pg.add_argument("--file", required=True, type=Path, help='{"pages": [{"handle", "title", "body_html", "template_suffix", "sample"}]}')
    pg.add_argument("--minutes", type=float, default=APPROVE_MINUTES)
    mn = sub.add_parser("menus")
    mn.add_argument("--job", required=True)
    mn.add_argument("--minutes", type=float, default=APPROVE_MINUTES)
    ac = sub.add_parser("activate")
    ac.add_argument("--job", required=True)
    ac.add_argument("--approved-by", required=True, help='"<name> (<where they said yes>)"')
    for name in ("draft", "copy", "apps", "installs", "status"):
        x = sub.add_parser(name)
        x.add_argument("--job", required=True)
        x.add_argument("--minutes", type=float, default=APPROVE_MINUTES)
        if name == "copy":
            x.add_argument("--again", action="store_true", help="a new copy after a finished one (what the store has is skipped)")
    ok = sub.add_parser("approve")
    ok.add_argument("--job", required=True)
    ok.add_argument("--key", required=True, help="ok_<what>, e.g. ok_header, ok_footer, ok_collection")
    ok.add_argument("--text", required=True, help="what will be written, with its preview link")
    ok.add_argument("--minutes", type=float, default=APPROVE_MINUTES)
    sp = sub.add_parser("step")
    sp.add_argument("--job", required=True)
    sp.add_argument("stage", choices=list(STORE_STAGES))
    sp.add_argument("--done", type=int, default=0)
    sp.add_argument("--total", type=int, default=0)
    rc = sub.add_parser("record")
    rc.add_argument("--job", required=True)
    rc.add_argument("--part", required=True)
    rc.add_argument("--preview", required=True)
    rc.add_argument("--code", default="")
    rc.add_argument("--note", default="")
    fi = sub.add_parser("finish")
    fi.add_argument("--job", required=True)
    fi.add_argument("--status", required=True, choices=STATUSES)
    fi.add_argument("--note", default="")
    a = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    from page_builder.progress import PageProgress  # noqa: PLC0415
    token = _token()
    if a.cmd == "start":
        try:
            sc = _scan(a.link)
        except Exception as exc:  # noqa: BLE001 - not a Shopify store, no access, n8n down: the session answers n8n with why
            print(f"stopped: {str(exc)[:400]}")
            return 1
        jid = job_id(sc["myshopify_domain"])
    else:
        jid = a.job
    progress = PageProgress(STATE_DIR / jid / "progress.json", token=token, stages=STORE_STAGES, units=STORE_UNITS)
    access = None
    if a.cmd == "draft":
        from page_builder import theme_target as tt  # noqa: PLC0415
        state = json.loads((STATE_DIR / jid / "job.json").read_text(encoding="utf-8")) if (STATE_DIR / jid / "job.json").exists() else {}
        access = tt.open_access(state.get("shop") or f"{jid}.myshopify.com")
    from provision.actionlog import ActionLog  # noqa: PLC0415
    job = Job(jid, send=_sender(token), rows=_rows, progress=progress, access=access, add_row=_add_row,
              log=ActionLog(STATE_DIR / jid / "action-log.jsonl", jid, automation="store-job"))
    if a.cmd == "start":
        job.begin(sc, a.chat, a.by)
        if a.chat and not progress.s.get("message_id"):
            progress.start(a.chat, f"Designing the store: {sc['name']}")
        return job.plan(a.minutes)
    if a.cmd == "status":
        print(json.dumps({k: job.s.get(k) for k in ("shop", "name", "plan", "draft", "copy_plan", "copy_approved_by", "apps_approved_by",
                                                     "written", "stopped")},
                         indent=1, ensure_ascii=False))
        return 0
    if a.cmd == "draft":
        from page_builder.theme_target import ThemeError  # noqa: PLC0415
        try:
            return job.draft(a.minutes)
        except ThemeError as exc:
            print(f"stopped: {exc}")
            return 1
    if a.cmd == "copy":
        return job.copy(a.minutes, again=getattr(a, "again", False))
    if a.cmd == "assets":
        return job.assets(a.file)
    if a.cmd == "activate":
        return job.activate(a.approved_by, job.handles())
    if a.cmd == "pages":
        return job.pages(a.file, a.minutes)
    if a.cmd == "menus":
        return job.menus(a.minutes)
    if a.cmd == "apps":
        return job.apps(a.minutes)
    if a.cmd == "installs":
        return job.installs(a.minutes)
    if a.cmd == "approve":
        return job.approve(a.key, a.text, a.minutes)
    if a.cmd == "step":
        job.bar(a.stage, a.done, a.total)
        return 0
    if a.cmd == "record":
        return job.record(a.part, a.preview, a.code, a.note)
    return job.finish(a.status, a.note)


if __name__ == "__main__":
    raise SystemExit(main())
