"""The Claude API plan step: Claude decides WHICH sections the product page uses, in WHAT order, which one is emphasised, and fills the
brand style choices the client left open. Code stays the gate: only sections the client's facts can fill are built, every colour is
contrast-checked by direction.py, every text is a sourced fact or a validated signpost, and anything the plan gets wrong is corrected
and reported (never silently).

    from page_builder.ai_plan import run_plan_step
    outcome = run_plan_step(brand, facts)                                   # dry run: builds the exact request, calls nothing
    outcome = run_plan_step(brand, facts, client=make_client(),             # live: ONE API call
                            references=[Path("ref1.png")])                  # optional pages the agency likes (inspiration only)
    result = build_pdp(outcome.brand, facts, plan=outcome.plan)             # plan is None when the step did not run or failed: the
                                                                            # house rules (recipes/pdp.json) decide instead

Same API conventions as copy_step.py: API key from the environment only (never read, printed or logged here), structured output,
server-side fallback on a safety decline, refusal and cut-off handled, usage and cost reported.
"""
from __future__ import annotations

import base64
import copy
import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path

from . import direction as direction_mod
from . import niches, sections
from .catalog import Catalog
from .copy_step import EFFORT, FALLBACK_BETA, MAX_TOKENS, MODEL, _cost, _usage

HERE = Path(__file__).resolve().parent
SIGNATURES = ("proof_panel", "free_from_band", "story_card")
CHOICES = {  # brand style choices the plan may fill when the client left them open ("keep" = leave as the client/category has it)
    "price_tier": ("value", "mid", "premium"),
    "voice": ("plain", "warm", "clinical", "playful", "luxe"),
    "shape_language": ("sharp", "soft", "round"),
    "heading_class": ("theme", "sans", "serif"),
}
BLOCKS = {  # which of our app blocks each section is built from
    "trust_marquee": ["dtj-sections/marquee"],
    "why_features": ["dtj-sections-2/feature-showcase"],
    "facts_glance": ["dtj-sections/science-stats", "dtj-sections-2/stat-cards (when every figure has a picture)"],
    "story_split": ["dtj-sections-2/split-story"],
    "how_split": ["dtj-sections-2/split-story"],
    "proof_panel": ["dtj-sections-2/measured-results"],
    "pack_inside": ["dtj-sections/whats-inside"],
    "free_from": ["dtj-sections/whats-not-inside"],
    "comparison": ["dtj-sections/comparison-table"],
    "reviews_slider": ["dtj-sections/testimonials-slider"],
    "faq": ["dtj-sections/faq"],
}
SAME_FIGURES = ("proof_panel", "facts_glance")  # two styles of the same numbers: a page uses at most one
IMAGE_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp", ".gif": "image/gif"}
MAX_REFERENCES = 5
MAX_IMAGE_BYTES = 4_500_000  # below the API's 5 MB per-image limit


class ReferenceImageError(ValueError):
    pass


def system_prompt() -> str:
    return (HERE / "prompts" / "plan_system.md").read_text(encoding="utf-8")


def prompt_version() -> str:
    h = hashlib.sha256()
    h.update(system_prompt().encode("utf-8"))
    h.update(Path(__file__).read_bytes())
    h.update(reference_notes().encode("utf-8"))
    h.update(MODEL.encode() + EFFORT.encode())
    return h.hexdigest()[:12]


def _recipe() -> dict:
    return json.loads((HERE / "recipes" / "pdp.json").read_text(encoding="utf-8"))


def house_order(category: str) -> list[str]:
    r = _recipe()
    return r.get("overrides", {}).get(category, {}).get("order") or [e["builder"] for e in r["sections"]]


def not_set(brand: dict) -> list[str]:
    out = [k for k in ("price_tier", "voice", "shape_language") if not brand.get(k)]
    if not (brand.get("fonts") or {}).get("heading_class"):
        out.append("heading_class")
    return out


