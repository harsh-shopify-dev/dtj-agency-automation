"""DTJ social media automation. Commands:

  Content session (a person at the laptop or VPS, with Claude Code; skill dtj-smm):
    python -m smm store                          open the content store (.work/smm-content) and print its path
    python -m smm new 2026-W44                   a new week: 7 empty daily posts at SMM_POST_TIME (default 19:00 IST)
    python -m smm render 2026-W44                make every picture from its template; fills overlay_text
    python -m smm check 2026-W44                 the gate
    python -m smm deck 2026-W44                  the approval deck (.pptx)
    python -m smm submit 2026-W44                gate + deck + save to the store + send the deck and pictures to Telegram
    python -m smm approve --week 2026-W44 --posts p1-p7 --by "Harsh" [--harsh-unreachable] [--revoke]
    python -m smm status 2026-W44                what is approved, posted, handed over or failed

  Scheduled (GitHub Actions, .github/workflows/smm-daily.yml):
    python -m smm daily [--store content] [--now ISO] [--no-push]
    python -m smm results [--store content] [--report] [--no-push]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path

from . import approve as approve_mod
from .config import IST, load as load_config
from .daily import Daily
from .deck import build as build_deck
from .gate import check_week, history_of
from .notify import Telegram
from .render import render
from .results import last_week, pull, report
from .store import Store, open_local
from .week import load, publish_time


def _store(arg: str | None) -> Store:
    return Store(arg) if arg else open_local()


def cmd_new(store: Store, week: str) -> int:
    folder = store.week_folder(week)
    if (folder / "week.json").exists():
        print(f"{week} already exists: {folder}")
        return 1
    hh, mm = (os.environ.get("SMM_POST_TIME") or "19:00").split(":")
    monday = date.fromisocalendar(int(week[:4]), int(week[6:]), 1)
    posts = []
    for i in range(7):
        when = datetime.combine(monday + timedelta(days=i), time(int(hh), int(mm)), IST)
        posts.append({"id": f"{week}-p{i + 1}", "publish_at": when.strftime("%Y-%m-%dT%H:%M:00+05:30"), "theme": "tip",
                      "format": "image", "proof_ids": [], "media": [{"file": f"media/p{i + 1}.jpg", "alt": "TODO describe the picture"}],
                      "render": [{"file": f"media/p{i + 1}.jpg", "template": "pain", "fields": {"headline": "TODO"}}],
                      "platforms": {"instagram": {"caption": "TODO", "hashtags": []}, "facebook": {"caption": "TODO {link}"},
                                    "linkedin": {"caption": "TODO {link}"}, "x": {"text": "TODO {link}"}}})
    (folder / "media").mkdir(parents=True, exist_ok=True)
    (folder / "week.json").write_text(json.dumps({"week": week, "made_by": "", "research": [], "posts": posts}, indent=1,
                                                 ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"New week: {folder / 'week.json'}")
    return 0


def cmd_render(store: Store, week: str) -> int:
    path = store.week_folder(week) / "week.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    specs = [dict(r, file=r["file"].removeprefix("media/")) for p in data["posts"] for r in p.get("render", [])]
    words = render(specs, store.week_folder(week) / "media")
    for p in data["posts"]:
        if p.get("render"):
            p["overlay_text"] = [w for r in p["render"] for w in words[r["file"].removeprefix("media/")]]
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Rendered {len(specs)} pictures into {store.week_folder(week) / 'media'}")
    return 0


def cmd_check(store: Store, week: str, now: datetime | None = None) -> dict:
    wk = load(store.week_folder(week))
    result = check_week(wk, history_of(store.weeks, week), now=now)
    for pid, problems in result.items():
        print(f"{pid}: {'PASS' if not problems else 'BLOCKED'}")
        for p in problems:
            print(f"   - {p}")
    print(f"\n{sum(1 for v in result.values() if not v)} of {len(result)} posts pass.")
    return result


def cmd_submit(store: Store, week: str) -> int:
    result = cmd_check(store, week, now=datetime.now(IST))
    if any(result.values()):
        print("Fix the blocked posts first (or drop them from week.json); nothing was sent.")
        return 1
    wk = load(store.week_folder(week))
    deck = build_deck(wk, store.week_folder(week) / f"DTJ-social-{week}.pptx", store.weeks)
    store.save(f"SMM {week}: posts for approval")
    cfg = load_config()
    tg = Telegram(os.environ, cfg.telegram_chat_id)
    posts = sorted(wk.posts, key=publish_time)
    tg.text(f"DTJ social posts for approval: {week}, {len(posts)} posts, "
            f"{publish_time(posts[0]):%a %d %b} to {publish_time(posts[-1]):%a %d %b}. The deck and each picture follow.\n"
            "Reply 'yes' with the post numbers (e.g. 'yes p1-p7'), or say what to change.")
    tg.files([deck])
    for p in posts:
        first = next(iter(p["platforms"].values()))
        words = first.get("caption") or first.get("text") or first.get("title", "")
        tg.files([wk.media_path(m) for m in p["media"]] or [], f"{p['id'].split('-')[-1]} · {publish_time(p):%a %d %b %H:%M} · "
                 f"{', '.join(sorted(p['platforms']))}\n\n{words.replace('{link}', '[audit link]')}")
    print(f"Sent for approval. Deck: {deck}")
    return 0


def cmd_status(store: Store, week: str) -> int:
    wk = load(store.week_folder(week))
    for p in sorted(wk.posts, key=publish_time):
        a = store.read(store.path(week, "approvals", p["id"]))
        state = "not approved" if not a else ("approval withdrawn" if a.get("revoked") else f"approved by {a['approved_by']}")
        if a and not a.get("revoked") and a["fingerprint"] != wk.fingerprint(p):
            state += " (CHANGED since: needs a new yes)"
        print(f"{p['id']}  {publish_time(p):%a %d %b %H:%M}  {state}")
        for pl in sorted(p["platforms"]):
            for kind, word in (("published", "posted"), ("handed", "sent for posting by hand"), ("failures", "failed")):
                rec = store.read(store.path(week, kind, p["id"], pl))
                if rec:
                    extra = rec.get("url") or rec.get("reason") or f"{rec.get('count')} tries"
                    print(f"     {pl}: {word} {extra}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m smm", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("store", "new", "render", "check", "deck", "submit", "status"):
        sp = sub.add_parser(name)
        if name != "store":
            sp.add_argument("week")
        sp.add_argument("--store")
    sp = sub.add_parser("approve")
    sp.add_argument("--week", required=True)
    sp.add_argument("--posts", required=True)
    sp.add_argument("--by", required=True)
    sp.add_argument("--harsh-unreachable", action="store_true")
    sp.add_argument("--revoke", action="store_true")
    sp.add_argument("--store")
    sp.add_argument("--no-push", action="store_true")
    for name in ("daily", "results"):
        sp = sub.add_parser(name)
        sp.add_argument("--store")
        sp.add_argument("--now")
        sp.add_argument("--no-push", action="store_true")
        if name == "results":
            sp.add_argument("--report", action="store_true", help="also write and send last week's report")
    args = ap.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")
    store = _store(args.store)

    if args.cmd == "store":
        print(store.root)
        return 0
    if args.cmd == "new":
        return cmd_new(store, args.week)
    if args.cmd == "render":
        return cmd_render(store, args.week)
    if args.cmd == "check":
        return 1 if any(cmd_check(store, args.week).values()) else 0
    if args.cmd == "deck":
        print(build_deck(load(store.week_folder(args.week)), store.week_folder(args.week) / f"DTJ-social-{args.week}.pptx", store.weeks))
        return 0
    if args.cmd == "submit":
        return cmd_submit(store, args.week)
    if args.cmd == "status":
        return cmd_status(store, args.week)
    if args.cmd == "approve":
        try:
            lines = approve_mod.approve(store, args.week, args.posts, args.by, args.harsh_unreachable, args.revoke)
        except approve_mod.ApprovalError as e:
            print(f"NOT APPROVED: {e}")
            return 1
        print("\n".join(lines))
        store.save(f"SMM {args.week}: {'withdrawn' if args.revoke else 'approved'} {args.posts} by {args.by}", push=not args.no_push)
        return 0
    now = datetime.fromisoformat(args.now) if args.now else datetime.now(IST)
    if args.cmd == "daily":
        code = Daily(load_config(), store, os.environ).run(now)
        store.save(f"SMM daily run {now:%Y-%m-%d %H:%M}", push=not args.no_push)
        return code
    if args.cmd == "results":
        print(f"Pulled {pull(store, os.environ, now=now)} results.")
        if args.report:
            week = last_week(now)
            text = report(store, week)
            store.write(store.root / "reports" / f"{week}.json", {"week": week, "text": text})
            (store.root / "reports" / f"{week}.md").write_text(text + "\n", encoding="utf-8")
            Telegram(os.environ, load_config().telegram_chat_id).text(text)
        store.save(f"SMM results {now:%Y-%m-%d}", push=not args.no_push)
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
