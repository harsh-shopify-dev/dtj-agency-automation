"""Settings and the permission gate for DTJ's social media automation. Reads environment variables only (never .env files).

    AUTOMATION_ENABLED   master kill switch, default OFF: nothing is posted
    SMM_ENABLED          this automation's own switch, default OFF
    SMM_DRY_RUN          default ON: say what would be posted, post nothing
    SMM_MODE             shadow (default: the daily run sends today's post to Telegram for a person to post by hand)
                         or approve (code posts each APPROVED post at its time on the platforms in SMM_LIVE_PLATFORMS)
    SMM_LIVE_PLATFORMS   comma list of platforms code may post to, e.g. "instagram,facebook". Every other platform of a post is
                         sent to Telegram as "post by hand" with the file and the caption.
    SMM_AUDIT_URL        the page every post points to (default DTJ's free growth audit)
    SMM_TELEGRAM_CHAT_ID the team chat for the daily message; DTJ_TELEGRAM_BOT_TOKEN the bot (GitHub secret)
    Platform tokens      read at call time by each publisher (see publishers/), never stored on an object or logged.

Posting is Tier 2 (public content): code posts only a post that a named person approved, and only the exact files they approved
(the approval stores a fingerprint of the post and its files). Deleting a live post is Tier 3 and is not in this service at all.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping
from zoneinfo import ZoneInfo

from .platforms import PLATFORMS

IST = ZoneInfo("Asia/Kolkata")
DEFAULT_AUDIT_URL = "https://digitaltusharjoshi.com/free-growth-audit"
_TRUE = {"1", "true", "yes", "on"}


class ConfigError(Exception):
    pass


def _flag(env: Mapping[str, str], name: str, default: bool) -> bool:
    value = env.get(name)
    return default if value is None or value.strip() == "" else value.strip().lower() in _TRUE


@dataclass(frozen=True)
class Decision:
    allowed: bool
    reason: str


@dataclass(frozen=True)
class Config:
    automation_enabled: bool
    smm_enabled: bool
    dry_run: bool
    mode: str  # shadow | approve
    live_platforms: tuple[str, ...]
    audit_url: str
    telegram_chat_id: str

    def may_post(self, platform: str, approved_by: str | None) -> Decision:
        """May code post an approved post on this platform right now?"""
        if not (approved_by or "").strip():
            return Decision(False, "posting is tier 2: it needs a named approver (Harsh, or a DTJ teammate when he can't be reached)")
        if not self.automation_enabled:
            return Decision(False, "kill switch is off (AUTOMATION_ENABLED)")
        if not self.smm_enabled:
            return Decision(False, "SMM is switched off (SMM_ENABLED)")
        if self.mode != "approve":
            return Decision(False, "shadow mode: a person posts it by hand (SMM_MODE)")
        if platform not in self.live_platforms:
            return Decision(False, f"{platform} is not switched on for posting by code (SMM_LIVE_PLATFORMS)")
        if self.dry_run:
            return Decision(False, "dry run: nothing is posted (SMM_DRY_RUN)")
        return Decision(True, f"approved by {approved_by.strip()}")


def load(env: Mapping[str, str] | None = None) -> Config:
    env = os.environ if env is None else env
    mode = (env.get("SMM_MODE") or "shadow").strip().lower()
    if mode not in {"shadow", "approve"}:
        raise ConfigError(f"SMM_MODE must be shadow or approve, not {mode!r}")
    live = tuple(p.strip().lower() for p in (env.get("SMM_LIVE_PLATFORMS") or "").split(",") if p.strip())
    unknown = [p for p in live if p not in PLATFORMS]
    if unknown:
        raise ConfigError(f"SMM_LIVE_PLATFORMS has unknown platforms: {', '.join(unknown)}")
    audit_url = (env.get("SMM_AUDIT_URL") or DEFAULT_AUDIT_URL).strip().rstrip("/")
    if not audit_url.startswith("https://digitaltusharjoshi.com"):
        raise ConfigError("SMM_AUDIT_URL must be a page on https://digitaltusharjoshi.com")
    return Config(automation_enabled=_flag(env, "AUTOMATION_ENABLED", False), smm_enabled=_flag(env, "SMM_ENABLED", False),
                  dry_run=_flag(env, "SMM_DRY_RUN", True), mode=mode, live_platforms=live, audit_url=audit_url,
                  telegram_chat_id=(env.get("SMM_TELEGRAM_CHAT_ID") or "").strip())


def secret(name: str, env: Mapping[str, str] | None = None) -> str:
    """A token, read at call time. Raises if missing; the value is never printed."""
    env = os.environ if env is None else env
    value = (env.get(name) or "").strip()
    if not value:
        raise ConfigError(f"{name} is not set")
    return value
