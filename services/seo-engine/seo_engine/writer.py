"""The weekly article writer: one Claude API call drafts an answer article for the next unwritten topic; gates.py then checks every line.

Unattended runs use the Claude API with an API KEY (ANTHROPIC_API_KEY, filled from the vault), never a subscription login. The SDK reads
the key; this module never reads, prints, stores or logs it.

    from seo_engine.writer import write_article, make_client
    out = write_article(topic, pages)                         # dry run: builds the exact request, calls nothing, costs nothing
    out = write_article(topic, pages, client=make_client())   # live: ONE API call, then the code gate
"""
from __future__ import annotations

import hashlib
import html
import json
import time
from dataclasses import dataclass, field
from pathlib import Path

from . import gates, serp_skeleton

HERE = Path(__file__).resolve().parent
MODEL = "claude-opus-5-5"
EFFORT = "high"  # a public article: quality matters more than the few cents a run costs
MAX_TOKENS = 32000  # thinking cannot be switched off on this model; the article itself is ~3k tokens
FALLBACK_BETA = "server-side-fallback-2026-07-01"
# Listed API prices in USD per million tokens (Claude API skill model table, cached 6 Oct 2026). Used only to report a run's cost.
PRICES = {"claude-opus-5-5": {"input": 4.00, "output": 20.00, "cache_read": 0.20}}

_STR = {"type": "string"}
SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["title", "slug", "meta_description", "short_answer", "sections", "faq", "facts_used", "internal_links", "sources"],
    "properties": {
        "title": _STR, "slug": _STR, "meta_description": _STR, "short_answer": _STR,
        "sections": {"type": "array", "items": {"type": "object", "additionalProperties": False, "required": ["heading", "paragraphs"],
                                                "properties": {"heading": _STR, "paragraphs": {"type": "array", "items": _STR}}}},
        "faq": {"type": "array", "items": {"type": "object", "additionalProperties": False, "required": ["question", "answer"],
                                           "properties": {"question": _STR, "answer": _STR}}},
        "facts_used": {"type": "array", "items": _STR},
        "internal_links": {"type": "array", "items": {"type": "object", "additionalProperties": False, "required": ["url", "anchor"],
                                                      "properties": {"url": _STR, "anchor": _STR}}},
        "sources": {"type": "array", "items": {"type": "object", "additionalProperties": False, "required": ["url", "title"],
                                               "properties": {"url": _STR, "title": _STR}}},
    },
}


def system_prompt(kind: str = "article") -> str:
    text = (HERE / "prompts" / "writer.md").read_text(encoding="utf-8")
    return text + (HERE / "prompts" / "city.md").read_text(encoding="utf-8") if kind == "city" else text


def prompt_version() -> str:
    h = hashlib.sha256()
    for p in (HERE / "prompts" / "writer.md", HERE / "prompts" / "city.md", HERE / "data" / "facts.json", HERE / "data" / "rules.json"):
        h.update(p.read_bytes())
    h.update((MODEL + EFFORT).encode())
    return h.hexdigest()[:12]


def build_request(topic: dict, pages: list[dict], facts: dict | None = None, *, skeleton: dict | None = None,
                  local: dict | None = None) -> dict:
    """What the model sees: the question and keywords, the founder's words, the approved facts only, the unknowns, the real pages it
    may link, the outline of the top 3 Google results (never their text) and, for a city page, that city's real proof."""
    facts = facts or gates.load_json("facts.json")
    req = {
        "topic": {k: topic[k] for k in ("question", "main_keyword", "keywords", "pain", "words_they_use") if k in topic},
        "place": topic.get("place"),
        "brand": facts["brand"],
        "approved_facts": [{"id": f["id"], "text": f["text"]} for f in facts["facts"] if f["status"] == "approved"],
        "unknown": facts["unknown"],
        "pages_you_may_link": [{"url": p["url"], "title": p.get("title", "")} for p in pages if p.get("status", 200) == 200],
        "suggested_link": topic.get("link_to"),
        "source_hosts_you_may_cite": gates.load_json("rules.json").get("source_link_hosts", []),
    }
    if skeleton:
        req["top_results"] = serp_skeleton.for_model(skeleton)
        req["target_words"] = skeleton.get("target_words")
    if local is not None:
        req["local_proof"] = local
    return req


def request_params(topic: dict, pages: list[dict], *, model: str = MODEL, effort: str = EFFORT, fallbacks: bool = True,
                   skeleton: dict | None = None, local: dict | None = None, kind: str = "article") -> dict:
    body = build_request(topic, pages, skeleton=skeleton, local=local)
    params = {
        "model": model,
        "max_tokens": MAX_TOKENS,
        "system": system_prompt(kind),
        "messages": [{"role": "user", "content": json.dumps(body, ensure_ascii=False, indent=1)}],
        "output_config": {"effort": effort, "format": {"type": "json_schema", "schema": SCHEMA}},
    }
    if fallbacks:
        params["betas"] = [FALLBACK_BETA]
        params["fallbacks"] = "default"
    return params


