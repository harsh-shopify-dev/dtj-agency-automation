"""The engine's HTTP side (stdlib only). n8n calls it once per stage, like Champfuel's brand-engine /onepass:

    POST /stage          {"brand", "run", "stage", "watcher"? (required on "take"), "redo"?, ...stage fields}
                         -> 200 {"ok": true, ...} | 400 bad request | 404 unknown brand | 409 {"ok": false, "busy": true}
    GET  /outputs?brand=&run=      -> {"final": [...], "pictures": [...], "clips": [...]} (absolute paths on the host)
    POST /files?brand=&path=       body = the file (n8n's Drive sync); path stays inside the brand folder

A finished stage is not run again when n8n repeats the SAME call (a retry: {"cached": true}, so no second Flow spend); a call
with other fields (a new round, a note, `only`) or "redo": true runs it. Stages in `rerun` (the person's answer, read every
minute) always run. One reel at a time: a second call while a stage runs gets 409.
A run refuses every stage until "take" has a watcher: a person taps Start and watches (CLAUDE.md rule 9).

    python -m engine.server            REEL_ENGINE_ROOT (default /home/ai/reel-engine), REEL_ENGINE_HOST, REEL_ENGINE_PORT (8091)
"""
from __future__ import annotations

import json
import os
import threading
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .brands import Brand, NoReferences, UnknownBrand, slug
from .runs import Run

MAX_UPLOAD = 1024 * 1024 * 1024  # 1 GB: one reference reel


class NeedsPerson(RuntimeError):
    """A sign-in, captcha, quota page or a question only a person can answer; the run waits for them."""


class Context:
    def __init__(self, root: Path, stages: dict, rerun: set[str] = frozenset()):
        self.root, self.stages, self.rerun = Path(root), stages, set(rerun)
        self.lock = threading.Lock()


def handle(body: dict, ctx: Context) -> tuple[int, dict]:
    stage = str(body.get("stage") or "")
    if stage not in ctx.stages:
        return 400, {"ok": False, "error": f"unknown stage {stage!r}; known: {', '.join(ctx.stages)}"}
    try:
        brand = Brand(ctx.root, str(body.get("brand") or ""))
        run = Run(ctx.root, brand.name, str(body.get("run") or ""))
    except UnknownBrand as exc:
        return 404, {"ok": False, "error": str(exc)}
    except ValueError as exc:
        return 400, {"ok": False, "error": str(exc)}
    watcher = str(body.get("watcher") or run.state.get("watcher") or "").strip()
    if not watcher:
        return 400, {"ok": False, "error": "no watcher: a person must tap Start and watch this run (rule 9)"}
    # the person's answer and a new reel's "take" (which refuses in Telegram while another reel runs) never wait for the lock
    locked = stage not in ctx.rerun and stage != "take"
    if locked and not ctx.lock.acquire(blocking=False):
        return 409, {"ok": False, "busy": True}
    try:
        if run.state.get("watcher") != watcher:
            run.state["watcher"] = watcher
            run.save()
        saved = run.done(stage)
        sig = json.dumps({k: v for k, v in body.items() if k not in ("watcher", "redo")}, sort_keys=True, ensure_ascii=False)
        if saved and saved.get("ok") and saved.get("_call") == sig and not body.get("redo") and stage not in ctx.rerun:
            return 200, {**saved, "cached": True}
        try:
            result = ctx.stages[stage](run, brand, body)
        except NeedsPerson as exc:
            result = {"ok": False, "needs_person": True, "error": str(exc)[:500]}
        except NoReferences as exc:
            result = {"ok": False, "error": str(exc)}
        run.record(stage, {**result, "_call": sig})
        # 422 stops the n8n run at this node (the person was told); fix, then "Retry" the node in n8n
        return (200 if result.get("ok") else 422), {"run": run.run, "stage": stage, **result}
    except Exception as exc:  # noqa: BLE001 - n8n gets a readable answer, the log keeps the trace
        traceback.print_exc()
        return 500, {"ok": False, "error": f"{type(exc).__name__}: {str(exc)[:400]}"}
    finally:
        if locked:
            ctx.lock.release()


def save_file(ctx: Context, brand: str, rel: str, data: bytes) -> tuple[int, dict]:
    try:
        slug(brand, "brand")
    except ValueError as exc:
        return 400, {"ok": False, "error": str(exc)}
    base = (ctx.root / "brands" / brand).resolve()
    if rel != "brand.json" and not (base / "brand.json").is_file():
        return 404, {"ok": False, "error": f"unknown brand {brand!r}: send brand.json first"}
    dest = (base / rel).resolve()
    if base not in dest.parents:
        return 400, {"ok": False, "error": "path must stay inside the brand folder"}
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return 200, {"ok": True, "path": str(dest), "bytes": len(data)}


def outputs(ctx: Context, brand: str, run: str) -> tuple[int, dict]:
    try:
        r = Run(ctx.root, brand, run)
    except ValueError as exc:
        return 400, {"ok": False, "error": str(exc)}

    def files(sub: str) -> list[str]:
        d = r.dir / sub
        return sorted(str(p) for p in d.rglob("*") if p.is_file()) if d.is_dir() else []

    return 200, {"ok": True, "brand": r.brand, "run": r.run, "final": files("final"), "pictures": files("pictures"),
                 "clips": files("clips")}


def serve(ctx: Context, host: str, port: int) -> None:
    class H(BaseHTTPRequestHandler):
        def _send(self, code: int, ans: dict) -> None:
            raw = json.dumps(ans, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self):  # noqa: N802
            u = urlparse(self.path)
            q = {k: v[0] for k, v in parse_qs(u.query).items()}
            if u.path == "/outputs":
                return self._send(*outputs(ctx, q.get("brand", ""), q.get("run", "")))
            if u.path == "/health":
                return self._send(200, {"ok": True, "busy": ctx.lock.locked()})
            self._send(404, {"ok": False, "error": "not found"})

        def do_POST(self):  # noqa: N802
            u = urlparse(self.path)
            n = int(self.headers.get("Content-Length") or 0)
            if n > MAX_UPLOAD:
                return self._send(413, {"ok": False, "error": "file too large"})
            data = self.rfile.read(n)
            if u.path == "/files":
                q = {k: v[0] for k, v in parse_qs(u.query).items()}
                return self._send(*save_file(ctx, q.get("brand", ""), q.get("path", ""), data))
            if u.path == "/stage":
                try:
                    body = json.loads(data or b"{}")
                except json.JSONDecodeError:
                    return self._send(400, {"ok": False, "error": "body is not JSON"})
                return self._send(*handle(body, ctx))
            self._send(404, {"ok": False, "error": "not found"})

    ThreadingHTTPServer((host, port), H).serve_forever()


def main() -> None:
    from .stages import RERUN, SERVER_STAGES  # noqa: PLC0415 - the stages pull in reel-factory; tests use their own
    root = Path(os.environ.get("REEL_ENGINE_ROOT", "/home/ai/reel-engine"))
    serve(Context(root, SERVER_STAGES, RERUN), os.environ.get("REEL_ENGINE_HOST", "172.16.1.1"),
          int(os.environ.get("REEL_ENGINE_PORT", "8091")))


if __name__ == "__main__":
    main()
