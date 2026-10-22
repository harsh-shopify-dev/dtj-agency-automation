"""The store job: a whole store from the one link a person sends the DTJ bot (Harsh, 21 Oct 2026: "i just share the brand store link
and it starts designing the store and it asks the specific questions it needs along with the app installation"). The laptop side of
n8n's "Store Factory: New Store"; the runbook is the skill dtj-new-store.

    python n8n/store-factory/store_job.py start --link https://store.myshopify.com --chat <telegram id> --by "<name>"
        read the store and ask the questions in Telegram (the brand's link, whose store, the client's name, what to design, which
        products, an offer)
    python n8n/store-factory/store_job.py draft --job <job>       Approve tap, then the live theme duplicated as an UNPUBLISHED copy
    python n8n/store-factory/store_job.py copy --job <job>        the brand's products, collections and empty policy pages: a read-only
                                                                   plan kept on the install service, an Approve tap (it starts n8n's
                                                                   Store Factory: Brand Copy, which does the writes), then it waits
    python n8n/store-factory/store_job.py apps --job <job>        Approve tap for the app copies; prints the add_shop.py command
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
PARTS = {"chrome": "Header and footer", "home": "Home page", "collection": "Collection page", "products": "Product pages"}
FULL, PRODUCTS_ONLY = ("chrome", "home", "collection", "products"), ("products",)
STORE_STAGES = {
    "questions": ("Your answers", 0, 8),
    "draft": ("The draft copy of the theme", 8, 12),
    "copy": ("Copying the brand's products and collections", 12, 25),
    "apps": ("The DTJ apps: made, released, installed", 25, 38),
    "intake": ("Collecting the brand's pictures and details", 38, 45),
    "chrome": ("Header and footer", 45, 53),
    "home": ("Home page", 53, 63),
    "collection": ("Collection page", 63, 70),
    "products": ("Product pages", 70, 98),
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
                 copy_status=None, add_row=None):
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
        # the brand comes first (Harsh, 21 Oct 2026: "it didnt asked me the brand link it has to create the shopify store of it"):
        # the link sent is the store to build in; the brand's own store is where the products, collections and policies come from
        got = a.choose("brand_src", intro + "\n\nWhich brand should I build in this store?",
                       [("I'll send the brand's link", "send"), ("This store is the brand", "self"), ("Wrong store: stop", "stop")],
                       minutes)
        if not got:
            return WAITING
        if got["value"] == "stop":
            return self.stop("the person said it is the wrong store")
        if got["value"] == "send" and not s.get("brand"):
            link = a.type_in("brand_link", "Send the brand's website link: its own Shopify store, for example https://brand.com",
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
                   + ("Its website is not a Shopify store" + (" and shows no prices, so its products are copied as hidden drafts: you "
                      "set each price in Shopify before they show. " if br.get("prices", 0) < br["product_count"] else ". ") if website else "")
                   + f"Nothing is copied into {esc(sc['name'])} before your Approve tap.")
        elif got["value"] == "self":
            s["brand"] = sc
        br = s["brand"]
        p["brand"] = {"link": br["base"], "name": br["name"], "store": br["myshopify_domain"], "currency": br.get("currency"),
                      "product_count": br["product_count"]}
        p["copy"] = br["myshopify_domain"] != sc["myshopify_domain"]
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
        if "products" in p["parts"]:
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
        products = "; ".join(x["title"] for x in p.get("products", [])) or "none"
        copying = f"Copy <b>{esc(br['name'])}</b> into it, then design: " if p["copy"] else ""
        a.tell(f"Plan for <b>{esc(s['name'])}</b>: {copying}{esc(', '.join(PARTS[x] for x in p['parts']))}. Product pages: "
               f"{esc(products)}. Offer: {esc(p['offer'] or 'none')}.\nBefore anything is made or written I send an Approve button: "
               "the draft copy, " + ("the brand copy, " if p["copy"] else "") + "the app copies, the header and footer, the collection "
               "page. Product and home pages go to the draft without one (Harsh's standing rule). Nothing is published.")
        self.out(json.dumps({"job": self.job, "plan": p}, ensure_ascii=False))
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
    def copy(self, minutes: float = APPROVE_MINUTES) -> int:
        """A read-only plan through the install service (DTJ Store Builder), kept there for this job; its Approve tap, which itself
        starts "Store Factory: Brand Copy" in n8n; then waits until the install service says the copy is finished."""
        self.need_plan()
        s, p = self.s, self.s["plan"]
        if not p.get("copy"):
            self.out("nothing to copy: this store is the brand")
            return 0
        if s.get("copy_result"):
            self.out(json.dumps(s["copy_result"]))
            return 0
        self.bar("copy")
        end = self.ask.clock() + minutes * 60
        while not s.get("copy_plan"):
            try:
                plan = self.planner(p["brand"]["link"], s["shop"], p["brand"].get("currency"), self.dir / "copy", job=self.job)
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
        ok, by = self.ask.approve("ok_copy", f"Copy <b>{esc(p['brand']['name'])}</b> into <b>{esc(s['name'])}</b>: {esc(cp['summary'])}. "
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
            what = (f"Connect DTJ's own apps to <b>{esc(s['name'])}</b>: register the store with DTJ's install service and update that "
                    "service (DTJ's original apps must be installed on the store by a person).")
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
        if self.progress:
            self.progress.finish(status == "done", f"{self.s.get('name', '')}: {status}" + (f". {note[:200]}" if note else ""))
        self.out(f"answer for n8n: {self.dir / 'answer.json'}")
        return 0


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


def _catcher(body: dict, opener=urllib.request.urlopen) -> dict:
    """One signed call to the install service's POST /copy (DTJ_CATCHER_CONTROL_KEY, as licence_call.py signs /licence)."""
    sys.path.insert(0, str(ROOT / "services" / "install-catcher" / "tools"))
    from deploy import read_var  # noqa: PLC0415
    key = read_var("DTJ_CATCHER_CONTROL_KEY")
    if not key:
        raise CatcherError("DTJ_CATCHER_CONTROL_KEY is not set on this laptop (vault.py pull)")
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
        if exc.code == 404 and "not installed" in why:
            raise NotInstalled(why) from exc
        raise CatcherError(f"the install service said {exc.code}: {why or 'no reason given'}") from exc


def _copy_plan(brand_link: str, store: str, currency: str | None, out: Path, job: str) -> dict:
    """Read only: the brand's public catalogue, and what the store has through DTJ Store Builder; then the plan is kept on the
    install service for this job (nothing reaches the store until the Approve tap)."""
    from provision import brand_copy  # noqa: PLC0415
    plan = brand_copy.make_plan(brand_copy.read_brand(brand_link), _catcher({"op": "target", "shop": store}), currency)
    out.mkdir(parents=True, exist_ok=True)
    (out / "plan.json").write_text(json.dumps(plan, indent=1, ensure_ascii=False), encoding="utf-8")
    kept = _catcher({"op": "plan", "job": job, "shop": store, "plan": plan})
    if kept.get("refused"):
        plan["notes"].append(f"{len(kept['refused'])} products the install service refused to copy: {', '.join(kept['refused'][:5])}")
    return plan


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
    for name in ("draft", "copy", "apps", "status"):
        x = sub.add_parser(name)
        x.add_argument("--job", required=True)
        x.add_argument("--minutes", type=float, default=APPROVE_MINUTES)
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
        return job.copy(a.minutes)
    if a.cmd == "apps":
        return job.apps(a.minutes)
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
