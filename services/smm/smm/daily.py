"""The daily run (GitHub Actions, every hour from morning to night, India time). No AI here: plain code.

For every post whose time has come (and is less than 20 hours late):
  - not approved, or changed after its approval -> not posted; the team is told once;
  - approved, and code may post on the platform (kill switch on, SMM_MODE=approve, platform in SMM_LIVE_PLATFORMS, not a dry
    run, its tokens set) -> posted; the live link is saved, logged and sent to Telegram;
  - approved, but code may not post there -> the picture and the exact words go to Telegram for a person to post by hand.
A failed try is retried on the next run; after 3 failed runs it stops and alerts with the error.
It also warns once when one of the next 3 days has no approved post, so the daily rhythm doesn't break silently.

    python -m smm daily [--store DIR] [--now 2026-10-21T19:05:00+05:30] [--no-push]
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Mapping

from . import media_host
from .actionlog import ActionLog
from .config import IST, Config
from .http import Http, PublishError
from .notify import Telegram
from .publishers import Job, missing, publisher
from .store import Store
from .week import Week, final_text, load, publish_time

LATE_LIMIT = timedelta(hours=20)
MAX_FAILURES = 3
NAMES = {"instagram": "Instagram", "facebook": "Facebook", "linkedin": "LinkedIn", "x": "X", "youtube": "YouTube"}


def recent_weeks(store: Store, now: datetime, back: int = 2) -> list[Week]:
    names = store.week_names()
    wanted = {(now - timedelta(weeks=i)).strftime("%G-W%V") for i in range(back + 1)} | {(now + timedelta(weeks=1)).strftime("%G-W%V")}
    return [load(store.week_folder(n)) for n in names if n in wanted]


def hand_over_text(post: dict, platform: str, texts: dict[str, str]) -> str:
    when = publish_time(post).strftime("%a %d %b, %H:%M")
    body = "\n\n".join(texts[k] for k in ("title", "caption", "text", "description") if texts.get(k))
    return f"POST BY HAND on {NAMES[platform]} ({post['id']}, due {when} IST)\nCopy the words below exactly:\n\n{body}"


class Daily:
    def __init__(self, cfg: Config, store: Store, env: Mapping[str, str], http: Http | None = None, tg: Telegram | None = None,
                 out=print, publish: Callable | None = None, host: Callable | None = None):
        self.cfg, self.store, self.env, self.out = cfg, store, env, out
        self.http = http or Http()
        self.tg = tg or Telegram(env, cfg.telegram_chat_id, out=out)
        self.log = ActionLog(store.root / "log" / "actions.jsonl")
        self.publish = publish or (lambda platform, job: publisher(platform)(job, self.http, env))
        self.host = host or (lambda path, name, alt: media_host.upload(self.http, env, path, name, alt))
        self.summary: list[str] = []
        self.pictures_sent: set[str] = set()

    def run(self, now: datetime | None = None) -> int:
        now = now or datetime.now(IST)
        if not self.cfg.automation_enabled or not self.cfg.smm_enabled:
            self.out("Kill switch: AUTOMATION_ENABLED or SMM_ENABLED is off. Posts still go to Telegram for a person; code posts nothing.")
        for wk in recent_weeks(self.store, now):
            for post in wk.posts:
                self.handle(wk, post, now)
        self.runway(now)
        if self.summary:
            self.tg.text("DTJ social posts, " + now.strftime("%a %d %b %H:%M") + " IST\n\n" + "\n".join(self.summary))
        return 0

    def handle(self, wk: Week, post: dict, now: datetime) -> None:
        due = publish_time(post)
        if due > now:
            return
        pid = post["id"]
        todo = [pl for pl in sorted(post["platforms"]) if not (self.store.path(wk.name, "published", pid, pl).exists()
                                                               or self.store.path(wk.name, "handed", pid, pl).exists())]
        if not todo:
            return
        if now - due > LATE_LIMIT:
            if self.store.notice_once(f"late-{pid}"):
                self.summary.append(f"MISSED {pid}: due {due:%a %d %b %H:%M}, not posted on {', '.join(NAMES[p] for p in todo)}. "
                                    "It is too late to post it as planned; a person decides.")
            return
        approval = self.store.read(self.store.path(wk.name, "approvals", pid))
        if not approval or approval.get("revoked"):
            if self.store.notice_once(f"unapproved-{pid}"):
                self.summary.append(f"NOT POSTED {pid}: nobody has approved it yet (python -m smm approve ...).")
                self.log.record(tier=2, mode=self.cfg.mode, target=pid, action="post", reason="no approval", result="blocked")
            return
        if approval["fingerprint"] != wk.fingerprint(post):
            if self.store.notice_once(f"changed-{pid}-{wk.fingerprint(post)[:12]}"):
                self.summary.append(f"NOT POSTED {pid}: it changed after {approval['approved_by']} approved it. It needs a new yes.")
                self.log.record(tier=2, mode=self.cfg.mode, target=pid, action="post", reason="changed after approval",
                                result="blocked", approved_by=approval["approved_by"])
            return
        urls: list[str] = []

        def public_urls() -> list[str]:
            if not urls:
                urls.extend(self.host(wk.media_path(m), f"dtj-social-{pid}-{i + 1}{wk.media_path(m).suffix}", m["alt"])
                            for i, m in enumerate(post["media"]))
            return urls

        for platform in todo:
            self.one(wk, post, platform, approval, public_urls)

    def one(self, wk: Week, post: dict, platform: str, approval: dict, public_urls) -> None:
        pid = post["id"]
        texts = final_text(post, platform, self.cfg.audit_url)
        n = post["platforms"][platform].get("first_media") or len(post["media"])
        files = [wk.media_path(m) for m in post["media"][:n]]
        decision = self.cfg.may_post(platform, approval["approved_by"])
        lacking = missing(platform, self.env) if decision.allowed else []
        if not decision.allowed or lacking:
            reason = decision.reason if not decision.allowed else f"{NAMES[platform]} is not connected yet ({', '.join(lacking)} not set)"
            if files and pid not in self.pictures_sent:   # the picture once per post, then the words for each platform
                self.tg.files(files, hand_over_text(post, platform, texts))
                self.pictures_sent.add(pid)
            else:
                self.tg.text(hand_over_text(post, platform, texts))
            self.store.write(self.store.path(wk.name, "handed", pid, platform),
                             {"at": datetime.now(timezone.utc).isoformat(), "reason": reason, "texts": texts})
            self.log.record(tier=2, mode=self.cfg.mode, target=f"{pid} {platform}", action="hand to a person", reason=reason,
                            result="dry_run" if self.cfg.dry_run else "recommended", approved_by=approval["approved_by"],
                            approved_at=approval["approved_at"])
            self.summary.append(f"{NAMES[platform]}: {pid} sent above for a person to post ({reason}).")
            return
        fail_path = self.store.path(wk.name, "failures", pid, platform)
        failures = self.store.read(fail_path) or {"count": 0, "errors": []}
        if failures["count"] >= MAX_FAILURES:
            return
        job = Job(post=post, texts=texts, files=files, alts=[m["alt"] for m in post["media"][:n]],
                  public_urls=lambda: public_urls()[:n])
        try:
            result = self.publish(platform, job)
        except (PublishError, KeyError, ValueError, OSError) as e:
            failures["count"] += 1
            failures["errors"].append({"at": datetime.now(timezone.utc).isoformat(), "error": str(e)[:500]})
            self.store.write(fail_path, failures)
            self.log.record(tier=2, mode="approve", target=f"{pid} {platform}", action="post", reason="approved and due",
                            result="failed", error=str(e)[:500], approved_by=approval["approved_by"], approved_at=approval["approved_at"])
            if failures["count"] >= MAX_FAILURES:
                self.summary.append(f"STOPPED {NAMES[platform]} {pid}: failed {MAX_FAILURES} times. Last error: {str(e)[:300]}. "
                                    "The post and its files are kept; a person checks the platform login and posts it by hand.")
            else:
                self.summary.append(f"{NAMES[platform]}: {pid} failed (try {failures['count']} of {MAX_FAILURES}), next run tries again.")
            return
        self.store.write(self.store.path(wk.name, "published", pid, platform),
                         {"at": datetime.now(timezone.utc).isoformat(), "fingerprint": approval["fingerprint"],
                          "approved_by": approval["approved_by"], **result})
        self.log.record(tier=2, mode="approve", target=f"{pid} {platform}", action="post", reason="approved and due", result="success",
                        approved_by=approval["approved_by"], approved_at=approval["approved_at"], after={"id": result["id"], "url": result.get("url")},
                        evidence={"fingerprint": approval["fingerprint"]})
        self.summary.append(f"POSTED on {NAMES[platform]}: {pid} {result.get('url', '')}".rstrip()
                            + (f"\n  Note: {result['warning']}" if result.get("warning") else ""))

    def runway(self, now: datetime) -> None:
        """Warn once per day when one of the next 3 days has no approved post at all."""
        approved_days = set()
        for wk in recent_weeks(self.store, now):
            for post in wk.posts:
                a = self.store.read(self.store.path(wk.name, "approvals", post["id"]))
                if a and not a.get("revoked"):
                    approved_days.add(publish_time(post).date())
        gaps = [d for d in ((now + timedelta(days=i)).date() for i in range(1, 4)) if d not in approved_days]
        if gaps and self.store.notice_once(f"runway-{now.date()}"):
            self.summary.append("No approved post yet for " + ", ".join(d.strftime("%a %d %b") for d in gaps)
                                + ". Make and approve the next posts so DTJ keeps posting daily.")
        expires = (self.env.get("LINKEDIN_TOKEN_EXPIRES") or "").strip()
        if expires:
            try:
                left = (datetime.fromisoformat(expires).date() - now.date()).days
            except ValueError:
                left = None
            if left is not None and left <= 10 and self.store.notice_once(f"linkedin-token-{now.date()}"):
                self.summary.append(f"The LinkedIn login ends in {left} days: a page admin signs in again and updates LINKEDIN_TOKEN.")
