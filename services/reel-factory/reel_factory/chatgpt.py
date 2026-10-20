"""Make the reel's character and the product-in-hand picture in ChatGPT, in the same logged-in Chrome as Flow (no API).

Harsh's process (20 Oct 2026):
1. A FRESH chat, text only: a written description of the reference creator's look and setting (never her photo), so the new
   character does not copy a real person. Anti-"AI slop" wording comes from the script (real room, natural light, phone camera).
2. Another FRESH chat: the character picture + the real product photo: "put this exact product in her hand", label readable.
Every call opens a new chat, so nothing from one product leaks into the next.
The page's selectors were read on chatgpt.com on 20 Oct 2026; ChatGPT changes its page often: when a selector stops matching this
raises ChatGPTError with what it looked for, and the session doing the job does that step by hand in the same window.
"""
from __future__ import annotations

import re
import time
from pathlib import Path

from .flow import NeedsPerson, download

CHAT = "https://chatgpt.com/"


class ChatGPTError(RuntimeError):
    pass


class ChatGPT:
    def __init__(self, page):
        self.page = page

    @classmethod
    def attach(cls, cdp: str = "http://127.0.0.1:9222"):
        from playwright.sync_api import sync_playwright
        pw = sync_playwright().start()
        browser = pw.chromium.connect_over_cdp(cdp)
        ctx = browser.contexts[0] if browser.contexts else browser.new_context()
        inst = cls(ctx.new_page())
        inst._pw = pw
        return inst

    def close(self):
        self.page.close()
        if getattr(self, "_pw", None):
            self._pw.stop()

    def _guard(self):
        if "auth" in self.page.url or self.page.locator("text=/Log in|Sign up/").count() and not self.page.locator("#prompt-textarea").count():
            raise NeedsPerson("ChatGPT is signed out in the reel Chrome window: a person must sign in once")
        if self.page.locator("text=/verify you are human|unusual activity/i").count():
            raise NeedsPerson("ChatGPT shows a human check: a person must look at the reel Chrome window")

    def new_chat(self):
        self.page.goto(CHAT, wait_until="domcontentloaded")
        self.page.wait_for_timeout(3000)
        self._guard()
        if not self.page.locator("#prompt-textarea").count():
            raise ChatGPTError("no prompt box (#prompt-textarea) on chatgpt.com")

    def _images(self) -> list[str]:
        return self.page.eval_on_selector_all("main img", "els => els.filter(e => e.naturalWidth >= 512).map(e => e.src)")

    def image(self, prompt: str, out: str | Path, files: list[str | Path] = (), timeout_s: int = 300) -> Path:
        """One fresh chat: attach `files`, send `prompt`, wait for the generated picture, save it to `out`."""
        self.new_chat()
        if files:
            self.page.locator("input[type=file]").first.set_input_files([str(f) for f in files])
            self.page.wait_for_timeout(4000)
        before = set(self._images())
        box = self.page.locator("#prompt-textarea")
        box.click(); box.fill(prompt)
        self.page.locator("[data-testid=send-button]").click()
        end = time.time() + timeout_s
        while time.time() < end:
            self.page.wait_for_timeout(5000)
            self._guard()
            busy = self.page.locator("[data-testid=stop-button]").count()
            new = [s for s in self._images() if s not in before]
            if new and not busy:
                self.page.wait_for_timeout(3000)
                src = [s for s in self._images() if s not in before][-1]
                return _save(self.page, src, out)
            refused = self.page.locator("text=/can.t help|content policy|unable to generate/i").count()
            if refused and not busy:
                raise ChatGPTError("ChatGPT refused the picture: reword the description (no real person's name, no brand of another company)")
        raise ChatGPTError(f"no picture after {timeout_s}s")


def _save(page, src: str, out: str | Path) -> Path:
    if re.match(r"^https?://", src):
        try:
            return download(src, out)
        except OSError:
            pass
    # signed-in picture links need the page's cookies: fetch inside the page
    data = page.evaluate("""async (u) => { const r = await fetch(u); const b = new Uint8Array(await r.arrayBuffer());
                                          let s = ''; for (const x of b) s += String.fromCharCode(x); return btoa(s); }""", src)
    import base64
    out = Path(out); out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(base64.b64decode(data))
    return out
