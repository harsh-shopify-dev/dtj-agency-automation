"""A brand's folder on the engine host (filled from its Drive folder by n8n "Reel: Sync brand from Drive"):

    <root>/brands/<brand>/brand.json        {"name", "niche", "languages", ...}
                         brief.md            who the brand is, voice, audience
                         facts.md            the ONLY claims a reel may make
                         products/           product photos (the pack as it really is)
                         references/<style>/ winning reels of that style (ugc, cinematic, founder, ...)
                         style-cards/<style>.json   Gemini's breakdown of those references (made once, reused)
    <root>/Niches/<niche>/<style>/           shared references, used when a brand has fewer than MIN_REFS of its own
"""
from __future__ import annotations

import json
import re
from pathlib import Path

MIN_REFS = 3
VIDEO = {".mp4", ".mov", ".m4v", ".webm", ".mkv"}
SLUG = re.compile(r"^[a-z0-9][a-z0-9_-]{0,62}$")


class UnknownBrand(LookupError):
    pass


class NoReferences(LookupError):
    pass


def slug(value: str, what: str) -> str:
    if not SLUG.match(value or ""):
        raise ValueError(f"{what} must be lowercase letters, numbers, - or _ (got {value!r})")
    return value


class Brand:
    def __init__(self, root: Path, name: str):
        self.name = slug(name, "brand")
        self.dir = Path(root) / "brands" / self.name
        if not (self.dir / "brand.json").is_file():
            raise UnknownBrand(f"no brand folder for {name!r} (brand.json missing): sync it from Drive first")
        self.info = json.loads((self.dir / "brand.json").read_text(encoding="utf-8"))

    def _text(self, name: str) -> str:
        p = self.dir / name
        return p.read_text(encoding="utf-8") if p.is_file() else ""

    @property
    def brief(self) -> str:
        return self._text("brief.md")

    @property
    def facts(self) -> str:
        return self._text("facts.md")

    @property
    def niche(self) -> str:
        return str(self.info.get("niche") or "")

    @property
    def products(self) -> list[Path]:
        d = self.dir / "products"
        return sorted(p for p in d.iterdir() if p.is_file()) if d.is_dir() else []

    def references(self, style: str, niche_root: Path) -> list[Path]:
        """The brand's own references of this style; topped up from its niche library when it has fewer than MIN_REFS."""
        style = slug(style, "style")

        def vids(d: Path) -> list[Path]:
            return sorted(p for p in d.iterdir() if p.suffix.lower() in VIDEO) if d.is_dir() else []

        own = vids(self.dir / "references" / style)
        refs = own if len(own) >= MIN_REFS else own + (vids(Path(niche_root) / self.niche / style) if self.niche else [])
        if not refs:
            raise NoReferences(f"{self.name} has no {style} references and its niche ({self.niche or 'not set'}) has none: "
                               f"add reels to references/{style}/ in the brand's Drive folder")
        return refs

    def style_card_path(self, style: str) -> Path:
        return self.dir / "style-cards" / f"{slug(style, 'style')}.json"
