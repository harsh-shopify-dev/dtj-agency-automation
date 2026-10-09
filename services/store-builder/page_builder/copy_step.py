"""The Claude API copy step: rewrites the page's STRUCTURAL signposts ("Why choose X?", "How it works") in the brand's voice, inside the
contract in copy_contract.py. Fact text (benefits, steps, answers, reviews, figures) is never sent for rewriting and can never be changed.

Unattended runs use the Claude API with an API KEY (ANTHROPIC_API_KEY in the environment, filled from the vault), never a subscription
login. The SDK reads the key; this module never reads, prints, stores or logs it.

    from page_builder.copy_step import run_copy_step, make_client
    outcome = run_copy_step(brand, facts)                          # dry run: builds the exact request, calls nothing, costs nothing
    outcome = run_copy_step(brand, facts, client=make_client())    # live: ONE API call, every line checked by code

Whatever goes wrong (a refusal, a cut-off answer, an API error, bad JSON, a line that breaks a rule, a page that fails lint), the page stays
valid: a missing or rejected line keeps the template wording, and a rewritten page that fails lint falls back to the page without rewrites.
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path

from . import copy_contract
from .assemble import Result, build_pdp

HERE = Path(__file__).resolve().parent
MODEL = "claude-opus-5-5"
EFFORT = "medium"  # short signposts; raise it only when an eval shows better lines at a higher level
MAX_TOKENS = 16000  # thinking cannot be switched off on this model, so leave it room; the answer itself is a few hundred tokens
FALLBACK_BETA = "server-side-fallback-2026-07-01"  # on a safety decline, Anthropic re-runs the request on its recommended model
# Listed API prices in USD per million tokens (Claude API skill model table, cached 6 Oct 2026). Used only to report what a run cost;
# check the pricing page before quoting a bill. A run served by another model (a fallback) is reported without a cost.
PRICES = {"claude-opus-5-5": {"input": 4.00, "output": 20.00, "cache_read": 0.20}}


def system_prompt() -> str:
    return (HERE / "prompts" / "system.md").read_text(encoding="utf-8")


def prompt_version() -> str:
    """A short fingerprint of everything that shapes the model's answer, so a report always says which prompt produced which lines."""
    h = hashlib.sha256()
    h.update(system_prompt().encode("utf-8"))
    h.update((HERE / "copy_contract.py").read_bytes())
    h.update(MODEL.encode() + EFFORT.encode())
    return h.hexdigest()[:12]


def response_schema(slots: list[dict]) -> dict:
    """The JSON shape the model must answer in. Structured outputs accept only closed objects (additionalProperties false) and no length
    limits, so the schema is built per page: one required text per slot. The 48-character limit and every other rule are enforced
    afterwards by copy_contract.validate_response, which is the real gate."""
    names = [s["slot"] for s in slots]
    return {
        "type": "object", "additionalProperties": False, "required": ["slots"],
        "properties": {"slots": {"type": "object", "additionalProperties": False, "required": names,
                                 "properties": {n: {"type": "string"} for n in names}}},
    }


def request_params(first: Result, *, model: str = MODEL, effort: str = EFFORT, fallbacks: bool = True) -> dict:
    """The exact keyword arguments of the API call (no key in here: the client carries it)."""
    req = copy_contract.build_request(first)
    req.pop("response_schema", None)  # the API receives the closed per-page schema in output_config instead
    params = {
        "model": model,
        "max_tokens": MAX_TOKENS,
        "system": system_prompt(),
        "messages": [{"role": "user", "content": json.dumps(req, ensure_ascii=False, indent=1)}],
        "output_config": {"effort": effort, "format": {"type": "json_schema", "schema": response_schema(req["slots"])}},
    }
    if fallbacks:
        params["betas"] = [FALLBACK_BETA]
        params["fallbacks"] = "default"
    return params


