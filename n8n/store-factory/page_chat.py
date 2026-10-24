"""Talk about a finished page in Telegram, both ways.

Harsh, 24 Oct 2026: "cant i just share the message there regarding the changes and you update it from telegram so once we build the
page i can also chat with you there". Every message about a page ends with the line "(job page-<brief>, answer chat)". A person's
reply to one is saved in dtj_bot_answers by the bot's typed-answer route; the VPS worker (worker.py, look_at_chats) hands it to that
page's own Claude session, which answers with:

    python n8n/store-factory/page_chat.py --brief 12 --chat 7051933055 --say "<what changed, in plain words, and the preview link>"

Plain text (no HTML). The bot token comes from DTJ_TELEGRAM_BOT_TOKEN only and is never printed. Exit 0 = sent, 1 = not sent.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TAIL = "\n\nReply to this message to change something on the page.\n(job page-{brief}, answer chat)"
MAX_TEXT = 3500  # Telegram's limit is 4096 characters; the tail and some room stay free


def text_for(brief: str, say: str) -> str:
    return re.sub(r"\s+$", "", say or "")[:MAX_TEXT] + TAIL.format(brief=brief)


def _post(url: str, data: dict):
    sys.path.insert(0, str(ROOT / "services" / "store-builder"))
    from page_builder.progress import _post as post  # noqa: PLC0415 - the same Telegram call the progress bar uses
    return post(url, data)


def send(chat: str, brief: str, say: str, token: str | None = None, post=_post) -> bool:
    token = token if token is not None else os.environ.get("DTJ_TELEGRAM_BOT_TOKEN", "")
    if not (token and re.fullmatch(r"-?\d{3,20}", str(chat or "")) and re.fullmatch(r"\d{1,9}", str(brief or ""))):
        return False
    status, _answer = post(f"https://api.telegram.org/bot{token}/sendMessage",
                           {"chat_id": str(chat), "text": text_for(str(brief), say), "disable_web_page_preview": False})
    return status == 200


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--brief", required=True, help="the page's brief number (dtj_client_intake row)")
    ap.add_argument("--chat", required=True, help="the Telegram chat the message came from")
    ap.add_argument("--say", required=True, help="the message, in plain words")
    a = ap.parse_args(argv)
    ok = send(a.chat, a.brief, a.say)
    print("sent" if ok else "not sent (no DTJ_TELEGRAM_BOT_TOKEN, a wrong chat or brief, or Telegram refused it)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
