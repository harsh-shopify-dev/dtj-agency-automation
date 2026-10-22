"""Ask a person in Telegram and wait for the answer: the questions and Approve buttons of a laptop job (the store job, 21 Oct 2026).

The laptop sends each question itself (the bot's token from DTJ_TELEGRAM_BOT_TOKEN). The tap or the typed reply reaches the bot's
n8n workflow, which saves it in the data table dtj_bot_answers (job, key, value, choice, by, chat_id, at); the laptop reads that table
through n8n's MCP server. A button carries the callback data "a:<job>:<key>:<n>" (Telegram allows 64 bytes); a typed answer is a
reply to the question, whose last line is "(job <job>, answer <key>)", or (22 Oct 2026, Harsh sent the brand link as a plain
message) any plain message in that chat while a typed question is open: the laptop marks it open and closed in the same table (rows
with an empty value and choice "open" / "closed"), and the bot's "Load Open Questions" reads those marks. The Approve buttons are a question with two choices: the tap
of an active person on the bot, with their name, is the yes for that one action (Harsh, 21 Oct 2026: "Approve button in Telegram").
Only answers from the job's own chat count. Nothing here prints or stores the bot's token.
"""
from __future__ import annotations

import re
import time
from datetime import datetime, timedelta, timezone
from typing import Callable

TABLE = "dtj_bot_answers"
JOB_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,23}$")
KEY_RE = re.compile(r"^[a-z0-9_]{1,20}$")
POLL_SECONDS = 15
SKEW_SECONDS = 120  # the bot stamps an answer with n8n's clock, the question carries this laptop's: allow them to differ a little
APPROVE, SKIP = ("Approve", "yes"), ("Skip", "no")

Send = Callable[[str, dict], dict]          # (Telegram method, data) -> the result's "result" ({} when it failed)
Rows = Callable[[str], list]                # job -> its rows in dtj_bot_answers


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _earlier(stamp: str, seconds: int) -> str:
    try:
        return (datetime.strptime(stamp[:19], "%Y-%m-%dT%H:%M:%S") - timedelta(seconds=seconds)).strftime("%Y-%m-%dT%H:%M:%S")
    except ValueError:
        return ""


