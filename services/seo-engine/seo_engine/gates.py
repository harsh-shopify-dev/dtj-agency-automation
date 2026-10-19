"""The code gate every AI-written article must pass before it can become a WordPress draft.

The model is told the rules, but this file is what enforces them: no number that isn't in an approved fact, no ranking or promise DTJ
cannot prove, nothing about how DTJ works inside, no links off the site, and the shape that answer engines can lift (a short direct
answer first, question headings, an FAQ). A blocked draft is kept as a file with its reasons; it never reaches WordPress.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

DATA = Path(__file__).resolve().parent / "data"
_SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_NUM = re.compile(r"(₹\s?)?(\d[\d,]*(?:\.\d+)?)\s?(%|x\b|X\b|L\b|Cr\b|lakhs?\b|crores?\b|[kK]\b)?")
_URL = re.compile(r"https?://[^\s)\"'<>]+")


def load_json(name: str) -> dict:
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def numbers_in(text: str) -> list[tuple[str, str]]:
    """(as written, digits only) for every figure that counts as a claim: money, a percentage, a multiple, a lakh/crore figure, or any
    number above 10. Plain counting words like '3 things' or a year are not claims."""
    out = []
    for m in _NUM.finditer(text):
        cur, num, unit = m.group(1), m.group(2), m.group(3)
        core = num.replace(",", "").rstrip(".")
        if not core or core.count(".") > 1:
            continue
        try:
            value = float(core)
        except ValueError:
            continue
        if not cur and not unit and (value <= 10 or (2015 <= value <= 2035 and "." not in core)):
            continue
        out.append((m.group(0).strip(), core))
    return out


@dataclass
class GateResult:
    ok: bool
    blocks: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    words: int = 0


def article_text(a: dict) -> str:
    parts = [a.get("title", ""), a.get("meta_description", ""), a.get("short_answer", "")]
    for s in a.get("sections", []):
        parts.append(s.get("heading", ""))
        parts.extend(s.get("paragraphs", []))
    for q in a.get("faq", []):
        parts += [q.get("question", ""), q.get("answer", "")]
    return "\n".join(p for p in parts if p)


def shingles(text: str, n: int) -> set[str]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return {" ".join(words[i:i + n]) for i in range(max(0, len(words) - n + 1))}


def similarity(a: str, b: str, n: int = 5) -> float:
    """How much two pages say the same thing (shared 5-word phrases / all of them). Doorway pages score high."""
    sa, sb = shingles(a, n), shingles(b, n)
    return len(sa & sb) / len(sa | sb) if sa and sb else 0.0


def copied_phrases(a: dict, fingerprint: set[str]) -> int:
    """How many 10-word phrases of the draft also appear on a top-3 competitor page (see serp_skeleton.shingles)."""
    from .serp_skeleton import shingles as hashed
    return len(hashed(article_text(a)) & fingerprint) if fingerprint else 0


def check(a: dict, facts: dict | None = None, rules: dict | None = None, *, kind: str = "article",
          fingerprint: set[str] | None = None, extra_facts: list[str] | tuple = ()) -> GateResult:
    """kind: article (a blog post) or city (a service page for one city). extra_facts: approved local proof lines for a city page."""
    facts = facts or load_json("facts.json")
    rules = rules or load_json("rules.json")
    lim = {**rules["article"], **(rules["city_page"] if kind == "city" else {})}
    blocks, warns = [], []
    text = article_text(a)
    words = len(re.findall(r"\w+", text))

    for key in ("title", "slug", "meta_description", "short_answer", "sections", "faq"):
        if not a.get(key):
            blocks.append(f"missing {key}")
    title, meta, slug = a.get("title", ""), a.get("meta_description", ""), a.get("slug", "")
    if len(title) > lim["title_max"]:
        blocks.append(f"title is {len(title)} characters (max {lim['title_max']})")
    if meta and not lim["meta_min"] <= len(meta) <= lim["meta_max"]:
        blocks.append(f"meta description is {len(meta)} characters ({lim['meta_min']}-{lim['meta_max']})")
    if slug and (not _SLUG.match(slug) or len(slug) > 70):
        blocks.append(f"slug {slug!r} must be lowercase words joined by '-', at most 70 characters")
    sa_words = len(a.get("short_answer", "").split())
    if sa_words > lim["short_answer_max_words"]:
        blocks.append(f"short answer is {sa_words} words (max {lim['short_answer_max_words']}): answer engines lift short answers")
    if not lim["words_min"] <= words <= lim["words_max"]:
        blocks.append(f"article is {words} words ({lim['words_min']}-{lim['words_max']})")
    nfaq = len(a.get("faq", []))
    if not lim["faq_min"] <= nfaq <= lim["faq_max"]:
        blocks.append(f"{nfaq} FAQ items ({lim['faq_min']}-{lim['faq_max']})")
    if a.get("faq") and any(not q.get("question", "").strip().endswith("?") for q in a["faq"]):
        blocks.append("every FAQ question must end with '?'")

    for r in rules["block"]:
        for m in re.finditer(r["pattern"], text, re.I):
            blocks.append(f"{m.group(0)!r}: {r['why']}")
    for r in rules["warn"]:
        hits = sorted({m.group(0).lower() for m in re.finditer(r["pattern"], text, re.I)})
        if hits:
            warns.append(f"{', '.join(hits)}: {r['why']}")

    approved = {core for f in facts["facts"] if f["status"] == "approved" for _, core in numbers_in(f["text"])}
    approved |= {core for line in extra_facts for _, core in numbers_in(line)}
    unsourced = {core: f for f in facts["facts"] if f["status"] != "approved" for _, core in numbers_in(f["text"])}
    for shown, core in numbers_in(text):
        if core in approved:
            continue
        if core in unsourced:
            blocks.append(f"{shown!r} is from '{unsourced[core]['id']}', which still needs a source")
        else:
            blocks.append(f"{shown!r} is not in any approved fact (numbers come from facts.json only)")

    known = {f["id"]: f for f in facts["facts"]}
    for fid in a.get("facts_used", []):
        if fid not in known:
            blocks.append(f"facts_used names an unknown fact {fid!r}")
        elif known[fid]["status"] != "approved":
            blocks.append(f"facts_used names {fid!r}, which still needs a source")

    hosts = set(rules["allowed_link_hosts"])
    sources = set(rules.get("source_link_hosts", []))
    for u in _URL.findall(text) + [l.get("url", "") for l in a.get("internal_links", [])]:
        if (urlparse(u).hostname or "").removeprefix("www.") not in hosts:
            blocks.append(f"link to {u!r}: links inside the text must go to {sorted(hosts)}")
    for u in [l.get("url", "") for l in a.get("sources", [])]:
        host = (urlparse(u).hostname or "").removeprefix("www.")
        if not u.startswith("https://") or not any(host == h or host.endswith("." + h) for h in sources):
            blocks.append(f"source {u!r}: only official help pages may be cited ({', '.join(sorted(sources))})")

    copied = copied_phrases(a, fingerprint or set())
    if copied:
        blocks.append(f"{copied} 10-word phrases are copied from a top-ranking competitor page: say it in our own words")

    blocks = list(dict.fromkeys(blocks))
    return GateResult(ok=not blocks, blocks=blocks, warnings=warns, words=words)


def check_snippet(text: str, *, min_len: int = 0, max_len: int = 10_000, facts: dict | None = None,
                  rules: dict | None = None) -> list[str]:
    """The same claim, number and wording rules for a short line (a meta description, a title, an alt text)."""
    facts = facts or load_json("facts.json")
    rules = rules or load_json("rules.json")
    blocks = []
    if not min_len <= len(text) <= max_len:
        blocks.append(f"{len(text)} characters ({min_len}-{max_len})")
    for r in rules["block"]:
        blocks += [f"{m.group(0)!r}: {r['why']}" for m in re.finditer(r["pattern"], text, re.I)]
    approved = {core for f in facts["facts"] if f["status"] == "approved" for _, core in numbers_in(f["text"])}
    blocks += [f"{shown!r} is not in any approved fact" for shown, core in numbers_in(text) if core not in approved]
    if re.search(r"\bWe Helping\b", text):
        blocks.append("broken grammar")
    return blocks
