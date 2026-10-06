"""Settings and the permission gate. Reads environment variables only (never .env files)."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Mapping

_TRUE = {"1", "true", "yes", "on"}
_DOMAIN = re.compile(r"^[a-z0-9][a-z0-9-]*\.myshopify\.com$")


class ConfigError(Exception):
    pass


def _flag(env: Mapping[str, str], name: str, default: bool) -> bool:
    value = env.get(name)
    return default if value is None else value.strip().lower() in _TRUE


@dataclass(frozen=True)
class Decision:
    allowed: bool
    reason: str


@dataclass(frozen=True)
class Config:
    automation_enabled: bool  # kill switch, default OFF
    dry_run: bool  # default ON
    mode: str  # "shadow" or "approve". Tier 2 never becomes "auto".
    api_version: str | None  # must be pinned before any live call
    store_domain: str | None
    client_id: str | None

    def token_env_name(self) -> str:
        if not self.client_id:
            raise ConfigError("CLIENT_ID is not set")
        return "SHOPIFY_ADMIN_TOKEN_" + re.sub(r"[^A-Z0-9]", "_", self.client_id.upper())

    def admin_token(self, env: Mapping[str, str] | None = None) -> str:
        """Fetched at call time, never stored on the object, never logged."""
        env = os.environ if env is None else env
        token = env.get(self.token_env_name())
        if not token:
            raise ConfigError(f"{self.token_env_name()} is not set")
        return token

    def missing_for_live(self, env: Mapping[str, str] | None = None) -> list[str]:
        env = os.environ if env is None else env
        missing = []
        if not self.automation_enabled:
            missing.append("AUTOMATION_ENABLED is off (kill switch)")
        if self.dry_run:
            missing.append("DRY_RUN is on")
        if not self.api_version:
            missing.append("SHOPIFY_API_VERSION is not pinned")
        if not self.store_domain:
            missing.append("SHOPIFY_DOMAIN is not set")
        if self.client_id and not env.get(self.token_env_name()):
            missing.append(f"{self.token_env_name()} is not set")
        return missing

    def decide(self, tier: int, approved_by: str | None = None) -> Decision:
        """May an action of this tier run now? Tier 0 reads are always fine."""
        if tier <= 0:
            return Decision(True, "tier 0 read only")
        if tier >= 3:
            return Decision(False, "tier 3 is forbidden")
        if not self.automation_enabled:
            return Decision(False, "kill switch is off")
        if self.dry_run:
            return Decision(False, "dry run: nothing is changed")
        if self.mode == "shadow":
            return Decision(False, "shadow mode: recommend only")
        if tier == 2 and not approved_by:
            return Decision(False, "tier 2 needs a named approver for this action")
        return Decision(True, "allowed")


def load(env: Mapping[str, str] | None = None) -> Config:
    env = os.environ if env is None else env
    mode = env.get("AUTOMATION_MODE", "shadow").strip().lower()
    if mode not in ("shadow", "approve"):
        raise ConfigError(f"AUTOMATION_MODE must be shadow or approve, got {mode!r}")
    domain = (env.get("SHOPIFY_DOMAIN") or "").strip().lower() or None
    if domain and not _DOMAIN.match(domain):
        raise ConfigError("SHOPIFY_DOMAIN must look like name.myshopify.com")
    return Config(
        automation_enabled=_flag(env, "AUTOMATION_ENABLED", False),
        dry_run=_flag(env, "DRY_RUN", True),
        mode=mode,
        api_version=(env.get("SHOPIFY_API_VERSION") or "").strip() or None,
        store_domain=domain,
        client_id=(env.get("CLIENT_ID") or "").strip() or None,
    )
