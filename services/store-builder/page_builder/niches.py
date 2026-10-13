"""Niche-aware block choice (Harsh's idea, 13 Oct 2026): when the page is built for a brand, blocks made for its niche come first, then blocks
that suit every niche, then blocks made for other niches (unless a block says it makes no sense outside its niches).

    niche_of("apparel")                                    -> "fashion"
    order_blocks(["dtj-sections/science-stats", "dtj-sections-2/stat-cards"], "apparel")
                                                           -> stat-cards first (suits every niche), science-stats after (made for wellness and beauty)

The tags live in block_tags.json. They are judgment, not data; the test suite fails when a block exists without a tag, so a new block
cannot be forgotten. Nothing here touches a store."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

HERE = Path(__file__).resolve().parent
NICHE_FIT, UNIVERSAL, OTHER_NICHE = 0, 1, 2


@lru_cache(maxsize=1)
def _tags() -> dict:
    return json.loads((HERE / "block_tags.json").read_text(encoding="utf-8"))


def niche_of(category: str) -> str:
    return _tags()["niche_of_category"].get(category, "general")


def tags() -> dict[str, dict]:
    return _tags()["blocks"]


def rank(app_block: str, category: str) -> int | None:
    """0 = made for this brand's niche, 1 = suits every niche, 2 = made for other niches, None = must not be used for this niche."""
    tag = tags().get(app_block.split(" ")[0])
    if tag is None or not tag.get("niches"):
        return UNIVERSAL
    niche = niche_of(category)
    if niche in tag["niches"]:
        return NICHE_FIT
    return OTHER_NICHE if tag.get("cross_niche", True) else None


def order_blocks(entries: list[str], category: str) -> list[str]:
    """The same blocks, best fit for the category first. A block that must not be used for this niche is dropped, unless that would leave
    nothing (the section would then have no block at all)."""
    ranked = [(rank(e, category), i, e) for i, e in enumerate(entries)]
    allowed = [r for r in ranked if r[0] is not None]
    keep = allowed or ranked
    return [e for _, _, e in sorted(keep, key=lambda r: (r[0] if r[0] is not None else OTHER_NICHE, r[1]))]


def fit_label(app_block: str, category: str) -> str:
    r = rank(app_block, category)
    return {NICHE_FIT: "made for this niche", UNIVERSAL: "suits every niche", OTHER_NICHE: "made for other niches"}.get(r, "not for this niche")


def unwired() -> list[str]:
    """Blocks we have that no page-builder section builds with yet."""
    return sorted(k for k, v in tags().items() if not v.get("wired"))
