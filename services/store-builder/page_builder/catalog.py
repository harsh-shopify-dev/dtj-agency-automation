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
VIDEO_PREFIX = "shopify://files/videos/"  # a video in the store's Files (Content > Files)


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
            elif kind == "range" and abs(((value - s["min"]) / s.get("step", 1)) - round((value - s["min"]) / s.get("step", 1))) > 1e-6:
                # Shopify refuses the whole file for a value between steps ("must be a step in the range", 10 Oct 2026)
                problems.append(f"{app}/{block}: {key}={value!r} is not on the {s.get('step', 1)} step from {s['min']}")
            elif kind == "checkbox" and not isinstance(value, bool):
                problems.append(f"{app}/{block}: {key} must be true or false")
            elif kind == "image_picker" and not str(value).startswith(IMAGE_PREFIX):
                problems.append(f"{app}/{block}: {key} must be {IMAGE_PREFIX}<file>, got {value!r}")
            elif kind == "video" and not str(value).startswith(VIDEO_PREFIX):
                problems.append(f"{app}/{block}: {key} must be {VIDEO_PREFIX}<file>, got {value!r}")
            elif kind == "color" and not re.fullmatch(r"#[0-9A-Fa-f]{6}([0-9A-Fa-f]{2})?", str(value)):
                problems.append(f"{app}/{block}: {key}={value!r} is not a hex colour")
            elif kind in ("text", "textarea", "inline_richtext", "richtext") and not isinstance(value, str):
                problems.append(f"{app}/{block}: {key} must be text")
        return problems

    def text_settings(self, app: str, block: str) -> set[str]:
        return {k for k, s in self.settings(app, block).items() if s["type"] in ("text", "textarea", "inline_richtext", "richtext")}


_TYPE = re.compile(r"^shopify://apps/(?P<handle>[^/]+)/blocks/(?P<block>[^/]+)/(?P<uuid>[^/]+)$")


def load_client_registry(path: str | Path) -> dict:
    """A client's own app copies: {"apps": {"dtj-blocks": {"handle": ..., "uuid": ...}, ...}}, read from blocks placed in that store's theme.
    A duplicated app has its own handle and extension uuid, so a page built with our addresses would show nothing in the client's store."""
    apps = json.loads(Path(path).read_text(encoding="utf-8"))["apps"]
    for app, entry in apps.items():
        if entry.get("handle") == "pending":
            raise ValueError(f"client registry: {app} is not installed yet (handle pending): run client_registry.py again after the install")
        if app not in registry():
            raise ValueError(f"client registry: unknown app {app!r}")
        if not (re.fullmatch(r"[a-z0-9][a-z0-9-]*", entry.get("handle", "")) and re.fullmatch(r"[0-9a-f-]{36}", entry.get("uuid", ""))):
            raise ValueError(f"client registry: {app} needs a handle and a 36-character uuid")
    return apps


def to_client(template: dict, client: dict, reg: dict | None = None) -> dict:
    """The same page with every DTJ block pointing at the client's copy of its app. Any DTJ block the client registry does not cover stops it."""
    reg = reg or registry()
    ours = {(app, entry["uuid"]): app for app, entry in reg.items()}

    def walk(node):
        if isinstance(node, dict):
            out = {k: walk(v) for k, v in node.items()}
            m = _TYPE.match(str(node.get("type", "")))
            if m and (m["handle"], m["uuid"]) in ours:
                app = ours[(m["handle"], m["uuid"])]
                if app not in client:
                    raise ValueError(f"the client registry has no copy of {app} (block {m['block']})")
                out["type"] = f"shopify://apps/{client[app]['handle']}/blocks/{m['block']}/{client[app]['uuid']}"
            return out
        if isinstance(node, list):
            return [walk(v) for v in node]
        return node

    return walk(template)
