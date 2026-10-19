"""Settings and the permission gate for the SEO/AEO engine. Reads environment variables only (never .env files).

    AUTOMATION_ENABLED   kill switch, default OFF (nothing that changes anything runs)
    SEO_DRY_RUN          default ON (plan and log, change nothing)
    SEO_MODE             shadow (default: recommend only, drafts stay as files) or approve (drafts go into WordPress as DRAFTS)
    SEO_SITE             the site, default https://digitaltusharjoshi.com
    WP_USER, WP_APP_PASSWORD  a WordPress Editor's application password; read at call time, never stored or logged
    ANTHROPIC_API_KEY    read by the Anthropic SDK itself, never by this code

Publishing pages is not in this service at all: a person presses Publish in WordPress. Live-site SEO fixes are Tier 2:
apply_batch.py writes a batch only with a named approver (Harsh's rule, 14 Oct 2026: approve each week's batch, first month).
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Mapping

_TRUE = {"1", "true", "yes", "on"}
_SITE = re.compile(r"^https://[a-z0-9.-]+$")
DEFAULT_SITE = "https://digitaltusharjoshi.com"


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
    dry_run: bool
    mode: str  # shadow | approve
    site: str

    def wp_credentials(self, env: Mapping[str, str] | None = None) -> tuple[str, str]:
        """Fetched at call time, never kept on the object, never logged."""
        env = os.environ if env is None else env
        user, password = (env.get("WP_USER") or "").strip(), (env.get("WP_APP_PASSWORD") or "").strip()
        if not user or not password:
            raise ConfigError("WP_USER and WP_APP_PASSWORD are not set")
        return user, password

    def decide(self, tier: int, approved_by: str | None = None) -> Decision:
        """May an action of this tier run now? Tier 0 reads always may. Tier 2 here means only an APPROVED fixes batch on the live
        site (apply_batch.py): it needs a named approver every time. Publishing pages is not in this service at all; tier 3 never."""
        if tier <= 0:
            return Decision(True, "tier 0 read only")
        if tier >= 3:
            return Decision(False, "tier 3 is never done")
        if tier == 2:
            if not (approved_by or "").strip():
                return Decision(False, "tier 2 needs a named approver for this batch (Harsh, or a DTJ teammate when he can't be reached)")
            if not self.automation_enabled:
                return Decision(False, "kill switch is off (AUTOMATION_ENABLED)")
            if self.dry_run:
                return Decision(False, "dry run: nothing is changed (SEO_DRY_RUN)")
            return Decision(True, f"approved by {approved_by.strip()}")
        if not self.automation_enabled:
            return Decision(False, "kill switch is off (AUTOMATION_ENABLED)")
        if self.dry_run:
            return Decision(False, "dry run: nothing is changed (SEO_DRY_RUN)")
        if self.mode == "shadow":
            return Decision(False, "shadow mode: the draft stays a file for review (SEO_MODE)")
        return Decision(True, "allowed: WordPress draft only")


def load(env: Mapping[str, str] | None = None) -> Config:
    env = os.environ if env is None else env
    mode = (env.get("SEO_MODE") or "shadow").strip().lower()
    if mode not in ("shadow", "approve"):
        raise ConfigError(f"SEO_MODE must be shadow or approve, got {mode!r}")
    site = (env.get("SEO_SITE") or DEFAULT_SITE).strip().rstrip("/").lower()
    if not _SITE.match(site):
        raise ConfigError("SEO_SITE must look like https://example.com")
    return Config(
        automation_enabled=_flag(env, "AUTOMATION_ENABLED", False),
        dry_run=_flag(env, "SEO_DRY_RUN", True),
        mode=mode,
        site=site,
    )
