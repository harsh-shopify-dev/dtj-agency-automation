"""The Flow clip command hosted on the reel VPS, the twin of chatgpt_cli (Harsh, 30 Oct 2026: "find a way if we can follow the
same as chatgpt cli that generates the images so the flow does too"):

    python -m reel_factory.flow_cli clip --image <start picture> --prompt-file <txt> --out <folder>
                                         [--product <pack photo> ...] [--seconds 8] [--takes 2] [--project <Flow project URL>]
                                         [--cdp http://127.0.0.1:9222] [--timeout 900]

Drives Google Flow in the logged-in reel Chrome (reel_factory/flow.py; the Ultra plan, no API): Video, Omni Flash, Ingredients,
9:16, the mode set BEFORE attaching (a mode change drops ingredients), the start picture and the pack uploaded and attached by
asset id (never by position), the takes downloaded from each clip's own signed URL. It prints ONE JSON line:
{"ok": true, "files": [...], "assets": [...], "credits": 24, "project": "<url>", "seconds": 61.0} (exit 0), or
{"ok": false, "error"} (exit 1; "needs_person": true when Google wants a sign-in or a check; exit 2 when the reel Chrome does not answer).
Spends Flow credits (Omni Flash: 14 per 4 s x2, 24 per 8 s x2; 6 s and 10 s not read: "credits": null).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from .flow import NeedsPerson
from .job import CREDITS, SECONDS

CDP_DEFAULT = "http://127.0.0.1:9222"


def _attach(cdp: str):
    from .flow import Flow  # noqa: PLC0415 - playwright is loaded only when a clip is made
    return Flow(cdp)


def _download(url: str, dest: Path) -> Path:
    from .flow import download  # noqa: PLC0415
    return download(url, dest)


def clip(image: str | Path, prompt_file: str | Path, out_dir: str | Path, products: list[str | Path] = (), seconds: int = 8,
         takes: int = 2, project: str | None = None, cdp: str = CDP_DEFAULT, timeout: int = 900, attach=None, download=None,
         clock=time.monotonic) -> tuple[int, dict]:
    """(exit code, the JSON answer). Nothing is retried here: the caller decides."""
    started = clock()
    if seconds not in SECONDS:
        return 1, {"ok": False, "error": f"seconds must be 4, 6, 8 or 10 (got {seconds})"}
    try:
        prompt = Path(prompt_file).read_text(encoding="utf-8").strip()
    except OSError as exc:
        return 1, {"ok": False, "error": f"cannot read the prompt file: {exc}"}
    if not prompt:
        return 1, {"ok": False, "error": "the prompt file is empty"}
    missing = [str(p) for p in (image, *products) if not Path(p).is_file()]
    if missing:
        return 1, {"ok": False, "error": f"picture not found: {', '.join(missing)}"}
    try:
        fl = (attach or _attach)(cdp)
    except Exception as exc:  # noqa: BLE001 - Chrome closed, playwright missing: the caller says what to open
        return 2, {"ok": False, "error": f"the reel Chrome does not answer at {cdp}: {str(exc)[:200]}"}
    try:
        url = fl.open_project(project)
        fl.settings("Video", takes=takes, model="Omni", seconds=seconds)
        ids = [fl.upload(p) for p in (image, *products)]
        fl.clear_attached()
        for a in ids:
            fl.attach(a)
        made = fl.generate(prompt, expect=takes, timeout_s=timeout)
        out = Path(out_dir)
        stem = Path(image).stem
        files = [str((download or _download)(fl.video_url(a), out / f"{stem}_t{k + 1}_{a[:8]}.mp4")) for k, a in enumerate(made)]
    except NeedsPerson as exc:
        return 1, {"ok": False, "error": str(exc)[:300], "needs_person": True}
    except Exception as exc:  # noqa: BLE001 - FlowError (policy, timeout, a selector changed): said plainly
        return 1, {"ok": False, "error": str(exc)[:300]}
    finally:
        if hasattr(fl, "close"):
            fl.close()
    credits = CREDITS.get(seconds) if takes == 2 else None
    return 0, {"ok": True, "files": files, "assets": made, "credits": credits, "project": url,
               "seconds": round(clock() - started, 1)}


def main(argv: list[str] | None = None, attach=None, download=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("clip", help="one Flow video (2 takes) from a start picture")
    c.add_argument("--image", required=True, help="the approved start picture of this scene")
    c.add_argument("--prompt-file", required=True)
    c.add_argument("--out", required=True, help="folder for the takes")
    c.add_argument("--product", action="append", default=[], help="a photo of our real pack (repeatable)")
    c.add_argument("--seconds", type=int, default=8)
    c.add_argument("--takes", type=int, default=2)
    c.add_argument("--project", default=None, help="reuse this Flow project (else a new one)")
    c.add_argument("--cdp", default=CDP_DEFAULT)
    c.add_argument("--timeout", type=int, default=900)
    a = ap.parse_args(argv)
    code, answer = clip(a.image, a.prompt_file, a.out, a.product, a.seconds, a.takes, a.project, a.cdp, a.timeout,
                        attach=attach, download=download)
    print(json.dumps(answer, ensure_ascii=False))
    return code


if __name__ == "__main__":
    sys.exit(main())