class Asker:
    """`state` is the caller's saved job state (a dict it writes to disk with `save`): which questions were sent and their answers,
    so a job that stops and starts again never asks twice and keeps what was answered."""

    def __init__(self, job: str, chat: str, *, send: Send, rows: Rows, state: dict, save: Callable[[], None],
                 sleep=time.sleep, clock=time.monotonic, poll: float = POLL_SECONDS, now: Callable[[], str] = utc_now,
                 add_row: Callable[[dict], None] | None = None):
        if not JOB_RE.fullmatch(job):
            raise ValueError(f"job {job!r}: lowercase letters, digits and dashes, at most 24")
        self.job, self.chat = job, str(chat or "")
        self.send, self.rows, self.state, self.save = send, rows, state, save
        self.sleep, self.clock, self.poll, self.now, self.add_row = sleep, clock, poll, now, add_row
        self.state.setdefault("asked", {})
        self.state.setdefault("answers", {})

    # ---- sending
    def _message(self, text: str, markup: dict | None = None) -> str:
        data = {"chat_id": self.chat, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}
        if markup:
            data["reply_markup"] = markup
        got = self.send("sendMessage", data) if self.chat else {}
        return str((got or {}).get("message_id") or "")

    def ask(self, key: str, text: str, options: list[tuple[str, str]]) -> None:
        """Buttons, one per row: (label, value). Sent once per key."""
        if not KEY_RE.fullmatch(key):
            raise ValueError(f"question key {key!r}: lowercase letters, digits and _, at most 20")
        if key in self.state["asked"]:
            return
        rows = [[{"text": label[:60], "callback_data": f"a:{self.job}:{key}:{i}"}] for i, (label, _v) in enumerate(options)]
        mid = self._message(text, {"inline_keyboard": rows})
        self.state["asked"][key] = {"options": [list(o) for o in options], "message_id": mid, "typed": False, "at": self.now()}
        self.save()

    def ask_text(self, key: str, text: str, placeholder: str = "") -> None:
        """Telegram's reply box; the answer is the text of the reply."""
        if not KEY_RE.fullmatch(key):
            raise ValueError(f"question key {key!r}: lowercase letters, digits and _, at most 20")
        if key in self.state["asked"] and self.state["asked"][key].get("typed"):
            return
        markup = {"force_reply": True, "input_field_placeholder": placeholder[:60]} if placeholder else {"force_reply": True}
        mid = self._message(f"{text}\n\n(job {self.job}, answer {key})", markup)
        self.state["asked"][key] = {"options": [], "message_id": mid, "typed": True, "at": self.now()}
        self.save()
        self._mark(key, "open")

    def _mark(self, key: str, choice: str) -> None:
        """The open / closed mark the bot reads, so a plain message in this chat answers the open typed question."""
        if self.add_row and self.chat:
            try:
                self.add_row({"job": self.job, "key": key, "value": "", "choice": choice, "by": "", "chat_id": self.chat, "at": self.now()})
            except Exception:  # noqa: BLE001 - without the mark only a reply to the question counts, as before
                pass

    def forget(self, key: str) -> int:
        """Ask this question again from the start (its answer could not be used). That answer never counts again, even when it is
        newer than the new question by the clock allowance; returns how many answers to this question were refused so far."""
        old = self.state["answers"].pop(key, None)
        spent = self.state.setdefault("spent", {}).setdefault(key, [])
        if old:
            spent.append(str(old.get("row") or ""))
        self.state["asked"].pop(key, None)
        self.save()
        return len(spent)

    def tell(self, text: str) -> None:
        self._message(text)

    # ---- reading
    def answer(self, key: str) -> dict | None:
        """{"value", "label", "by"} once answered (the last answer counts), else None."""
        if key in self.state["answers"]:
            return self.state["answers"][key]
        asked = self.state["asked"].get(key)
        if not asked:
            return None
        # only answers given after the question was sent count: an earlier run for the same store left its taps in the table
        since = _earlier(asked["at"], SKEW_SECONDS) if asked.get("at") else ""
        spent = set(self.state.get("spent", {}).get(key, []))
        mine = [r for r in self.rows(self.job) if str(r.get("key")) == key and str(r.get("chat_id", "")) == self.chat
                and str(r.get("at") or "")[:19] >= since and str(r.get("id") or "") not in spent and str(r.get("value") or "").strip()]
        if not mine:
            return None
        last = sorted(mine, key=lambda r: (str(r.get("at") or ""), int(r.get("id") or 0)))[-1]
        label, value = str(last.get("value") or "").strip(), None
        if asked["typed"]:
            value = label
        else:
            choice = str(last.get("choice") or "")
            if choice.isdigit() and int(choice) < len(asked["options"]):
                label, value = asked["options"][int(choice)]
        if value is None or value == "":
            return None
        got = {"value": value, "label": label, "by": str(last.get("by") or "").strip() or "someone on the DTJ bot", "row": str(last.get("id") or "")}
        self.state["answers"][key] = got
        self.save()
        if asked["typed"]:
            self._mark(key, "closed")
        return got

    def wait(self, key: str, minutes: float) -> dict | None:
        end = self.clock() + minutes * 60
        while True:
            got = self.answer(key)
            if got or self.clock() >= end:
                return got
            self.sleep(self.poll)

    def choose(self, key: str, text: str, options: list[tuple[str, str]], minutes: float) -> dict | None:
        self.ask(key, text, options)
        return self.wait(key, minutes)

    def type_in(self, key: str, text: str, minutes: float, placeholder: str = "") -> dict | None:
        self.ask_text(key, text, placeholder)
        return self.wait(key, minutes)

    def approve(self, key: str, text: str, minutes: float) -> tuple[bool | None, str]:
        """(True, who) approved, (False, who) skipped, (None, "") no tap yet. The tap is the yes for this one action only."""
        got = self.choose(key, text + "\n\nApprove = yes for exactly this. Skip = leave it undone.", [APPROVE, SKIP], minutes)
        if not got:
            return None, ""
        return got["value"] == "yes", got["by"]