def menu(brand: dict, facts: dict, catalog: Catalog | None = None) -> list[dict]:
    """Every section Claude may choose, with whether the client's facts can fill it now. Availability is decided by running the real
    builder on a scratch context, so the menu can never promise a section the builder would refuse."""
    cat = catalog or Catalog()
    d = direction_mod.derive(brand)
    purpose = {e["builder"]: e["why"] for e in _recipe()["sections"]}
    items = []
    for name, build in ((n, b) for n, b in sections.BUILDERS.items() if n in BLOCKS):  # the plan step's menu: the pdp recipe's sections
        res = build(sections.Ctx(brand, facts, d, cat))
        item = {"section": name, "what_it_is_for": purpose.get(name, ""), "blocks": niches.order_blocks(BLOCKS[name], brand["category"]),  # best fit for the niche first
                "available": not isinstance(res, sections.Omit)}
        if isinstance(res, sections.Omit):
            item["why_not"] = res.reason
        items.append(item)
    return items


def load_references(paths) -> list[dict]:
    """Image content blocks for the reference pages. Refuses (rather than silently skipping) anything it cannot send."""
    paths = [Path(p) for p in paths or []]
    if len(paths) > MAX_REFERENCES:
        raise ReferenceImageError(f"at most {MAX_REFERENCES} reference images per plan (got {len(paths)})")
    blocks = []
    for p in paths:
        media = IMAGE_TYPES.get(p.suffix.lower())
        if not media:
            raise ReferenceImageError(f"{p.name}: use a .png, .jpg, .webp or .gif screenshot")
        data = p.read_bytes()
        if len(data) > MAX_IMAGE_BYTES:
            raise ReferenceImageError(f"{p.name}: {len(data) // 1_000_000} MB is too big; keep each image under 4.5 MB")
        blocks.append({"type": "image", "source": {"type": "base64", "media_type": media, "data": base64.b64encode(data).decode("ascii")}})
    return blocks


def response_schema() -> dict:
    names = [n for n in sections.BUILDERS if n in BLOCKS]
    pick = {"type": "object", "additionalProperties": False, "required": ["section", "why"],
            "properties": {"section": {"type": "string", "enum": names}, "why": {"type": "string"}}}
    return {
        "type": "object", "additionalProperties": False,
        "required": ["sections", "left_out", "signature", "brand_choices", "summary"],
        "properties": {
            "sections": {"type": "array", "items": pick},
            "left_out": {"type": "array", "items": pick},
            "signature": {"type": "string", "enum": list(SIGNATURES)},
            "brand_choices": {"type": "object", "additionalProperties": False, "required": list(CHOICES),
                              "properties": {k: {"type": "string", "enum": ["keep", *v]} for k, v in CHOICES.items()}},
            "summary": {"type": "string"},
        },
    }


REFERENCE_NOTES = HERE / "references"  # written notes on sample pages the agency likes (agency-samples.md); sent with every plan


def reference_notes() -> str:
    return "\n\n".join(p.read_text(encoding="utf-8") for p in sorted(REFERENCE_NOTES.glob("*.md")))


def build_request(brand: dict, facts: dict, *, store_product: dict | None = None, catalog: Catalog | None = None) -> dict:
    return {
        "brand": {**brand, "not_set": not_set(brand)},
        "facts": facts,
        "store_product": store_product,
        "niche": niches.niche_of(brand["category"]),
        "menu": menu(brand, facts, catalog),
        "house_default": house_order(brand["category"]),
        "agency_references": reference_notes(),
    }


def request_params(brand: dict, facts: dict, *, references=(), store_product: dict | None = None, catalog: Catalog | None = None,
                   model: str = MODEL, effort: str = EFFORT, fallbacks: bool = True) -> dict:
    """The exact keyword arguments of the API call (no key in here: the client carries it)."""
    req = build_request(brand, facts, store_product=store_product, catalog=catalog)
    content = load_references(references)
    if content:
        content.append({"type": "text", "text": f"The {len(content)} image(s) above are product pages the agency likes: references only."})
    content.append({"type": "text", "text": json.dumps(req, ensure_ascii=False, indent=1)})
    params = {
        "model": model,
        "max_tokens": MAX_TOKENS,
        "system": system_prompt(),
        "messages": [{"role": "user", "content": content}],
        "output_config": {"effort": effort, "format": {"type": "json_schema", "schema": response_schema()}},
    }
    if fallbacks:
        params["betas"] = [FALLBACK_BETA]
        params["fallbacks"] = "default"
    return params


