"""A live progress bar for the brand intake in ONE Telegram message (Harsh, 19 Oct 2026: "is it possible to add a progress bar or time
duration in the telegram bot?"). The GitHub run sends the message when the intake starts and edits it as the work moves on:

    Brand intake: freesoul.com
    ███████░░░ 70%
    Downloading pictures and videos: product 14 of 20
    Time so far: 1 min 05 s

The percentage comes from real counts (products read, files uploaded), never from a guess of how long a store takes. It is switched on
only when the run has the bot token and a chat (DTJ_TELEGRAM_BOT_TOKEN, DTJ_PROGRESS_CHAT); otherwise every call does nothing. It is
best effort: a Telegram error never stops the intake, and an error message never contains the token (it is part of Telegram's URL).
In a GitHub run (GITHUB_RUN_ID) the message carries a Stop button (callback stop:intake:<run id>; the bot cancels that run, Harsh,
19 Oct 2026: "add a stop feature"). The last edit removes the button. With DTJ_PROGRESS_FILE set, the message id is kept in that file
until the last edit, so the workflow's final step can close a message the intake could not close itself (a stopped or crashed run).

PAGE DESIGN (Harsh, 20 Oct 2026: "in the telegram bot also add the progress bar for page designing"): the same kind of message for a
page request from the bot. The designer's Claude Code session runs one short command at each step of its task list
(n8n/store-factory/request_page_design.js); every command edits the same message, its id kept in a small state file next to the page:

    python -m page_builder.progress page start --chat <telegram chat id> --title "Page design: radiance-serum" --state <client>/progress.json
    python -m page_builder.progress page step --stage build --done 2 --total 3 --state <client>/progress.json
    python -m page_builder.progress page done --state <client>/progress.json          (or: page stopped --note "why")

    Page design: radiance-serum
    ███████░░░ 70%
    Building the page and running the design checks: round 2 of 3
    Time so far: 9 min 40 s

The split between the steps is a set layout (PAGE_STAGES), not a measured timing; the time is the real time since the start. Each
command always exits 0 and never stops the design: no chat or no token = nothing is sent.
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
        run = os.environ.get("GITHUB_RUN_ID", "")
        self.buttons = {"inline_keyboard": [[{"text": "Stop", "callback_data": f"stop:intake:{run}"}]]} if run.isdigit() else None
        self.id_file = os.environ.get("DTJ_PROGRESS_FILE", "")

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
        data = {"chat_id": self.chat, "text": text, "disable_notification": True}
        if self.buttons:
            data["reply_markup"] = self.buttons
        sent = self._call("sendMessage", data)
        self.message_id = sent.get("message_id")
        if self.message_id and self.id_file:
            try:
                with open(self.id_file, "w", encoding="utf-8") as fh:
                    fh.write(str(self.message_id))
            except OSError:
                pass
        self.last_text, self.last_edit = text, self.clock()

    def _edit(self, text: str, force: bool, last: bool = False) -> None:
        if not self.message_id or text == self.last_text:
            return
        now = self.clock()
        if not force and now - self.last_edit < self.every:
            return
        data = {"chat_id": self.chat, "message_id": self.message_id, "text": text}
        if self.buttons and not last:  # an edit without reply_markup removes the button: only the last edit does that
            data["reply_markup"] = self.buttons
        self._call("editMessageText", data)
        self.last_text, self.last_edit = text, now
        if last and self.id_file:  # closed here: the workflow's last step leaves the message alone
            try:
                os.remove(self.id_file)
            except OSError:
                pass

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
            self._edit(text, force=True, last=True)
        return spent


# ------------------------------------------------------------------------------------------------ page design
# step -> (what the person reads, where the bar starts, where it ends). A set layout: most of the bar for the slow parts (the brand
# data, the facts and words, the build with its design checks), not a measured timing.
PAGE_STAGES = {
    "brief": ("Reading the brief", 0, 5),
    "intake": ("Collecting the brand's pictures and details", 5, 20),
    "product": ("Reading the product and its pictures", 20, 30),
    "facts": ("Writing the facts, the brand and the words", 30, 55),
    "build": ("Building the page and running the design checks", 55, 85),
    "check": ("Checking the page on the draft theme", 85, 95),
}
ROUND_UNITS = {"build": "round", "intake": "step"}


class PageProgress:
    """The page-design bar. Each command is its own process, so the message id, the chat and the start time live in a state file
    (no secret in it: the token comes from DTJ_TELEGRAM_BOT_TOKEN only)."""

    def __init__(self, state: str | os.PathLike, token: str | None = None, post: Post = _post, clock: Callable[[], float] = time.time):
        self.path, self.post, self.clock = os.fspath(state), post, clock
        self.token = token if token is not None else os.environ.get("DTJ_TELEGRAM_BOT_TOKEN", "")
        try:
            with open(self.path, encoding="utf-8") as fh:
                self.s = json.load(fh)
        except (OSError, ValueError):
            self.s = {}

    def _save(self) -> None:
        folder = os.path.dirname(self.path)
        if folder:
            os.makedirs(folder, exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as fh:
            json.dump(self.s, fh, indent=1)

    def _call(self, method: str, data: dict) -> dict:
        if not self.token:
            return {}
        status, answer = self.post(f"https://api.telegram.org/bot{self.token}/{method}", data)
        if status != 200:
            print(f"progress bar: Telegram answered {status or 'nothing'} (the design goes on)")
            return {}
        return answer.get("result") or {}

    def _time(self) -> str:
        return took(self.clock() - float(self.s.get("started", self.clock())))

    def _edit(self, text: str) -> None:
        if not self.s.get("message_id") or text == self.s.get("last_text"):  # Telegram refuses an edit that changes nothing
            return
        self._call("editMessageText", {"chat_id": self.s["chat"], "message_id": self.s["message_id"], "text": text})
        self.s["last_text"] = text
        self._save()

    def start(self, chat: str, title: str) -> str:
        chat = str(chat or "").strip()
        if not chat or not self.token:
            return "progress bar: off (no Telegram chat for this request, or no DTJ_TELEGRAM_BOT_TOKEN)"
        text = f"{title}\n{bar(0)}\nStarting...\nTime so far: 0 s"
        sent = self._call("sendMessage", {"chat_id": chat, "text": text, "disable_notification": True})
        self.s = {"chat": chat, "title": title, "message_id": sent.get("message_id"), "started": self.clock(), "last_text": text}
        self._save()
        return "progress bar: started" if sent.get("message_id") else "progress bar: Telegram did not take the message (the design goes on)"

    def step(self, stage: str, done: int = 0, total: int = 0) -> str:
        if stage not in PAGE_STAGES:
            return f"progress bar: unknown step {stage!r}; use one of {', '.join(PAGE_STAGES)}"
        if not self.s.get("message_id"):
            return "progress bar: off"
        label, lo, hi = PAGE_STAGES[stage]
        share = min(1.0, done / total) if total else 0.0
        percent = int(lo + (hi - lo) * share)
        unit = ROUND_UNITS.get(stage)
        line = f"{label}: {unit} {done} of {total}" if unit and total else label
        self._edit(f"{self.s['title']}\n{bar(percent)}\n{line}\nTime so far: {self._time()}")
        return f"progress bar: {percent}%"

    def finish(self, ok: bool, note: str = "") -> str:
        if not self.s.get("message_id"):
            return "progress bar: off"
        spent = self._time()
        if ok:
            self._edit(f"{self.s['title']}\n{bar(100)}\nDone in {spent}.\n{note or 'The preview link comes in the next message.'}")
        else:
            self._edit(f"{self.s['title']}\nStopped after {spent}.\n{note or 'The next message says why.'}")
        return f"progress bar: {'done' if ok else 'stopped'} after {spent}"


def main(argv: list[str] | None = None) -> int:
    import argparse  # noqa: PLC0415  (only the command line needs it)

    ap = argparse.ArgumentParser(description="The page-design progress bar in Telegram (one message, edited at every step).")
    sub = ap.add_subparsers(dest="kind", required=True)
    page = sub.add_parser("page", help="a page request from the bot")
    page.add_argument("action", choices=("start", "step", "done", "stopped"))
    page.add_argument("--state", required=True, help="the state file, e.g. <client folder>/progress.json")
    page.add_argument("--chat", help="start: the requester's Telegram chat id (the brief's telegram_chat_id)")
    page.add_argument("--title", default="Page design", help="start: the first line, e.g. 'Page design: radiance-serum'")
    page.add_argument("--stage", help=f"step: one of {', '.join(PAGE_STAGES)}")
    page.add_argument("--done", type=int, default=0)
    page.add_argument("--total", type=int, default=0)
    page.add_argument("--note", default="", help="done / stopped: the last line")
    a = ap.parse_args(argv)
    p = PageProgress(a.state)
    try:
        if a.action == "start":
            msg = p.start(a.chat, a.title)
        elif a.action == "step":
            msg = p.step(a.stage or "", a.done, a.total)
        else:
            msg = p.finish(a.action == "done", a.note)
    except OSError as exc:  # a state file that cannot be written must not stop the design either
        msg = f"progress bar: {type(exc).__name__} (the design goes on)"
    print(msg)
    return 0  # never stops the design


if __name__ == "__main__":
    raise SystemExit(main())
