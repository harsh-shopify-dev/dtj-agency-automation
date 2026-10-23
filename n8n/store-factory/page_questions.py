"""A product page's own questions in Telegram, the same as a whole store's (Harsh, 23 Oct 2026: "here it should also show ChatGPT
generates and that competitor flow message follow ups"). The page's Claude session asks them after the Start tap
(n8n/store-factory/request_page_design.js, step 2b):

    python n8n/store-factory/page_questions.py --brief 9 --chat 7051933055
        1. Should ChatGPT make new pictures for this page (from the product's own photos)?
        2. Study competitor websites first? Your links / find them yourself / no
        3. What should the study focus on? Everything / one by one / only what I type, then anything specific (typed)
        prints one JSON line: {"pictures": "make" | "none", "pictures_by": "<who tapped>", "competitors": {"how", "links", "focus",
        "note"}}. Exit 0 = answered, 3 = waiting for the person (run it again: it never asks twice).
    python n8n/store-factory/page_questions.py --brief 9 --study <study.md>
        the competitor study the session wrote (one heading per focus, and "Your request"): kept and its short form sent to Telegram.

The answers live in .work/pages/brief-<n>/job.json (no secret in it). The "make pictures" tap is the person's yes for making those
pictures and putting them on this page's draft (store Files), named in the action log.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import store_job  # noqa: E402

STATE_DIR = store_job.ROOT / ".work" / "pages"
PICTURES = [("Yes: make them and add them to the page", "make"), ("No: the product's own pictures", "none")]


def page_job(brief: str, chat: str, **kw) -> store_job.Job:
    """A store job used only for its Telegram questions (job id p<brief>: its buttons carry it)."""
    j = store_job.Job(f"p{brief}"[:24], send=kw.pop("send", None) or store_job._sender(store_job._token()),
                      rows=kw.pop("rows", None) or store_job._rows, state_dir=kw.pop("state_dir", STATE_DIR),
                      add_row=kw.pop("add_row", store_job._add_row), **kw)
    if not j.s.get("job"):
        j.s.update(job=j.job, name=f"brief {brief}", chat=str(chat or ""), plan={}, planned=True, shop="")
        j.save()
    j.ask.chat = j.s["chat"]
    return j


def ask(j: store_job.Job, minutes: float) -> int:
    p, a = j.s["plan"], j.ask
    got = a.choose("pictures", "Should ChatGPT make new pictures for this page? They are made from the product's own photos (the "
                               "product stays exactly as it is), marked as samples, and put on the draft page only.", PICTURES, minutes)
    if not got:
        return store_job.WAITING
    p["pictures"], p["pictures_by"] = got["value"], got.get("by", "")
    waiting = j.study_questions(minutes)
    if waiting is not None:
        return waiting
    j.save()
    j.ask.tell("Thanks, that is all I need. " + ("ChatGPT makes the pictures after the study. " if p["pictures"] == "make" else "")
               + "The progress bar above keeps moving; the preview link comes here when the page is in the draft.")
    j.out(json.dumps({"pictures": p["pictures"], "pictures_by": p["pictures_by"], "competitors": p.get("competitors") or {}},
                     ensure_ascii=False))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--brief", required=True)
    ap.add_argument("--chat", default="")
    ap.add_argument("--minutes", type=float, default=store_job.QUESTION_MINUTES)
    ap.add_argument("--study", type=Path, help="send the competitor study the session wrote")
    a = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if not str(a.brief).isdigit():
        raise SystemExit("--brief is the brief's row id (a number)")
    j = page_job(a.brief, a.chat)
    if a.study:
        return j.study(a.study)
    return ask(j, a.minutes)


if __name__ == "__main__":
    raise SystemExit(main())
