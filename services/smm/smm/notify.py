"""Telegram messages to DTJ's team chat through DTJ's bot (send only; the bot's own n8n workflow keeps handling replies).

Env: DTJ_TELEGRAM_BOT_TOKEN (GitHub secret), SMM_TELEGRAM_CHAT_ID. Without them every message is printed instead.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping

from .http import Http

API = "https://api.telegram.org"
CAPTION_MAX = 1024
TEXT_MAX = 4096


class Telegram:
    def __init__(self, env: Mapping[str, str], chat_id: str, http: Http | None = None, out=print):
        self.token = (env.get("DTJ_TELEGRAM_BOT_TOKEN") or "").strip()
        self.chat_id, self.http, self.out = chat_id, http or Http(), out

    @property
    def live(self) -> bool:
        return bool(self.token and self.chat_id)

    def _url(self, method: str) -> str:
        return f"{API}/bot{self.token}/{method}"

    def text(self, message: str) -> None:
        for i in range(0, len(message), TEXT_MAX):
            part = message[i:i + TEXT_MAX]
            if not self.live:
                self.out(f"[telegram] {part}")
                continue
            self.http.call("POST", self._url("sendMessage"), json={"chat_id": self.chat_id, "text": part,
                                                                   "disable_web_page_preview": True})

    def files(self, paths: list[Path], caption: str = "") -> None:
        """One picture, video or document, or an album of up to 10 pictures. A long caption goes as its own message."""
        short = caption if len(caption) <= CAPTION_MAX else ""
        if not self.live:
            self.out(f"[telegram] files {[p.name for p in paths]} {short or ''}")
            if caption and not short:
                self.text(caption)
            return
        if len(paths) == 1:
            p = paths[0]
            kind = {".jpg": "photo", ".jpeg": "photo", ".png": "photo", ".mp4": "video"}.get(p.suffix.lower(), "document")
            self.http.call("POST", self._url(f"send{kind.capitalize()}"), data={"chat_id": self.chat_id, "caption": short},
                           files={kind: (p.name, p.read_bytes())})
        else:
            media = [{"type": "photo", "media": f"attach://f{i}", **({"caption": short} if i == 0 and short else {})}
                     for i in range(len(paths[:10]))]
            self.http.call("POST", self._url("sendMediaGroup"), data={"chat_id": self.chat_id, "media": json.dumps(media)},
                           files={f"f{i}": (p.name, p.read_bytes()) for i, p in enumerate(paths[:10])})
        if caption and not short:
            self.text(caption)