def check_plan(answer: dict, brand: dict, facts: dict, catalog: Catalog | None = None) -> tuple[dict, dict, list[str]]:
    """The gate. Returns (plan for build_pdp, brand with the open style choices filled, notes on every correction made)."""
    notes: list[str] = []
    available = {m["section"]: m for m in menu(brand, facts, catalog)}
    order, why, left = [], {}, {}
    for item in answer.get("sections", []):
        name = item.get("section")
        if name not in available:
            notes.append(f"plan chose an unknown section {name!r}: ignored")
        elif name in order:
            notes.append(f"plan chose {name} twice: kept the first place")
        elif not available[name]["available"]:
            left[name] = f"chosen by the plan but cannot be built: {available[name]['why_not']}"
            notes.append(f"plan chose {name}, which the client's facts cannot fill ({available[name]['why_not']}): left out")
        else:
            order.append(name)
            why[name] = item.get("why", "")
    figures = [n for n in order if n in SAME_FIGURES]
    for extra in figures[1:]:
        order.remove(extra)
        left[extra] = f"shows the same figures as {figures[0]}, which the plan placed first"
        notes.append(f"plan used both {figures[0]} and {extra}: kept {figures[0]} only")
    if "faq" in order and order[-1] != "faq":
        order.remove("faq")
        order.append("faq")
        notes.append("faq moved to the end (it answers the last doubts above the footer)")
    for item in answer.get("left_out", []):
        name = item.get("section")
        if name in available and name not in order and name not in left:
            left[name] = item.get("why", "") or "left out by the plan"
    for name in available:
        if name not in order and name not in left:
            left[name] = "not mentioned by the plan"
            notes.append(f"plan did not mention {name}: left out")
    signature = answer.get("signature")
    if signature not in SIGNATURES:
        notes.append(f"plan gave an unknown signature {signature!r}: the category default is used")
        signature = None

    brand2 = copy.deepcopy(brand)
    open_ = set(not_set(brand))
    for key, value in (answer.get("brand_choices") or {}).items():
        if value in (None, "keep") or key not in CHOICES:
            continue
        if value not in CHOICES[key]:
            notes.append(f"plan gave {key}={value!r}, not a valid choice: ignored")
        elif key not in open_:
            notes.append(f"plan wanted {key}={value}, but the client already chose it: the client's choice is kept")
        elif key == "heading_class":
            brand2.setdefault("fonts", {})["heading_class"] = value
        else:
            brand2[key] = value
    plan = {"order": order, "why": why, "left_out": left, "signature": signature, "summary": answer.get("summary", "")}
    return plan, brand2, notes


@dataclass
class PlanOutcome:
    brand: dict  # the brand to build with (open style choices filled when the plan was applied)
    plan: dict | None  # for build_pdp(plan=...); None means the house rules decide
    mode: str  # dry-run | live | claude-code (answered by a Claude Code session, same gate)
    status: str  # not-run | applied | refusal | cut-off | api-error | bad-json | empty
    notes: list = field(default_factory=list)
    answer: dict | None = None  # the model's raw structured answer, kept for the report
    params: dict = field(default_factory=dict)
    usage: dict = field(default_factory=dict)
    served_by: str | None = None
    request_id: str | None = None
    cost_usd: float | None = None
    seconds: float | None = None
    error: str | None = None

    def as_report(self) -> dict:
        return {
            "mode": self.mode, "status": self.status,
            "decided_by": ("house rules (recipes/pdp.json)" if not self.plan else
                           "claude code session plan (checked by code)" if self.mode == "claude-code" else "claude plan (checked by code)"),
            "model": self.params.get("model"), "effort": self.params.get("output_config", {}).get("effort"), "prompt_version": prompt_version(),
            "served_by": self.served_by, "request_id": self.request_id, "plan": self.plan, "corrections": self.notes, "answer": self.answer,
            "references_sent": sum(1 for b in (self.params.get("messages") or [{}])[0].get("content", []) if b.get("type") == "image"),
            "usage": self.usage, "cost_usd": self.cost_usd,
            "cost_source": "listed per-token prices x reported usage" if self.cost_usd is not None else None,
            "seconds": self.seconds, "error": self.error,
        }


