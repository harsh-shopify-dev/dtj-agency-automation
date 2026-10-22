"""The ChatGPT picture command hosted on the reel VPS (Harsh, 22 Oct 2026: "we will use chatgpt cli which will be hosted on our
hostinger vps using which you can generate the images ... where you have to upload the referennce images of our products").

    python -m reel_factory.chatgpt_cli image --prompt-file <txt> --out <png> [--ref <img> ...] [--cdp http://127.0.0.1:9222]
                                             [--timeout 300]

One FRESH chat in the reel Chrome (the logged-in ChatGPT the reel factory already drives, reel_factory/chatgpt.py; no API key):
the reference pictures of OUR product are attached, the prompt is sent, the picture is saved at --out. It prints ONE JSON line:
{"ok": true, "path", "refs", "seconds"} (exit 0), or {"ok": false, "error"} (exit 1; "needs_person": true when ChatGPT is signed
out or shows a human check; exit 2 when the reel Chrome does not answer). The laptop calls it over ssh
(services/store-builder/provision/ai_images.py, backend "vps"); every call is a new chat, so nothing leaks between products.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from .flow import NeedsPerson

CDP_DEFAULT = "http://127.0.0.1:9222"


def _attach(cdp: str):
    from .chatgpt import ChatGPT  # noqa: PLC0415 - playwright is loaded only when a picture is made
    return ChatGPT.attach(cdp)


def image(prompt_file: str | Path, out: str | Path, refs: list[str | Path] = (), cdp: str = CDP_DEFAULT, timeout: int = 300,
          attach=None, clock=time.monotonic) -> tuple[int, dict]:
    """(exit code, the JSON answer). Nothing is retried here: the caller decides."""
    started = clock()
    try:
        prompt = Path(prompt_file).read_text(encoding="utf-8").strip()
    except OSError as exc:
        return 1, {"ok": False, "error": f"cannot read the prompt file: {exc}"}
    if not prompt:
        return 1, {"ok": False, "error": "the prompt file is empty"}
    missing = [str(r) for r in refs if not Path(r).is_file()]
    if missing:
        return 1, {"ok": False, "error": f"reference picture not found: {', '.join(missing)}"}
    try:
        cg = (attach or _attach)(cdp)
    except Exception as exc:  # noqa: BLE001 - Chrome closed, playwright missing: the caller says what to open
        return 2, {"ok": False, "error": f"the reel Chrome does not answer at {cdp}: {str(exc)[:200]}"}
    try:
        saved = Path(cg.image(prompt, out, files=[str(r) for r in refs], timeout_s=timeout))
    except NeedsPerson as exc:
        return 1, {"ok": False, "error": str(exc)[:300], "needs_person": True}
    except Exception as exc:  # noqa: BLE001 - ChatGPTError (refused, no picture in time, a selector changed): said plainly
        return 1, {"ok": False, "error": str(exc)[:300]}
    finally:
        if hasattr(cg, "close"):
            cg.close()
    if not saved.is_file() or not saved.stat().st_size:
        return 1, {"ok": False, "error": "ChatGPT answered but no picture was saved"}
    return 0, {"ok": True, "path": str(saved), "refs": len(refs), "seconds": round(clock() - started, 1)}


def main(argv: list[str] | None = None, attach=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    im = sub.add_parser("image", help="one picture in a fresh ChatGPT chat")
    im.add_argument("--prompt-file", required=True)
    im.add_argument("--out", required=True)
    im.add_argument("--ref", action="append", default=[], help="a reference picture of our product (repeatable)")
    im.add_argument("--cdp", default=CDP_DEFAULT)
    im.add_argument("--timeout", type=int, default=300)
    a = ap.parse_args(argv)
    code, answer = image(a.prompt_file, a.out, a.ref, a.cdp, a.timeout, attach=attach)
    print(json.dumps(answer, ensure_ascii=False))
    return code


if __name__ == "__main__":
    sys.exit(main())
