"""HTTP with DTJ's retry rule (CLAUDE.md, self-healing): retry 429 and 5xx with backoff, at most 3 tries. Errors never carry a token."""
from __future__ import annotations

import re
import time
from typing import Callable

import requests

_SECRETISH = re.compile(r"(access_token|token|key|secret|password)=([^&\s]+)", re.I)


class PublishError(Exception):
    pass


_BOT_TOKEN = re.compile(r"bot\d+:[A-Za-z0-9_-]+")


def clean(text: str) -> str:
    return _BOT_TOKEN.sub("bot[redacted]", _SECRETISH.sub(r"\1=[redacted]", str(text)))[:800]


class Http:
    def __init__(self, session: requests.Session | None = None, sleep: Callable[[float], None] = time.sleep, tries: int = 3):
        self.session = session or requests.Session()
        self.sleep, self.tries = sleep, tries

    def call(self, method: str, url: str, *, ok=(200, 201, 202, 204, 308), **kw) -> requests.Response:
        kw.setdefault("timeout", 120)
        last = None
        for attempt in range(self.tries):
            try:
                r = self.session.request(method, url, **kw)
            except requests.RequestException as e:
                last = f"{type(e).__name__}"
            else:
                if r.status_code in ok:
                    return r
                last = f"HTTP {r.status_code}: {clean(r.text)}"
                if r.status_code != 429 and r.status_code < 500:
                    break
            if attempt < self.tries - 1:
                self.sleep(2 ** attempt * 5)
        raise PublishError(f"{method} {clean(url.split('?')[0])} failed: {last}")

    def json(self, method: str, url: str, **kw) -> dict:
        r = self.call(method, url, **kw)
        return r.json() if r.content else {}
