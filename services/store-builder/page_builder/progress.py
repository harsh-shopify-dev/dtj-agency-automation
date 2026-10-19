"""A live progress bar for the brand intake in ONE Telegram message (Harsh, 19 Oct 2026: "is it possible to add a progress bar or time
duration in the telegram bot?"). The GitHub run sends the message when the intake starts and edits it as the work moves on:

    Brand intake: freesoul.com
    ███████░░░ 70%
    Downloading pictures and videos: product 14 of 20
    Time so far: 1 min 05 s

The percentage comes from real counts (products read, files uploaded), never from a guess of how long a store takes. It is switched on
only when the run has the bot token and a chat (DTJ_TELEGRAM_BOT_TOKEN, DTJ_PROGRESS_CHAT); otherwise every call does nothing. It is
best effort: a Telegram error never stops the intake, and an error message never contains the token (it is part of Telegram's URL).
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Callable

# stage -> (what the person reads, where the bar starts, where it ends). The split between stages is a set layout (most of the bar for
# the downloads and the upload, the slow parts), not a measured timing; inside a stage the bar moves by real counts.
STAGES = {
    "read": ("Reading the store", 0, 10),
    "products": ("Downloading pictures and videos", 10, 70),
    "extras": ("Collections and policies", 70, 76),
    "write": ("Writing BRAND.md and the palette", 76, 80),
    "drive": ("Uploading to Google Drive", 80, 100),
}
CELLS = 10
EVERY = 4.0  # seconds between edits: Telegram allows about one edit a second per chat
Post = Callable[[str, dict], "tuple[int, dict]"]


def _post(url: str, data: dict) -> tuple[int, dict]:
    req = urllib.request.Request(url, data=json.dumps(data).encode(), headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as exc:
        return exc.code, {}
    except (urllib.error.URLError, OSError, ValueError):
        return 0, {}


def took(seconds: float) -> str:
    """'45 s', '2 min 05 s'."""
    s = max(0, int(round(seconds)))
    return f"{s} s" if s < 60 else f"{s // 60} min {s % 60:02d} s"


def bar(percent: int) -> str:
    full = round(CELLS * percent / 100)
    return "█" * full + "░" * (CELLS - full) + f" {percent}%"


class Progress:
    def __init__(self, store: str, token: str | None = None, chat: str | None = None, post: Post = _post,
                 clock: Callable[[], float] = time.monotonic, every: float = EVERY):
        self.store, self.post, self.clock, self.every = store, post, clock, every
        self.token = token if token is not None else os.environ.get("DTJ_TELEGRAM_BOT_TOKEN", "")
        self.chat = chat if chat is not None else os.environ.get("DTJ_PROGRESS_CHAT", "")
        self.on = bool(self.token and self.chat)
        self.started = clock()
        self.message_id = None
        self.last_edit = -1e9
        self.last_text = ""
        self.failures = 0

    def _call(self, method: str, data: dict) -> dict:
        if not self.on or self.failures >= 3:  # three failed calls: stop trying, the intake goes on
            return {}
        status, answer = self.post(f"https://api.telegram.org/bot{self.token}/{method}", data)
        if status != 200:
            self.failures += 1
            print(f"  progress message: Telegram answered {status or 'nothing'} (the intake goes on)")
            return {}
        return answer.get("result") or {}

    def _text(self, percent: int, line: str, last: str) -> str:
        return f"Brand intake: {self.store}\n{bar(percent)}\n{line}\n{last}"

    def start(self) -> None:
        text = self._text(0, "Starting...", "Time so far: 0 s")
        sent = self._call("sendMessage", {"chat_id": self.chat, "text": text, "disable_notification": True})
        self.message_id = sent.get("message_id")
        self.last_text, self.last_edit = text, self.clock()

    def _edit(self, text: str, force: bool) -> None:
        if not self.message_id or text == self.last_text:
            return
        now = self.clock()
        if not force and now - self.last_edit < self.every:
            return
        self._call("editMessageText", {"chat_id": self.chat, "message_id": self.message_id, "text": text})
        self.last_text, self.last_edit = text, now

    def update(self, stage: str, done: int = 0, total: int = 0) -> None:
        """Where the intake is: a stage from STAGES and, when known, how many of how many (products, files)."""
        if not self.on:
            return
        label, lo, hi = STAGES[stage]
        share = min(1.0, done / total) if total else 0.0
        percent = int(lo + (hi - lo) * share)
        unit = {"products": "product", "drive": "file"}.get(stage)
        line = f"{label}: {unit} {done} of {total}" if unit and total else label
        self._edit(self._text(percent, line, f"Time so far: {took(self.clock() - self.started)}"), force=False)

    def finish(self, ok: bool, note: str = "") -> str:
        """The last edit (always sent): done in N, or stopped after N. Returns the time taken, for the final message."""
        spent = took(self.clock() - self.started)
        if self.on:
            if ok:
                text = self._text(100, f"Done in {spent}.", note or "The Drive link comes in the next message.")
            else:
                text = f"Brand intake: {self.store}\nStopped after {spent}.\n{note or 'The next message says why.'}"
            self._edit(text, force=True)
        return spent