def run_plan_step(brand: dict, facts: dict, *, client=None, references=(), store_product: dict | None = None,
                  catalog: Catalog | None = None, model: str = MODEL, effort: str = EFFORT, fallbacks: bool = True) -> PlanOutcome:
    params = request_params(brand, facts, references=references, store_product=store_product, catalog=catalog,
                            model=model, effort=effort, fallbacks=fallbacks)
    if client is None:
        return PlanOutcome(brand, None, "dry-run", "not-run", params=params)
    started = time.monotonic()
    out = PlanOutcome(brand, None, "live", "api-error", params=params)
    try:
        create = client.beta.messages.create if fallbacks else client.messages.create
        resp = create(**params)
    except Exception as exc:  # noqa: BLE001 - the SDK has already retried 429/5xx; any failure here means "the house rules decide"
        out.error = f"{type(exc).__name__}: {str(exc)[:300]}"
        out.seconds = round(time.monotonic() - started, 2)
        return out
    out.seconds = round(time.monotonic() - started, 2)
    out.usage = _usage(resp)
    out.served_by = getattr(resp, "model", None)
    out.request_id = getattr(resp, "_request_id", None) or getattr(resp, "id", None)
    out.cost_usd = _cost(out.served_by, out.usage)
    stop = getattr(resp, "stop_reason", None)
    if stop in ("refusal", "max_tokens"):
        out.status = "refusal" if stop == "refusal" else "cut-off"
        return out
    text = next((b.text for b in getattr(resp, "content", []) or [] if getattr(b, "type", None) == "text"), None)
    try:
        data = json.loads(text) if text else None
    except (TypeError, ValueError):
        data = None
    return _apply(out, data, brand, facts, catalog)


def plan_request(brand: dict, facts: dict, *, references=(), store_product: dict | None = None, catalog: Catalog | None = None) -> dict:
    """Everything a Claude Code session needs to answer the plan step itself: the same system prompt, request and answer shape the API
    gets (reference images are named by path; the session opens them itself)."""
    load_references(references)  # same refusals as the API route
    return {"system": system_prompt(), "request": build_request(brand, facts, store_product=store_product, catalog=catalog),
            "references": [str(Path(p).resolve()) for p in references or []], "answer_schema": response_schema(),
            "prompt_version": prompt_version(),
            "how_to_answer": "Write ONE JSON object matching answer_schema to plan-answer.json. Account for every menu section once."}


def read_answer(path) -> dict | None:
    """An answer file holds the JSON answer itself, or an API-style {"content": [{"type": "text", "text": "<json>"}]} (the shape the n8n
    'Wait for Claude Code' nodes receive). None when it cannot be read as one JSON object."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("content"), list):
            data = json.loads("".join(b.get("text", "") for b in data["content"] if isinstance(b, dict) and b.get("type") == "text"))
    except (OSError, TypeError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def apply_answer(brand: dict, facts: dict, data, *, references=(), store_product: dict | None = None,
                 catalog: Catalog | None = None) -> PlanOutcome:
    """The plan answered by a Claude Code session instead of the API (Harsh's choice, 9 Oct 2026, the same route as the dtj content
    workflow). The answer goes through exactly the same gate (check_plan) as an API answer."""
    params = request_params(brand, facts, references=references, store_product=store_product, catalog=catalog)
    return _apply(PlanOutcome(brand, None, "claude-code", "bad-json", params=params), data, brand, facts, catalog)


def _apply(out: PlanOutcome, data, brand: dict, facts: dict, catalog: Catalog | None) -> PlanOutcome:
    if not isinstance(data, dict):
        out.status = "bad-json"
        return out
    out.answer = data
    plan, brand2, notes = check_plan(data, brand, facts, catalog)
    out.notes = notes
    if not plan["order"]:
        out.status = "empty"
        out.notes.append("the plan left no buildable section: the house rules decide")
        return out
    out.brand, out.plan, out.status = brand2, plan, "applied"
    return out
