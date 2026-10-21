"""The store job: a whole store from the one link a person sends the DTJ bot (Harsh, 21 Oct 2026: "i just share the brand store link
and it starts designing the store and it asks the specific questions it needs along with the app installation"). The laptop side of
n8n's "Store Factory: New Store"; the runbook is the skill dtj-new-store.

    python n8n/store-factory/store_job.py start --link https://brand.com --chat <telegram id> --by "<name>"
        read the store and ask the questions in Telegram (whose store, the client's name, what to design, which products, an offer)
    python n8n/store-factory/store_job.py draft --job <job>       Approve tap, then the live theme duplicated as an UNPUBLISHED copy
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
import html
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "services" / "store-builder"))
from bot_ask import TABLE, Asker  # noqa: E402

STATE_DIR = ROOT / ".work" / "stores"
WAITING, SKIPPED = 3, 4
QUESTION_MINUTES = 60   # each question waits this long, then the job says "waiting" (exit 3) and a rerun keeps waiting
APPROVE_MINUTES = 120
PARTS = {"chrome": "Header and footer", "home": "Home page", "collection": "Collection page", "products": "Product pages"}
FULL, PRODUCTS_ONLY = ("chrome", "home", "collection", "products"), ("products",)
STORE_STAGES = {
    "questions": ("Your answers", 0, 8),
    "draft": ("The draft copy of the theme", 8, 12),
    "apps": ("The DTJ apps: made, released, installed", 12, 35),
    "intake": ("Collecting the brand's pictures and details", 35, 45),
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


def match_products(lines: list[str], sellers: list[dict]) -> tuple[list[dict], list[str]]:
    """Typed product links or names -> the store's products (by the handle in a link, else a name that contains the words)."""
    picked, unknown = [], []
    for line in (ln.strip() for ln in lines):
        if not line:
            continue
        m = re.search(r"/products/([a-z0-9][a-z0-9-]*)", line, re.I)
        hit = None
        if m:
            hit = next((p for p in sellers if p["handle"] == m.group(1).lower()), None)
        else:
            words = [w for w in re.findall(r"[a-z0-9]+", line.lower()) if len(w) > 1]
            hits = [p for p in sellers if words and all(w in p["title"].lower() for w in words)]
            hit = hits[0] if len(hits) == 1 else None
        if hit and hit not in picked:
            picked.append(hit)
        elif not hit:
            unknown.append(line[:80])
    return picked, unknown


class Job:
    def __init__(self, job: str, *, send: Callable[[str, dict], dict], rows: Callable[[str], list], progress=None, access=None,
                 log=None, state_dir: Path = STATE_DIR, out=print, sleep=time.sleep, clock=time.monotonic,
                 today: Callable[[], str] = lambda: datetime.now(timezone.utc).strftime("%d %b %Y")):
        self.job, self.dir = job, state_dir / job
        self.path = self.dir / "job.json"
        self.s = json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else {}
        self.out, self.progress, self.access, self.log, self.today = out, progress, access, log, today
        self.ask = Asker(job, self.s.get("chat", ""), send=send, rows=rows, state=self.s, save=self.save, sleep=sleep, clock=clock)

    def save(self) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.s, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    def bar(self, stage: str, done: int = 0, total: int = 0) -> None:
        if self.progress:
            self.progress.step(stage, done, total)

    def logged(self, action: str, reason: str, by: str, result: str = "success", **extra) -> None:
        if self.log:
            self.log.record(tier=2, mode="approve", target=self.s.get("shop", self.job), action=action, reason=reason, result=result,
                            approver=by, **extra)

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
        got = a.choose("whose", intro + "\n\nWhose store is it?",
                       [("A client's store", "client"), ("DTJ's own store", "dtj"), ("Wrong store: stop", "stop")], minutes)
        if not got:
            return WAITING
        if got["value"] == "stop":
            return self.stop("the person said it is the wrong store")
        p["whose"] = got["value"]
        if p["whose"] == "client":
            got = a.choose("label", f"The client's name for the app names: <b>{esc(sc['name'])}</b>?",
                           [(f"Use \"{sc['name'][:40]}\"", "use"), ("I'll type it", "type")], minutes)
            if not got:
                return WAITING
            if got["value"] == "type":
                got = a.type_in("label_typed", "Send the client's name, as it should appear in the app names.", minutes, "Royal Dosa")
                if not got:
                    return WAITING
                p["label"] = re.sub(r"\s+", " ", got["value"]).strip()[:40]
            else:
                p["label"] = sc["name"][:40]
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
            sellers = sc["best_sellers"]
            top = "\n".join(f"{i}. {esc(x['title'])}" for i, x in enumerate(sellers[:5], 1))
            got = a.choose("products", f"Which product pages? Best sellers first ({esc(sc['best_sellers_from'])}):\n{top}",
                           [(lbl, v) for lbl, v in product_choices(len(sellers))], minutes)
            if not got:
                return WAITING
            if got["value"] == "pick":
                got = a.type_in("products_typed", "Send the product links (from the store's website) or exact names, one per line.",
                                minutes, "https://brand.com/products/...")
                if not got:
                    return WAITING
                picked, unknown = match_products(got["value"].splitlines(), sellers)
                if unknown:
                    a.tell("Not found in the store, left out: " + "; ".join(esc(u) for u in unknown))
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
        self.save()
        products = "; ".join(x["title"] for x in p.get("products", [])) or "none"
        a.tell(f"Plan for <b>{esc(s['name'])}</b>: {esc(', '.join(PARTS[x] for x in p['parts']))}. Product pages: {esc(products)}. "
               f"Offer: {esc(p['offer'] or 'none')}.\nBefore anything is made or written I send an Approve button: the draft copy, "
               "the app copies, the header and footer, the collection page. Product and home pages go to the draft without one "
               "(Harsh's standing rule). Nothing is published.")
        self.out(json.dumps({"job": self.job, "plan": p}, ensure_ascii=False))
        return 0

    def stop(self, why: str) -> int:
        self.s["stopped"] = why
        self.save()
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
            self.logged("draft copy of the live theme", "skipped in Telegram", by, result="skipped")
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
            self.logged("DTJ apps for the store", "skipped in Telegram", by, result="skipped")
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
        self.logged(f"approval {key}", "a write that needs a person's yes", by, result="approved" if ok else "skipped",
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
    for name in ("draft", "apps", "status"):
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
        from page_builder.store_scan import NotShopify, scan  # noqa: PLC0415
        try:
            sc = scan(a.link)
        except NotShopify as exc:
            print(f"stopped: {exc}")
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
    job = Job(jid, send=_sender(token), rows=_rows, progress=progress, access=access,
              log=ActionLog(STATE_DIR / jid / "action-log.jsonl", jid, automation="store-job"))
    if a.cmd == "start":
        job.begin(sc, a.chat, a.by)
        if a.chat and not progress.s.get("message_id"):
            progress.start(a.chat, f"Designing the store: {sc['name']}")
        return job.plan(a.minutes)
    if a.cmd == "status":
        print(json.dumps({k: job.s.get(k) for k in ("shop", "name", "plan", "draft", "apps_approved_by", "written", "stopped")},
                         indent=1, ensure_ascii=False))
        return 0
    if a.cmd == "draft":
        from page_builder.theme_target import ThemeError  # noqa: PLC0415
        try:
            return job.draft(a.minutes)
        except ThemeError as exc:
            print(f"stopped: {exc}")
            return 1
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
