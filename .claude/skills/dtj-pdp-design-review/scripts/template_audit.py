"""Audit a built page's template.json BEFORE it reaches a store: repeated claims, reused pictures, section order and CTA coverage.

    python template_audit.py <run dir or template.json> [--plan wireframe-plan.md]

Reads only the DTJ blocks' settings (theme blocks carry no copy we wrote). Prints JSON:
- sections: the page order (section id, block types)
- repeated_text: lines used more than once, and near-duplicates (word-trigram overlap >= 0.6)
- pictures: each shopify://shop_images/ file with how many times it is used (more than 2 = finding)
- ctas: sections that end with a button setting (cta_text / button_label_* / cta_link)
Deterministic; standard library only.
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from itertools import combinations
from pathlib import Path

TEXT_KEYS = re.compile(r"(heading|subheading|text|body|bullet|name|description|quote|label|title|question|answer|phrase|benefits|eyebrow|note|tagline|intro)", re.I)


def load(path: Path) -> dict:
    p = path / "template.json" if path.is_dir() else path
    raw = p.read_text(encoding="utf-8")
    return json.loads(raw.split("*/", 1)[1] if raw.lstrip().startswith("/*") else raw)


def walk_blocks(node, out, section=None):
    if isinstance(node, dict):
        t = str(node.get("type", ""))
        if t.startswith("shopify://apps/"):
            out.append((section, t.split("/blocks/")[1].split("/")[0], node.get("settings", {})))
        for k, v in node.items():
            walk_blocks(v, out, section)
    elif isinstance(node, list):
        for v in node:
            walk_blocks(v, out, section)


def norm(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]+", " ", s.lower())).strip()


def trigrams(s: str) -> set:
    w = s.split()
    return {tuple(w[i:i + 3]) for i in range(len(w) - 2)}


def audit(template: dict) -> dict:
    order = template.get("order") or list(template["sections"])
    blocks = []
    for sid in order:
        walk_blocks(template["sections"][sid], blocks, sid)
    texts, pictures, ctas = [], Counter(), []
    for sid, btype, settings in blocks:
        for k, v in settings.items():
            if isinstance(v, str) and v.startswith("shopify://shop_images/"):
                pictures[v.split("/")[-1]] += 1
            elif isinstance(v, str) and TEXT_KEYS.search(k) and len(norm(v)) >= 12:
                texts.append((norm(v), f"{sid}/{btype}.{k}"))
        if any(settings.get(k) for k in settings if re.match(r"(cta_text|cta_link|button_label(_\d+)?)$", k)):
            ctas.append(sid)
    exact = Counter(t for t, _ in texts)
    repeated = [{"text": t, "times": n, "where": [w for tt, w in texts if tt == t]} for t, n in exact.items() if n > 1]
    near = []
    uniq = list({t: w for t, w in texts}.items())
    for (a, wa), (b, wb) in combinations(uniq, 2):
        ta, tb = trigrams(a), trigrams(b)
        if ta and tb and len(ta & tb) / min(len(ta), len(tb)) >= 0.6:
            near.append({"a": wa, "b": wb, "text_a": a[:90], "text_b": b[:90]})
    return {
        "sections": [{"id": sid, "blocks": [b for s, b, _ in blocks if s == sid]} for sid in order],
        "repeated_text": repeated, "near_duplicates": near[:30],
        "pictures": [{"file": f, "times": n, "finding": n > 2} for f, n in pictures.most_common()],
        "sections_with_cta": ctas,
    }


def main(argv=None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if not argv:
        print(__doc__)
        return 1
    json.dump(audit(load(Path(argv[0]))), sys.stdout, indent=1)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