@dataclass
class Draft:
    topic_id: str
    mode: str  # dry-run | live
    status: str  # not-run | passed | blocked | refusal | cut-off | api-error | bad-json
    article: dict | None = None
    gate: dict = field(default_factory=dict)
    usage: dict = field(default_factory=dict)
    served_by: str | None = None
    request_id: str | None = None
    cost_usd: float | None = None
    seconds: float | None = None
    error: str | None = None
    kind: str = "article"  # article (blog post) | city (city service page)

    def as_report(self) -> dict:
        return {"topic_id": self.topic_id, "mode": self.mode, "status": self.status, "model": MODEL, "effort": EFFORT,
                "kind": self.kind, "prompt_version": prompt_version(), "served_by": self.served_by, "request_id": self.request_id, "usage": self.usage,
                "cost_usd": self.cost_usd, "cost_source": "listed per-token prices x reported usage" if self.cost_usd is not None else None,
                "seconds": self.seconds, "error": self.error, "gate": self.gate, "article": self.article}


def make_client():
    """A live client. The SDK reads ANTHROPIC_API_KEY from the environment; it is never passed, printed or logged here."""
    import anthropic

    return anthropic.Anthropic()


def _usage(resp) -> dict:
    u = getattr(resp, "usage", None)
    keys = ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")
    return {k: int(getattr(u, k, 0) or 0) for k in keys} if u is not None else {}


def _cost(model: str | None, usage: dict) -> float | None:
    p = PRICES.get(model or "")
    if not p or not usage or usage.get("cache_creation_input_tokens"):
        return None
    total = usage["input_tokens"] * p["input"] + usage["output_tokens"] * p["output"] + usage["cache_read_input_tokens"] * p["cache_read"]
    return round(total / 1_000_000, 6)


def local_lines(local: dict | None) -> list[str]:
    """Every proof line of a city page, so its numbers count as approved for that page only."""
    if not local:
        return []
    lines = [c.get("result", "") for c in local.get("clients", [])] + [r.get("text", "") for r in local.get("reviews", [])]
    return [l for l in lines if l] + ([local["office"]["address"], local["office"].get("phone", "")] if local.get("office") else [])


def write_article(topic: dict, pages: list[dict], *, client=None, fallbacks: bool = True, skeleton: dict | None = None,
                  local: dict | None = None, kind: str = "article") -> Draft:
    params = request_params(topic, pages, fallbacks=fallbacks, skeleton=skeleton, local=local, kind=kind)
    if client is None:
        return Draft(topic["id"], "dry-run", "not-run", kind=kind)
    started = time.monotonic()
    out = Draft(topic["id"], "live", "api-error", kind=kind)
    try:
        create = client.beta.messages.create if fallbacks else client.messages.create
        resp = create(**params)
    except Exception as exc:  # noqa: BLE001 - the SDK already retried 429/5xx; any failure here means "no draft this week"
        out.error = f"{type(exc).__name__}: {str(exc)[:300]}"
        out.seconds = round(time.monotonic() - started, 2)
        return out
    out.seconds = round(time.monotonic() - started, 2)
    out.usage, out.served_by = _usage(resp), getattr(resp, "model", None)
    out.request_id = getattr(resp, "_request_id", None) or getattr(resp, "id", None)
    out.cost_usd = _cost(out.served_by, out.usage)
    stop = getattr(resp, "stop_reason", None)
    if stop in ("refusal", "max_tokens"):
        out.status = "refusal" if stop == "refusal" else "cut-off"
        return out
    text = next((b.text for b in getattr(resp, "content", []) or [] if getattr(b, "type", None) == "text"), None)
    try:
        article = json.loads(text) if text else None
    except (TypeError, ValueError):
        article = None
    if not isinstance(article, dict):
        out.status = "bad-json"
        return out
    if topic.get("slug"):
        article["slug"] = topic["slug"]  # fixed per topic, so WordPress can tell a topic was already drafted
    result = gates.check(article, kind=kind, fingerprint=(skeleton or {}).get("_fingerprint"), extra_facts=local_lines(local))
    out.article = article
    out.gate = {"ok": result.ok, "blocks": result.blocks, "warnings": result.warnings, "words": result.words}
    out.status = "passed" if result.ok else "blocked"
    return out


def to_html(a: dict) -> str:
    """WordPress post body: the short answer first (what AI engines quote), question headings, the FAQ, and FAQPage data."""
    e = html.escape
    parts = [f'<p class="dtj-short-answer"><strong>{e(a["short_answer"])}</strong></p>']
    links = {l["url"]: l["anchor"] for l in a.get("internal_links", [])}
    for s in a["sections"]:
        parts.append(f"<h2>{e(s['heading'])}</h2>")
        parts += [f"<p>{e(p)}</p>" for p in s["paragraphs"]]
    if links:
        parts.append("<p>Read next: " + " · ".join(f'<a href="{e(u)}">{e(t)}</a>' for u, t in links.items()) + "</p>")
    if a.get("sources"):
        parts.append("<p>Sources: " + " · ".join(f'<a href="{e(x["url"])}" rel="nofollow noopener">{e(x["title"])}</a>'
                                                  for x in a["sources"]) + "</p>")
    parts.append("<h2>Questions founders ask</h2>")
    for q in a["faq"]:
        parts += [f"<h3>{e(q['question'])}</h3>", f"<p>{e(q['answer'])}</p>"]
    faq_ld = {"@context": "https://schema.org", "@type": "FAQPage",
              "mainEntity": [{"@type": "Question", "name": q["question"], "acceptedAnswer": {"@type": "Answer", "text": q["answer"]}}
                             for q in a["faq"]]}
    parts.append('<script type="application/ld+json">' + json.dumps(faq_ld, ensure_ascii=False).replace("</", "<\\/") + "</script>")
    return "\n".join(parts)
