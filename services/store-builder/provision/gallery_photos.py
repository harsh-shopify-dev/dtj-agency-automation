"""Make every photo of a page's picture plan at once, a few at a time, so a session starts it in the background and goes on with
the facts, the copy and the design meanwhile.

Harsh, 24 Oct 2026: "i want such tasks to go parallely currently the full focus was on image generation instead you could have
started designing the page parallely or writing copy to save time". One command for the whole plan (the gallery's photos and the
section photos), WORKERS pictures at the same time (Codex on the VPS took 60-125 s per picture on 24 Oct 2026; 12 pictures in about
6 minutes), each through ai_images.make (the same guard, references and sidecars). Results land in <out>/photos.json as they finish,
so the session can look at the first ones while the rest are still being made.

    python -m provision.gallery_photos --plan <client>/gallery/plan.json --out <client>/gallery/photos [--only a,b] [--workers 3]
        --detach      start it in its own process and return at once (the session writes the facts and the copy meanwhile)
        --wait        later: block until every photo of the plan is made or failed (--timeout seconds, default 1800)
        --progress <client>/progress.json   move the page's Telegram bar ("pictures: picture N of M") as each photo finishes
    plan.json: {"refs": ["<a photo of our product>"],
                "photos": [{"name": "p-pack", "kind": "studio", "prompt": "...", "ref": true, "transparent": false}, ...]}
    "ref": true uses the plan's refs, a list names its own, false or missing uses none. "kind" defaults to studio.
Exit 0 = every photo made, 1 = some were not (each reason is in photos.json and printed), 2 = the plan is wrong or a prompt was
refused (nothing is made).
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from provision import ai_images  # noqa: E402

WORKERS = 3  # Codex on one ChatGPT account: three at a time worked on 23-24 Oct 2026 without a limit message


def _refs(photo: dict, plan: dict, base: Path) -> list[Path]:
    ref = photo.get("ref")
    names = plan.get("refs", []) if ref is True else (ref if isinstance(ref, list) else [])
    return [Path(r) if Path(r).is_absolute() else base / r for r in names]


def check(plan: dict, base: Path) -> list[dict]:
    """The photos to make, every prompt guarded first: ValueError names each refused one, and then nothing is made."""
    photos = plan.get("photos") or []
    if not photos:
        raise ValueError("the plan has no photos")
    names = [p.get("name") or "" for p in photos]
    if "" in names or len(set(names)) != len(names):
        raise ValueError("every photo needs its own name")
    why = []
    for p in photos:
        try:
            ai_images.guard(p.get("prompt", ""), p.get("kind", "studio"), refs=bool(_refs(p, plan, base)))
        except ValueError as exc:
            why.append(f"{p['name']}: {str(exc).removeprefix('refused: ')}")
    if why:
        raise ValueError("refused: " + "; ".join(why))
    return photos


def make_all(plan: dict, out: Path, base: Path, only: set[str] | None = None, workers: int = WORKERS, make=ai_images.make,
             progress=None) -> list[dict]:
    """progress(done, total): called after each photo (the Telegram bar); it never stops the photos."""
    photos = [p for p in check(plan, base) if not only or p["name"] in only]
    out.mkdir(parents=True, exist_ok=True)
    record = out / "photos.json"
    done: dict[str, dict] = {r["name"]: r for r in (json.loads(record.read_text(encoding="utf-8")) if record.exists() else [])}
    lock, finished_now = threading.Lock(), []

    def one(p: dict) -> dict:
        try:
            side = make(p.get("kind", "studio"), p["prompt"], out / f"{p['name']}.png", refs=_refs(p, plan, base),
                        transparent=bool(p.get("transparent")))
            row = {"name": p["name"], "path": side["path"], "transparent": side.get("transparent")}
        except (ai_images.ImagesError, ValueError, OSError) as exc:
            row = {"name": p["name"], "error": str(exc)[:300]}
        with lock:  # each result is written as soon as it is there: the session can look while the others are made
            done[p["name"]] = row
            record.write_text(json.dumps(list(done.values()), indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
            finished_now.append(p["name"])  # this run's photos only (an earlier run's rows stay in photos.json)
            finished = len(finished_now)
        print(f"{p['name']}: " + (row.get("path") or f"FAILED {row['error']}"), flush=True)
        if progress:
            try:
                progress(finished, len(photos))
            except Exception:  # noqa: BLE001 - the bar is a courtesy: the photos go on
                pass
        return row

    with ThreadPoolExecutor(max(1, workers)) as pool:
        return list(pool.map(one, photos))


def detach(argv: list[str], out: Path, popen=subprocess.Popen) -> int:
    """The same command without --detach in its own session (it outlives the shell that started it); its log is <out>/run.log."""
    out.mkdir(parents=True, exist_ok=True)
    args = [a for a in argv if a != "--detach"]
    with (out / "run.log").open("a", encoding="utf-8") as log:
        proc = popen([sys.executable, "-m", "provision.gallery_photos", *args], cwd=str(Path(__file__).resolve().parents[1]),
                     stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, start_new_session=True)
    (out / "running.json").write_text(json.dumps({"pid": proc.pid, "started": time.time()}) + "\n", encoding="utf-8")
    print(f"started in the background (pid {proc.pid}): results land in {out / 'photos.json'} as they finish; "
          f"later run the same command with --wait")
    return 0


def wait(plan: dict, out: Path, timeout: float, sleep=time.sleep, clock=time.time, alive=None) -> int:
    """Until every photo of the plan has a row in photos.json, or the maker stopped, or the time is up."""
    names = {p["name"] for p in plan.get("photos") or []}
    alive = alive or _alive
    end = clock() + timeout
    while True:
        rows = json.loads((out / "photos.json").read_text(encoding="utf-8")) if (out / "photos.json").exists() else []
        have = {r["name"]: r for r in rows if r["name"] in names}
        if len(have) == len(names) or not alive(out) or clock() >= end:
            break
        sleep(10)
    made = [n for n in names if "path" in have.get(n, {})]
    failed = {n: have[n]["error"] for n in names if "error" in have.get(n, {})}
    missing = sorted(names - set(have))
    print(json.dumps({"made": sorted(made), "failed": failed, "not_finished": missing}, indent=1, ensure_ascii=False))
    return 0 if len(made) == len(names) else 1


def _alive(out: Path) -> bool:
    try:
        pid = json.loads((out / "running.json").read_text(encoding="utf-8"))["pid"]
        os.kill(pid, 0)
        return True
    except (OSError, ValueError, KeyError):
        return False


def _bar(state: str):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from page_builder.progress import PageProgress  # noqa: PLC0415
    return lambda done, total: PageProgress(state).step("pictures", done, total)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--plan", required=True, help="plan.json (refs relative to its folder)")
    ap.add_argument("--out", required=True, help="the folder for the photos and photos.json")
    ap.add_argument("--only", default="", help="comma-separated names: make only these again (a failed or rejected photo)")
    ap.add_argument("--workers", type=int, default=WORKERS)
    ap.add_argument("--detach", action="store_true", help="start in the background and return at once")
    ap.add_argument("--wait", action="store_true", help="wait until every photo of the plan is made or failed")
    ap.add_argument("--timeout", type=float, default=1800, help="--wait: the most seconds to wait")
    ap.add_argument("--progress", help="the page's progress.json: the Telegram bar moves as photos finish")
    a = ap.parse_args(argv)
    plan_path = Path(a.plan)
    try:
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        if a.wait:
            return wait(plan, Path(a.out), a.timeout)
        check(plan, plan_path.parent)  # a refused prompt stops here, also before --detach
        if a.detach:
            return detach(argv, Path(a.out))
        rows = make_all(plan, Path(a.out), plan_path.parent, set(filter(None, a.only.split(","))) or None, a.workers,
                        progress=_bar(a.progress) if a.progress else None)
    except (OSError, ValueError) as exc:
        print(f"REFUSED, nothing made: {str(exc).removeprefix('refused: ')}")
        return 2
    return 0 if all("path" in r for r in rows) else 1


if __name__ == "__main__":
    sys.exit(main())
