"""The block catalog: reads the REAL settings of every DTJ block from the generated block files and checks a page's settings against them
(unknown id, select value, range, picture reference, text length). This is what stops a page from carrying a setting Shopify would ignore."""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

HERE = Path(__file__).resolve().parent
SERVICES = HERE.parents[1]  # .../services
_SCHEMA = re.compile(r"\{%-?\s*schema\s*-?%\}(.*?)\{%-?\s*endschema\s*-?%\}", re.S)
IMAGE_PREFIX = "shopify://shop_images/"


@lru_cache(maxsize=1)
def registry(path: str | None = None) -> dict:
    return json.loads(Path(path or HERE / "registry.json").read_text(encoding="utf-8"))["apps"]


class Catalog:
    def __init__(self, reg: dict | None = None, services: Path = SERVICES):
        self.reg = reg or registry()
        self.services = services
        self._cache: dict[tuple[str, str], dict] = {}

    def block_ref(self, app: str, block: str) -> str:
        if app not in self.reg:
            raise KeyError(f"unknown app {app!r}")
        return f"shopify://apps/{app}/blocks/dtj-{block}/{self.reg[app]['uuid']}"

    def schema(self, app: str, block: str) -> dict:
        key = (app, block)
        if key not in self._cache:
            path = self.services / self.reg[app]["folder"] / f"dtj-{block}.liquid"
            if not path.is_file():
                raise KeyError(f"block {app}/{block} not found at {path}")
            self._cache[key] = json.loads(_SCHEMA.search(path.read_text(encoding="utf-8")).group(1))
        return self._cache[key]

    def settings(self, app: str, block: str) -> dict[str, dict]:
        return {s["id"]: s for s in self.schema(app, block)["settings"] if "id" in s}

    def has(self, app: str, block: str, setting: str) -> bool:
        return setting in self.settings(app, block)

    def default(self, app: str, block: str, setting: str):
        return self.settings(app, block).get(setting, {}).get("default")

    def validate(self, app: str, block: str, values: dict) -> list[str]:
        """Problems with a block's settings, empty when it is valid."""
        spec = self.settings(app, block)
        problems = []
        for key, value in values.items():
            s = spec.get(key)
            if s is None:
                problems.append(f"{app}/{block}: unknown setting {key!r}")
                continue
            kind = s["type"]
            if kind == "select" and str(value) not in [o["value"] for o in s["options"]]:
                problems.append(f"{app}/{block}: {key}={value!r} is not one of {[o['value'] for o in s['options']]}")
            elif kind == "range" and not (isinstance(value, (int, float)) and s["min"] <= value <= s["max"]):
                problems.append(f"{app}/{block}: {key}={value!r} is outside {s['min']}..{s['max']}")
            elif kind == "checkbox" and not isinstance(value, bool):
                problems.append(f"{app}/{block}: {key} must be true or false")
            elif kind == "image_picker" and not str(value).startswith(IMAGE_PREFIX):
                problems.append(f"{app}/{block}: {key} must be {IMAGE_PREFIX}<file>, got {value!r}")
            elif kind == "color" and not re.fullmatch(r"#[0-9A-Fa-f]{6}([0-9A-Fa-f]{2})?", str(value)):
                problems.append(f"{app}/{block}: {key}={value!r} is not a hex colour")
            elif kind in ("text", "textarea", "inline_richtext", "richtext") and not isinstance(value, str):
                problems.append(f"{app}/{block}: {key} must be text")
        return problems

    def text_settings(self, app: str, block: str) -> set[str]:
        return {k for k, s in self.settings(app, block).items() if s["type"] in ("text", "textarea", "inline_richtext", "richtext")}