@dataclass
class CopyOutcome:
    result: Result  # the page to use (with the accepted rewrites, or the template wording)
    mode: str  # dry-run | live
    status: str  # not-run | no-slots | applied | no-changes | refusal | cut-off | api-error | bad-json | lint-fallback
    accepted: dict = field(default_factory=dict)  # slot -> new text, applied to the page
    rejected: dict = field(default_factory=dict)  # slot -> reason the line was refused (the template wording stays)
    params: dict = field(default_factory=dict)
    slots_sent: int = 0
    usage: dict = field(default_factory=dict)
    served_by: str | None = None
    request_id: str | None = None
    cost_usd: float | None = None
    seconds: float | None = None
    error: str | None = None
    lint_errors: list = field(default_factory=list)

    def as_report(self) -> dict:
        return {
            "mode": self.mode, "status": self.status, "model": self.params.get("model"), "effort": self.params.get("output_config", {}).get("effort"),
            "prompt_version": prompt_version(), "served_by": self.served_by, "request_id": self.request_id,
            "slots_sent": self.slots_sent, "accepted": self.accepted, "rejected": self.rejected, "usage": self.usage,
            "cost_usd": self.cost_usd, "cost_source": "listed per-token prices x reported usage" if self.cost_usd is not None else None,
            "seconds": self.seconds, "error": self.error, "lint_errors": self.lint_errors,
        }


def make_client():
    """A live client. The SDK reads ANTHROPIC_API_KEY from the environment; it is never passed, printed or logged here."""
    import anthropic  # only needed for a live run: pip install anthropic

    return anthropic.Anthropic()


def _usage(resp) -> dict:
    u = getattr(resp, "usage", None)
    keys = ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")
    return {k: int(getattr(u, k, 0) or 0) for k in keys} if u is not None else {}


def _cost(model: str | None, usage: dict) -> float | None:
    p = PRICES.get(model or "")
    if not p or not usage or usage.get("cache_creation_input_tokens"):
        return None  # unknown model price, or a cache write whose price is not in the table: report tokens only
    total = usage["input_tokens"] * p["input"] + usage["output_tokens"] * p["output"] + usage["cache_read_input_tokens"] * p["cache_read"]
    return round(total / 1_000_000, 6)


def run_copy_step(brand: dict, facts: dict, *, client=None, model: str = MODEL, effort: str = EFFORT, fallbacks: bool = True,
                  first: Result | None = None, **build_kw) -> CopyOutcome:
    first = first or build_pdp(brand, facts, **build_kw)
    params = request_params(first, model=model, effort=effort, fallbacks=fallbacks)
    slots = copy_contract.list_slots(first)
    if not slots:
        return CopyOutcome(first, "dry-run" if client is None else "live", "no-slots", params=params)
    if client is None:
        return CopyOutcome(first, "dry-run", "not-run", params=params, slots_sent=len(slots))

    started = time.monotonic()
    out = CopyOutcome(first, "live", "api-error", params=params, slots_sent=len(slots))
    try:
        create = client.beta.messages.create if fallbacks else client.messages.create
        resp = create(**params)
    except Exception as exc:  # noqa: BLE001 - the SDK has already retried 429/5xx; any failure here means "keep the template wording"
        out.error = f"{type(exc).__name__}: {str(exc)[:300]}"
        out.seconds = round(time.monotonic() - started, 2)
        return out

    out.seconds = round(time.monotonic() - started, 2)
    out.usage = _usage(resp)
    out.served_by = getattr(resp, "model", None)
    out.request_id = getattr(resp, "_request_id", None) or getattr(resp, "id", None)
    out.cost_usd = _cost(out.served_by, out.usage)
    stop = getattr(resp, "stop_reason", None)
    if stop == "refusal":
        out.status = "refusal"
        return out
    if stop == "max_tokens":
        out.status = "cut-off"
        return out
    text = next((b.text for b in getattr(resp, "content", []) or [] if getattr(b, "type", None) == "text"), None)
    try:
        data = json.loads(text) if text else None
    except (TypeError, ValueError):
        data = None
    if not isinstance(data, dict):
        out.status = "bad-json"
        return out

    accepted, rejected = copy_contract.validate_response(first, data)
    current = {s["slot"]: s["current"] for s in slots}
    changed = {k: v for k, v in accepted.items() if v != current.get(k)}  # an unchanged line is not a rewrite: keep its true origin
    out.rejected = rejected
    if not changed:
        out.status = "no-changes"
        return out
    final = build_pdp(brand, facts, copy_overrides=changed, **build_kw)
    if not final.ok:
        out.status = "lint-fallback"
        out.lint_errors = [f for f in final.report["lint"] if f["severity"] == "error"] + [{"problem": p} for p in final.report["problems"]]
        return out
    out.result, out.accepted, out.status = final, changed, "applied"
    return out
