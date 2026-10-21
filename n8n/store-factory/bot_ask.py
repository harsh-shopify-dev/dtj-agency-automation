"""Ask a person in Telegram and wait for the answer: the questions and Approve buttons of a laptop job (the store job, 21 Oct 2026).

The laptop sends each question itself (the bot's token from DTJ_TELEGRAM_BOT_TOKEN). The tap or the typed reply reaches the bot's
n8n workflow, which saves it in the data table dtj_bot_answers (job, key, value, choice, by, chat_id, at); the laptop reads that table
through n8n's MCP server. A button carries the callback data "a:<job>:<key>:<n>" (Telegram allows 64 bytes); a typed answer is a
reply to the question, whose last line is "(job <job>, answer <key>)". The Approve buttons are a question with two choices: the tap
of an active person on the bot, with their name, is the yes for that one action (Harsh, 21 Oct 2026: "Approve button in Telegram").
Only answers from the job's own chat count. Nothing here prints or stores the bot's token.
"""
from __future__ import annotations

import re
import time
from typing import Callable

TABLE = "dtj_bot_answers"
JOB_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,23}$")
KEY_RE = re.compile(r"^[a-z0-9_]{1,20}$")
POLL_SECONDS = 15
APPROVE, SKIP = ("Approve", "yes"), ("Skip", "no")

Send = Callable[[str, dict], dict]          # (Telegram method, data) -> the result's "result" ({} when it failed)
Rows = Callable[[str], list]                # job -> its rows in dtj_bot_answers


class Asker:
    """`state` is the caller's saved job state (a dict it writes to disk with `save`): which questions were sent and their answers,
    so a job that stops and starts again never asks twice and keeps what was answered."""

    def __init__(self, job: str, chat: str, *, send: Send, rows: Rows, state: dict, save: Callable[[], None],
                 sleep=time.sleep, clock=time.monotonic, poll: float = POLL_SECONDS):
        if not JOB_RE.fullmatch(job):
            raise ValueError(f"job {job!r}: lowercase letters, digits and dashes, at most 24")
        self.job, self.chat = job, str(chat or "")
        self.send, self.rows, self.state, self.save = send, rows, state, save
        self.sleep, self.clock, self.poll = sleep, clock, poll
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
        self.state["asked"][key] = {"options": [list(o) for o in options], "message_id": mid, "typed": False}
        self.save()

    def ask_text(self, key: str, text: str, placeholder: str = "") -> None:
        """Telegram's reply box; the answer is the text of the reply."""
        if not KEY_RE.fullmatch(key):
            raise ValueError(f"question key {key!r}: lowercase letters, digits and _, at most 20")
        if key in self.state["asked"] and self.state["asked"][key].get("typed"):
            return
        markup = {"force_reply": True, "input_field_placeholder": placeholder[:60]} if placeholder else {"force_reply": True}
        mid = self._message(f"{text}\n\n(job {self.job}, answer {key})", markup)
        self.state["asked"][key] = {"options": [], "message_id": mid, "typed": True}
        self.save()

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
        mine = [r for r in self.rows(self.job) if str(r.get("key")) == key and str(r.get("chat_id", "")) == self.chat]
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
        got = {"value": value, "label": label, "by": str(last.get("by") or "").strip() or "someone on the DTJ bot"}
        self.state["answers"][key] = got
        self.save()
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
