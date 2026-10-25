"""A reel job's Telegram side: the progress bar, the three approvals and the person-needed questions (Harsh, 25 Oct 2026: "Plan /
script, Pictures, Final reel" approved in Telegram; "we will create a new telegram bot for this automation"). The reel's Claude
session on the VPS runs these; every message goes through the REEL bot (DTJ_REEL_BOT_TOKEN), and taps come back through that bot's
n8n workflow into dtj_bot_answers, read with the store factory's Asker (n8n/store-factory/bot_ask.py).

    python n8n/reel-factory/reel_job.py start    --job r42 --chat <telegram chat> --title "Reel: <product> (remake)"
    python n8n/reel-factory/reel_job.py step     --job r42 --stage pictures --done 3 --total 16
    python n8n/reel-factory/reel_job.py plan     --job r42 --file <plan.md or script summary> [--round 1]
    python n8n/reel-factory/reel_job.py pictures --job r42 --dir <images folder> [--files p01.png,p02.png] [--round 1]
    python n8n/reel-factory/reel_job.py final    --job r42 --file <final.mp4> [--round 1]
    python n8n/reel-factory/reel_job.py person   --job r42 --what "<what a person must do, e.g. sign in to Flow>" [--round 1]
    python n8n/reel-factory/reel_job.py tell     --job r42 --text "<a message>"
    python n8n/reel-factory/reel_job.py photos   --job r42 --ids tg:<file_id>,... --out <job>/inputs   (photos sent to the bot)
    python n8n/reel-factory/reel_job.py finish   --job r42 (--ok | --stopped) [--note "..."]
    plan / pictures / final take --watch <job>/watch/<gate>.verdict.json: the watcher's card is sent first; a BLOCKED verdict
    is refused (exit 2) so a person only ever sees work the watcher let through.

plan / pictures / final send what is to be judged (text, an album of numbered pictures, the video) with two buttons: "Approve" and
"Change something"; "Change something" then asks what to change (typed, for pictures "3, 7: the box is too small"). They print ONE
JSON line, {"ok": true, "by": "<name>"} or {"ok": false, "by": "<name>", "note": "<what to change>"}, and exit 0; exit 3 = no
answer yet (the worker runs the same command again until there is one, CLAUDE.md DTJ_WAIT; nothing is sent twice). A new round
(after changes) is a new --round. An Approve is that person's yes for the next step only, written to the job's action log as
approved_by "<name> (Telegram Approve)". State: .work/reels/telegram/<job>/job.json (no secret in it).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "n8n" / "store-factory"))
sys.path.insert(0, str(ROOT / "services" / "store-builder"))
sys.path.insert(0, str(ROOT / "services" / "reel-factory"))
import tg_media  # noqa: E402
from bot_ask import Asker  # noqa: E402
from reel_factory.watch_card import card  # noqa: E402 - no heavy imports

STATE_DIR = ROOT / ".work" / "reels" / "telegram"
WAITING = 3
MINUTES = 3            # each check waits this long, then exits 3 so the session hands the wait to the worker
REVIEW = [("Approve", "yes"), ("Change something", "redo")]
DONE = [("Done", "done")]
WHAT = {"plan": "the shot list / script", "pictures": "the pictures", "final": "the finished reel"}
NEXT = {"plan": "the pictures are made next (Codex, no Flow credits yet)",
        "pictures": "the motion clips are made next in Flow (this spends Flow credits)",
        "final": "the reel is marked ready; nothing is posted anywhere"}
REDO_HOW = {"plan": "What should change in the plan?",
            "pictures": "Which pictures and what should change? e.g. \"3, 7: the box is too small; 12: warmer light\"",
            "final": "What should change? e.g. \"shot 4: the oil pour is too slow\""}
# stage -> (what the person reads, where the bar starts, where it ends); inside a stage the bar moves by real counts
STAGES = {"refs": ("Downloading and studying the reference", 0, 10),
          "plan": ("Plan ready: waiting for your Approve", 10, 15),
          "pictures": ("Making the pictures", 15, 45),
          "clips": ("Making the motion clips in Flow", 45, 75),
          "edit": ("Editing to the reference", 75, 95),
          "final": ("Final reel: waiting for your Approve", 95, 100)}
UNITS = {"pictures": "picture", "clips": "clip"}


def token() -> str:
    return os.environ.get("DTJ_REEL_BOT_TOKEN", "")


def _sender(tok: str):
    from page_builder.progress import _post  # noqa: PLC0415

    def send(method: str, data: dict) -> dict:
        if not tok:
            return {}
        for _ in range(2):
            status, got = _post(f"https://api.telegram.org/bot{tok}/{method}", data)
            if status == 200:
                return got.get("result") or {}
        return {}
    return send


class ReelJob:
    def __init__(self, job: str, *, send=None, rows=None, add_row=None, media=None, progress=None, state_dir: Path = STATE_DIR,
                 out=print, sleep=None, clock=None, log=None):
        import time  # noqa: PLC0415
        self.job, self.dir = job, state_dir / job
        self.path = self.dir / "job.json"
        self.s = json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else {}
        self.out, self.log = out, log
        tok = token()
        self.media = media or tg_media
        self.tok = tok
        if rows is None or add_row is None:
            import store_job  # noqa: PLC0415 - n8n MCP helpers, loaded only when this runs for real
            rows = rows or store_job._rows
            add_row = add_row or store_job._add_row
        self.ask = Asker(job, self.s.get("chat", ""), send=send or _sender(tok), rows=rows, state=self.s, save=self.save,
                         sleep=sleep or time.sleep, clock=clock or time.monotonic, add_row=add_row)
        self._progress = progress
        self.watch: Path | None = None      # the watcher's verdict for this round (<job>/watch/<gate>.verdict.json)

    def save(self) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.s, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    @property
    def progress(self):
        if self._progress is None:
            from page_builder.progress import PageProgress  # noqa: PLC0415
            self._progress = PageProgress(self.dir / "progress.json", token=self.tok, stages=STAGES, units=UNITS)
        return self._progress

    def logged(self, action: str, by: str, ok: bool, note: str = "") -> None:
        row = {"at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "tier": 2, "mode": "approve", "target": self.job,
               "action": action, "result": "success" if ok else "blocked", "approved_by": f"{by} (Telegram Approve)" if ok else "",
               "asked_for_changes_by": "" if ok else by, "note": note[:500]}
        if self.log:
            self.log(row)
            return
        self.dir.mkdir(parents=True, exist_ok=True)
        with (self.dir / "action-log.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    # ---- commands
    def start(self, chat: str, title: str) -> int:
        if not self.s.get("chat"):
            self.s.update(job=self.job, chat=str(chat or ""), title=title)
            self.ask.chat = self.s["chat"]
            self.save()
            self.out(self.progress.start(self.s["chat"], title))
        else:
            self.out("already started")
        return 0

    def step(self, stage: str, done: int, total: int) -> int:
        self.out(self.progress.step(stage, done, total))
        return 0

    def tell(self, text: str) -> int:
        self.ask.tell(text)
        return 0

    def _sent(self, key: str) -> bool:
        return bool(self.s.setdefault("shown", {}).get(key))

    def _shown(self, key: str) -> None:
        self.s["shown"][key] = True
        self.save()

    def review(self, kind: str, rnd: int, show, minutes: float, watch: Path | None = None) -> int:
        """Show the thing once (with the watcher's card first, when there is a verdict), then Approve / Change something, then
        (Change) what to change. A BLOCKED verdict is never shown to a person: the maker fixes it first (dtj-reel-watcher)."""
        key, how = f"{kind}{rnd}", f"{kind}{rnd}n"
        verdict = json.loads(watch.read_text(encoding="utf-8")) if watch and watch.exists() else None
        if verdict and verdict.get("verdict") == "block":
            self.out(json.dumps({"error": "the watcher blocked this round: fix the blocking issues first", "blocking": verdict.get("blocking", [])},
                                ensure_ascii=False))
            return 2
        if not self._sent(key):
            if verdict:
                self.ask.tell(card(verdict))
            show()
            self._shown(key)
        got = self.ask.choose(key, f"{WHAT[kind].capitalize()} (round {rnd}): Approve, or tap Change something.\n"
                                   f"Approve = {NEXT[kind]}.", REVIEW, minutes)
        if not got:
            return WAITING
        if got["value"] == "yes":
            self.logged(f"approve {WHAT[kind]} round {rnd}", got["by"], True)
            self.out(json.dumps({"ok": True, "by": got["by"]}, ensure_ascii=False))
            return 0
        note = self.ask.type_in(how, REDO_HOW[kind], minutes)
        if not note:
            return WAITING
        self.logged(f"changes to {WHAT[kind]} round {rnd}", note["by"], False, note["value"])
        self.out(json.dumps({"ok": False, "by": note["by"], "note": note["value"]}, ensure_ascii=False))
        return 0

    def plan(self, file: Path, rnd: int, minutes: float) -> int:
        text = file.read_text(encoding="utf-8").strip()

        def show():
            for start in range(0, len(text), 3800):        # Telegram's message limit is 4096
                self.ask.tell(text[start:start + 3800])
        return self.review("plan", rnd, show, minutes, self.watch)

    def pictures(self, folder: Path, names: list[str], rnd: int, minutes: float) -> int:
        files = [folder / n for n in names] if names else sorted(p for p in folder.iterdir()
                                                                if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"))
        missing = [str(p) for p in files if not p.exists()]
        if missing:
            self.out(json.dumps({"error": "missing pictures", "files": missing}))
            return 2

        def show():
            sent = self.media.album(self.tok, self.s.get("chat", ""), files, [f"{i + 1}. {p.stem}" for i, p in enumerate(files)])
            if len(sent) < len(files):
                self.ask.tell(f"Telegram took {len(sent)} of {len(files)} pictures; the rest are on the VPS in {folder}.")
        return self.review("pictures", rnd, show, minutes, self.watch)

    def final(self, file: Path, rnd: int, minutes: float) -> int:
        if not file.exists():
            self.out(json.dumps({"error": "no such reel", "file": str(file)}))
            return 2

        def show():
            got = self.media.video(self.tok, self.s.get("chat", ""), file, f"{self.s.get('title', 'Reel')}: round {rnd}")
            if not got:
                self.ask.tell(f"The video did not reach Telegram; it is on the VPS: {file}")
        return self.review("final", rnd, show, minutes, self.watch)

    def person(self, what: str, rnd: int, minutes: float) -> int:
        key = f"person{rnd}"
        got = self.ask.choose(key, f"A person is needed: {what}\nTap Done when it is done; the reel then goes on by itself.",
                              DONE, minutes)
        if not got:
            return WAITING
        self.out(json.dumps({"ok": True, "by": got["by"]}, ensure_ascii=False))
        return 0

    def photos(self, ids: list[str], out: Path) -> int:
        """Photos sent to the reel bot (tg:<file_id> in the request) downloaded into the job's inputs."""
        got, failed = [], []
        for fid in ids:
            fid = fid.removeprefix("tg:")
            p = self.media.download(self.tok, fid, out)
            (got if p else failed).append(str(p) if p else fid[-12:])
        self.out(json.dumps({"saved": got, "failed": failed}))
        return 0 if got and not failed else 1

    def finish(self, ok: bool, note: str) -> int:
        self.out(self.progress.finish(ok, note))
        return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["start", "step", "plan", "pictures", "final", "person", "tell", "photos", "finish"])
    ap.add_argument("--job", required=True, help="r<dtj_reel_jobs row id>")
    ap.add_argument("--chat", default="")
    ap.add_argument("--title", default="")
    ap.add_argument("--stage", default="")
    ap.add_argument("--done", type=int, default=0)
    ap.add_argument("--total", type=int, default=0)
    ap.add_argument("--file", type=Path)
    ap.add_argument("--dir", type=Path)
    ap.add_argument("--files", default="")
    ap.add_argument("--round", type=int, default=1)
    ap.add_argument("--what", default="")
    ap.add_argument("--text", default="")
    ap.add_argument("--ids", default="", help="photos: tg:<file_id> list, comma separated")
    ap.add_argument("--out", type=Path, help="photos: where to save them")
    ap.add_argument("--ok", action="store_true")
    ap.add_argument("--stopped", action="store_true")
    ap.add_argument("--note", default="")
    ap.add_argument("--minutes", type=float, default=MINUTES)
    ap.add_argument("--watch", type=Path, help="the watcher's verdict for this round (tools/vps/watcher.sh)")
    a = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    j = ReelJob(a.job)
    j.watch = a.watch
    if a.command != "start" and not j.s.get("chat"):
        print(json.dumps({"error": "run start first (no chat for this job)"}))
        return 2
    if a.command == "start":
        return j.start(a.chat, a.title or f"Reel {a.job}")
    if a.command == "step":
        return j.step(a.stage, a.done, a.total)
    if a.command == "plan":
        return j.plan(a.file, a.round, a.minutes)
    if a.command == "pictures":
        return j.pictures(a.dir, [n for n in a.files.split(",") if n], a.round, a.minutes)
    if a.command == "final":
        return j.final(a.file, a.round, a.minutes)
    if a.command == "person":
        return j.person(a.what, a.round, a.minutes)
    if a.command == "tell":
        return j.tell(a.text)
    if a.command == "photos":
        return j.photos([i for i in a.ids.split(",") if i], a.out)
    return j.finish(a.ok and not a.stopped, a.note)


if __name__ == "__main__":
    raise SystemExit(main())
