"""Turns the website check into a batch of exact changes (before -> after) that a person approves with one yes.

Harsh, 14 Oct 2026: "b first month": the engine prepares the fixes every Monday; Harsh (or, when he can't be reached, a DTJ
teammate by name) approves the batch; apply_batch.py writes it. Nothing here changes the site.

Change kinds:
  auto   meta_description / seo_title (Yoast fields, written through the DTJ SEO Bridge plugin), noindex (Yoast field),
         alt_text (WordPress media library), site_jsonld (Organization + one LocalBusiness per real office, printed by the bridge)
  manual what only a person can do (WordPress/Yoast settings that need an administrator, content and claims decisions)
AI-written lines (descriptions, titles, alt text) pass gates.check_snippet; a line that fails is listed, never applied.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone

from . import gates

MODEL = "claude-opus-5-5"
MAX_TOKENS = 16000
FALLBACK_BETA = "server-side-fallback-2026-07-01"
MAX_PAGES_PER_BATCH = 15
MAX_IMAGES_PER_BATCH = 10
TITLE_MAX, DESC_MIN, DESC_MAX, ALT_MAX = 60, 120, 158, 125

_META_SCHEMA = {"type": "object", "additionalProperties": False, "required": ["pages"], "properties": {"pages": {"type": "array", "items": {
    "type": "object", "additionalProperties": False, "required": ["url", "seo_title", "meta_description"],
    "properties": {"url": {"type": "string"}, "seo_title": {"type": "string"}, "meta_description": {"type": "string"}}}}}}
_ALT_SCHEMA = {"type": "object", "additionalProperties": False, "required": ["images"], "properties": {"images": {"type": "array", "items": {
    "type": "object", "additionalProperties": False, "required": ["src", "alt"],
    "properties": {"src": {"type": "string"}, "alt": {"type": "string"}}}}}}

META_PROMPT = f"""You write Google search snippets for pages of Digital Tushar Joshi (DTJ), a performance marketing agency in India
for D2C brands. Readers are Indian D2C founders: plain words, no jargon, no hype.
For every page in the request return:
- seo_title: at most {TITLE_MAX} characters. What the page is about, then " | DTJ". Keep the current title's meaning if it is good.
- meta_description: {DESC_MIN}-{DESC_MAX} characters. One or two plain sentences: what the founder gets from this page. Correct grammar.
Rules (code rejects a line that breaks one): no number unless it is in the approved facts; no best/#1/leading/top-rated; no
guarantees; no response times; no prices; never mention AI or automation. Use only what the page excerpt and approved facts say."""

ALT_PROMPT = f"""Write alt text for each image on the website of Digital Tushar Joshi, a marketing agency. Describe what the image
shows in plain words, at most {ALT_MAX} characters, no "image of". Do not write any number, price or percentage, even if the image
shows one. Do not claim anything about results. If you cannot see the image, return an empty alt for it."""


def _call(client, system: str, content, schema: dict, effort: str) -> dict | None:
    resp = client.beta.messages.create(model=MODEL, max_tokens=MAX_TOKENS, system=system, betas=[FALLBACK_BETA], fallbacks="default",
                                       messages=[{"role": "user", "content": content}],
                                       output_config={"effort": effort, "format": {"type": "json_schema", "schema": schema}})
    if getattr(resp, "stop_reason", None) in ("refusal", "max_tokens"):
        return None
    text = next((b.text for b in getattr(resp, "content", []) or [] if getattr(b, "type", None) == "text"), None)
    try:
        return json.loads(text) if text else None
    except ValueError:
        return None


def _approved_facts() -> list[str]:
    return [f["text"] for f in gates.load_json("facts.json")["facts"] if f["status"] == "approved"]


def site_jsonld(proof: dict) -> dict:
    brand = gates.load_json("facts.json")["brand"]
    org = {"@type": "Organization", "@id": brand["site"] + "/#organization", "name": brand["name"], "alternateName": brand["short_name"],
           "url": brand["site"] + "/", "founder": {"@type": "Person", "name": brand["founder"]}}
    graph = [org]
    for city, c in proof["cities"].items():
        office = c.get("office")
        if not office:
            continue
        graph.append({"@type": "ProfessionalService", "@id": f"{brand['site']}/#office-{city.lower()}",
                      "name": f"{brand['name']} ({city}{' head office' if office.get('head_office') else ''})",
                      "url": brand["site"] + "/contact-us/", "telephone": office.get("phone"), "parentOrganization": {"@id": org["@id"]},
                      "address": {"@type": "PostalAddress", "streetAddress": office["address"], "addressLocality": city,
                                  "addressRegion": "Gujarat", "addressCountry": "IN"}})
    return {"@context": "https://schema.org", "@graph": graph}


def propose(scan: dict, *, client=None, proof: dict | None = None, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    proof = proof or gates.load_json("local_proof.json")
    pages = {p["url"]: p for p in scan["pages"]}
    by_rule: dict[str, list[dict]] = {}
    for f in scan["findings"]:
        by_rule.setdefault(f["rule"], []).append(f)
    changes: list[dict] = []
    notes: list[str] = []

    def add(kind, url, before, after, reason, how="auto", **extra):
        changes.append({"cid": f"c{len(changes) + 1:03d}", "kind": kind, "url": url, "before": before, "after": after,
                        "reason": reason, "how": how, **extra})

    # 1. Pages that should not be in Google at all
    for rule in ("template-in-sitemap", "wordpress-default-page"):
        for f in by_rule.get(rule, []):
            add("noindex", f["page"], pages.get(f["page"], {}).get("robots", ""), "noindex",
                f"{f['evidence']} (it leaves the sitemap once hidden)")

    # 2. Titles and descriptions (one AI call for the batch, every line checked)
    need = []
    for rule in ("description-missing", "description-grammar", "description-length", "title-long", "title-missing"):
        for f in by_rule.get(rule, []):
            p = pages.get(f["page"])
            if p and p["url"] not in [n["url"] for n in need] and not any(c["url"] == p["url"] and c["kind"] == "noindex" for c in changes):
                need.append(p)
    need = need[:MAX_PAGES_PER_BATCH]
    if need and client is None:
        notes.append(f"{len(need)} pages need a new title or description: written on a live run (needs the Claude API key).")
    elif need:
        req = {"approved_facts": _approved_facts(), "pages": [{"url": p["url"], "current_title": p["title"], "current_description": p["description"],
               "h1": p["h1"], "question_headings": p["questions"][:8], "excerpt": p["excerpt"]} for p in need]}
        try:
            out = _call(client, META_PROMPT, json.dumps(req, ensure_ascii=False), _META_SCHEMA, "medium") or {"pages": []}
        except Exception as exc:  # noqa: BLE001 - no snippets this week; the report says so
            out = {"pages": []}
            notes.append(f"Descriptions not written: {type(exc).__name__}")
        for s in out.get("pages", []):
            p = pages.get(s.get("url"))
            if not p:
                continue
            desc, title = s.get("meta_description", "").strip(), s.get("seo_title", "").strip()
            blocks = gates.check_snippet(desc, min_len=DESC_MIN, max_len=DESC_MAX)
            add("meta_description", p["url"], p["description"], desc, "missing, too long/short or broken description",
                how="auto" if not blocks else "blocked", blocks=blocks)
            if title and title != p["title"] and (len(p["title"]) > TITLE_MAX or not p["title"]):
                tb = gates.check_snippet(title, min_len=10, max_len=TITLE_MAX)
                add("seo_title", p["url"], p["title"], title, f"title is {len(p['title'])} characters (Google cuts it at about {TITLE_MAX})",
                    how="auto" if not tb else "blocked", blocks=tb)

    # 3. Alt text (one vision call for up to MAX_IMAGES_PER_BATCH images that have a WordPress media id)
    imgs, seen = [], set()
    for p in scan["pages"]:
        for im in p.get("images_no_alt", []):
            if im.get("media_id") and im["media_id"] not in seen and len(imgs) < MAX_IMAGES_PER_BATCH:
                seen.add(im["media_id"])
                imgs.append({**im, "page": p["url"]})
    if imgs and client is None:
        notes.append(f"{len(imgs)} images need alt text: written on a live run.")
    elif imgs:
        content = [{"type": "text", "text": "Images, in order: " + json.dumps([i["src"] for i in imgs])}]
        content += [{"type": "image", "source": {"type": "url", "url": i["src"]}} for i in imgs]
        try:
            out = _call(client, ALT_PROMPT, content, _ALT_SCHEMA, "low") or {"images": []}
        except Exception as exc:  # noqa: BLE001
            out = {"images": []}
            notes.append(f"Alt text not written: {type(exc).__name__}")
        alts = {x.get("src"): x.get("alt", "").strip() for x in out.get("images", [])}
        for im in imgs:
            alt = alts.get(im["src"], "")
            if not alt:
                continue
            blocks = gates.check_snippet(alt, min_len=5, max_len=ALT_MAX)
            add("alt_text", im["page"], "", alt, "image has no alt text", how="auto" if not blocks else "blocked",
                media_id=im["media_id"], src=im["src"], blocks=blocks)

    # 4. Business details AI assistants and Google read (no AI: built from the contact page facts)
    if by_rule.get("entity-schema-missing"):
        add("site_jsonld", scan["site"] + "/", None, site_jsonld(proof),
            "no Organization or office data on the home page; one entry per real office (Rajkot, Ahmedabad)")

    # 5. For a person
    manual = {
        "llms-txt-claim": "llms.txt is made by Yoast from the site title and tagline: an administrator changes the tagline in "
                          "Settings > General to a plain line (e.g. 'Performance marketing for D2C brands'). DTJ decides the wording.",
        "author-archive": "Yoast > Settings > Advanced > Author archives: off; and credit posts to a real person or 'DTJ Team' "
                          "(Users > the author's display name). Needs an administrator.",
        "h1-count": "These pages need exactly one main heading (H1): in Elementor, set the page's top heading to H1 and the others to H2.",
        "no-question-headings": "Add 3-5 founder questions as headings, each answered in its first sentence.",
        "thin-page": "Say more on these pages: proof, steps and FAQs.",
        "llms-txt-missing": "Turn on llms.txt in Yoast > Settings > Site features.",
    }
    for rule, how_to in manual.items():
        if by_rule.get(rule):
            add("manual", ", ".join(sorted({f["page"] for f in by_rule[rule]}))[:600], None, None, how_to, how="manual",
                rule=rule, pages=len(by_rule[rule]))
    if any(re.search(r"best-performance-marketing-agency|/why-90-of-", p["url"]) for p in scan["pages"]):
        add("manual", "blog posts with claims", None, None,
            "Two posts make claims we can't source ('India's Best ... Agency', 'Why 90% of D2C Brands Fail'): DTJ decides to "
            "keep, reword or remove them. The engine never touches them.", how="manual", rule="claims")

    return {"id": f"fix-{now:%Y-%m-%d}", "made_at": now.isoformat(), "site": scan["site"], "source": scan["source"],
            "changes": changes, "notes": notes,
            "counts": {k: sum(1 for c in changes if c["how"] == k) for k in ("auto", "blocked", "manual")}}
