"""Library rules, checked automatically for every block.

    python tools/check_library.py            (from services/block-library)

Rules (from docs/block-library-design.md):
1. The manifest is valid and every slot exists as a setting in the block's schema.
2. No baked-in copy: text-like settings must not have a default.
3. Every proprietary block runs the licence gate and the snippet exists.
4. No hard-coded colours (hex) in the block or its stylesheet: colours come from settings or the theme.
5. Settings follow Shopify's rules (unique ids, range default on a step, at most 101 steps, select default is an option).
6. Every `render 'x'` points at a snippet that exists.
9. At most 6 header/paragraph settings per app block (Shopify rejects the deploy otherwise).
7. Snippets never read `block.` or `section.` themselves: those are not visible inside {% render %}, the caller passes values in.
8. A block must not compare a snippet's OUTPUT (the theme editor wraps it in HTML comments): snippets are wrappers that print content.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

TOOLS_HOME = Path(__file__).resolve().parents[1]  # where the shared tools and schemas live (services/block-library)
ROOT = Path(os.environ.get("DTJ_APP_ROOT") or TOOLS_HOME).resolve()  # the second app sets DTJ_APP_ROOT


def ext_of(root: Path) -> Path:
    """The app's single theme extension folder (one extension per app), e.g. extensions/dtj-blocks."""
    found = [p for p in (root / "extensions").iterdir() if p.is_dir()]
    if len(found) != 1:
        raise SystemExit(f"{root}: expected exactly one folder under extensions/, found {[p.name for p in found]}")
    return found[0]


def schema_dir(root: Path) -> Path:
    return root / "schemas" if (root / "schemas").is_dir() else TOOLS_HOME / "schemas"
TEXT_LIKE = {"text", "textarea", "richtext", "inline_richtext"}
_SCHEMA = re.compile(r"{%-?\s*schema\s*-?%}(.*?){%-?\s*endschema\s*-?%}", re.S)
_HEX = re.compile(r"(?<![&\w])#[0-9A-Fa-f]{3,8}\b")  # not an HTML character code such as &#9733;
_RENDER = re.compile(r"{%-?\s*render\s+'([\w-]+)'")
_CAPTURED_GATE = re.compile(r"capture\s+\w+\s*-?%}\s*{%-?\s*render\s+'dtj-licence'")
_COMMENT = re.compile(r"{%-?\s*comment\s*-?%}.*?{%-?\s*endcomment\s*-?%}", re.S)
_SCOPE_READ = re.compile(r"\b(block|section)\.")


RESOURCE_PICKERS = {"product", "product_list", "collection", "collection_list", "article", "blog", "page", "link_list", "metaobject", "metaobject_list"}
_IMG = re.compile(r"<img\b[^>]*>")
_SINGLE_BRACE_END = re.compile(r"{{(?:(?!}).)*}(?!})", re.S)  # an output tag that a lone "}" closes early


def _css_sets_size(css: str, selector_regex: str) -> bool:
    """True if some rule whose selector list contains `selector_regex` sets width or height."""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)  # a comment above a rule must not become part of its selector
    for selector, declarations in re.findall(r"([^{}]+)\{([^{}]*)\}", css):
        if any(re.fullmatch(r"\s*" + selector_regex + r"(\s*|[:\[.#>+~ ].*)", part, re.S) for part in selector.split(",")) \
                and re.search(r"(^|[;\s])(width|height|min-width|max-width|aspect-ratio)\s*:", declarations):
            return True
    return False


def extract_schema(text: str) -> dict:
    match = _SCHEMA.search(text)
    if not match:
        raise ValueError("no {% schema %} block")
    return json.loads(match.group(1))


def strip_schema(text: str) -> str:
    return _SCHEMA.sub("", text)


def check_block(manifest_path: Path, root: Path = ROOT) -> list[str]:
    problems: list[str] = []
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    validator = Draft202012Validator(json.loads((schema_dir(root) / "block-manifest.schema.json").read_text(encoding="utf-8")))
    for err in validator.iter_errors(manifest):
        problems.append(f"manifest: {'/'.join(map(str, err.path)) or '(root)'}: {err.message}")
    if problems:
        return problems

    block_path = root / manifest["block_file"]
    if not block_path.is_file():
        return [f"block file missing: {manifest['block_file']}"]
    text = block_path.read_text(encoding="utf-8")
    try:
        schema = extract_schema(text)
    except ValueError as exc:
        return [f"{block_path.name}: {exc}"]
    except json.JSONDecodeError as exc:
        return [f"{block_path.name}: schema is not valid JSON ({exc})"]

    if schema.get("target") != "section":
        problems.append("schema.target must be 'section' for an app block")
    if "blocks" in schema:
        problems.append("app blocks cannot have nested blocks")

    settings = schema.get("settings", [])
    # rule 14: the schema name is limited to 25 characters (Shopify theme limits; deploy refused 'DTJ Option Picker (products)')
    if len(schema.get("name", "")) > 25:
        problems.append(f"schema name {schema.get('name')!r} is {len(schema['name'])} characters: Shopify allows 25")
    # rule 15: one resource picker per type in an app block. Shopify refused 'exceeds limit of 1 for type product' on 5 Oct 2026;
    # the same limit is assumed for the other picker types until Shopify proves otherwise.
    for picker in sorted(RESOURCE_PICKERS):
        count = sum(1 for s in settings if s.get("type") == picker)
        if count > 1:
            problems.append(f"{count} '{picker}' settings: an app block may have only 1 (use one product_list and per-position settings)")
    # rule 20: at most 75 interactive settings (everything except header/paragraph) in an app block. Shopify refused a real deploy:
    # "settings: must have a maximum of 75 for interactive settings" (6 Oct 2026, faithful Science Stats port; the own settings + the standard controls count).
    interactive = [s for s in settings if s.get("type") not in ("header", "paragraph")]
    if len(interactive) > 75:
        problems.append(f"{len(interactive)} interactive settings: Shopify allows at most 75 in an app block")
    non_interactive = [s for s in settings if s.get("type") in ("header", "paragraph")]
    if len(non_interactive) > 6:
        problems.append(f"{len(non_interactive)} header/paragraph settings: Shopify allows at most 6 non-interactive settings in an app block")
    # rule 21: a select option label is limited to 50 characters. Shopify refused the first DTJ Commerce release for exactly this (13 Oct 2026:
    # "option label is too long (max 50 characters)" on three blocks) although every local check had passed.
    for s in settings:
        for option in s.get("options", []) or []:
            if len(str(option.get("label", ""))) > 50:
                problems.append(f"setting {s.get('id')}: option label {option['label']!r} is {len(option['label'])} characters: Shopify allows 50")
    ids = [s["id"] for s in settings if "id" in s]
    if len(ids) != len(set(ids)):
        problems.append("duplicate setting ids")
    by_id = {s["id"]: s for s in settings if "id" in s}

    for slot in manifest["slots"]:
        setting = by_id.get(slot["id"])
        if setting is None:
            problems.append(f"slot {slot['id']} has no setting in the schema")
        elif setting.get("type") != slot["type"]:
            problems.append(f"slot {slot['id']} is {slot['type']} in the manifest but {setting.get('type')} in the schema")

    for s in settings:
        sid, stype = s.get("id"), s.get("type")
        if stype in TEXT_LIKE and "default" in s:
            problems.append(f"{sid}: text settings must not carry default copy")
        if stype == "range":
            if "unit" in s and not str(s["unit"]).strip():
                problems.append(f"{sid}: range unit can't be blank (leave the key out); Shopify refuses the deploy")
            lo, hi, step, dflt = s.get("min"), s.get("max"), s.get("step", 1), s.get("default")
            if dflt is None or not (lo <= dflt <= hi) or (dflt - lo) % step != 0:
                problems.append(f"{sid}: range default {dflt} is not on a step between {lo} and {hi}")
            if (hi - lo) / step > 101:
                problems.append(f"{sid}: more than 101 steps")
        if stype == "select" and s.get("default") not in [o["value"] for o in s.get("options", [])]:
            problems.append(f"{sid}: select default is not one of the options")
        if stype == "color" and "default" in s:
            problems.append(f"{sid}: colour settings must not have a hard-coded default")

    body = strip_schema(text)
    if manifest["licence"]:
        if "render 'dtj-licence'" not in body:
            problems.append("block does not run the licence gate (render 'dtj-licence')")
    # rule 11: Shopify's parser ends a {{ ... }} output at the FIRST single "}" (a literal such as '{count}' inside it breaks the
    # tag). Our local engine and Theme Check accept it; only Shopify's deploy validation refuses it (found 5 Oct 2026).
    for hit in _SINGLE_BRACE_END.finditer(_COMMENT.sub("", body)):
        problems.append(f"output expression ends at a single '}}': {hit.group(0)[:60]!r} (keep literal braces in a {{% assign %}} tag)")
    if _CAPTURED_GATE.search(body):
        problems.append("block captures the licence snippet's output: the gate must wrap the content, never be compared")
    # rule 18: a *_list setting (product_list, collection_list...) is read by looping over it, as Shopify documents. Reading it
    # by position (list[0]) is the suspected cause of the Option Picker staying empty in the real theme editor on 6 Oct 2026
    # with three valid products picked; the local engine accepts it, so only this rule catches it.
    code = _COMMENT.sub("", body)
    for s in settings:
        sid, stype = s.get("id"), s.get("type", "")
        if not sid or not stype.endswith("_list"):
            continue
        names = {f"block.settings.{sid}"}
        names |= set(re.findall(rf"assign\s+(\w+)\s*=\s*block\.settings\.{re.escape(sid)}\b(?!\.)", code))
        for name in sorted(names):
            if re.search(rf"(?<![\w.]){re.escape(name)}\s*\[", code):
                problems.append(f"{sid}: '{name}[...]' reads a {stype} by position: loop over it instead (for item in list)")
    for name in set(_RENDER.findall(body)):
        if not (ext_of(root) / "snippets" / f"{name}.liquid").is_file():
            problems.append(f"snippet '{name}' does not exist")

    snippets_dir = ext_of(root) / "snippets"
    for snippet in sorted(snippets_dir.glob("*.liquid")):
        code = _COMMENT.sub("", snippet.read_text(encoding="utf-8"))
        hit = _SCOPE_READ.search(code)
        if hit:
            problems.append(f"snippet {snippet.name} reads '{hit.group(1)}.' directly: pass it in as a parameter")

    css_names = [schema.get("stylesheet")] if schema.get("stylesheet") else []
    for source, label in [(body, block_path.name)] + [((ext_of(root) / "assets" / n).read_text(encoding="utf-8"), n)
                                                       for n in css_names if (ext_of(root) / "assets" / n).is_file()]:
        if _HEX.search(source):
            problems.append(f"{label}: hard-coded hex colour found")
    for n in css_names:
        if not (ext_of(root) / "assets" / n).is_file():
            problems.append(f"stylesheet {n} does not exist")

    # rule 13: a script loaded through the schema must stay under Theme Check's 10,000 byte limit (error level, found 5 Oct 2026)
    js_name = schema.get("javascript")
    if js_name:
        js_path = ext_of(root) / "assets" / js_name
        if not js_path.is_file():
            problems.append(f"script {js_name} does not exist")
        elif js_path.stat().st_size >= 10000:
            problems.append(f"script {js_name} is {js_path.stat().st_size} bytes: Theme Check errors at 10,000 (trim comments or split it)")

    # rule 10: every <img> (in the block or in a snippet it renders) needs an explicit size in the block's CSS.
    # Themes restyle images (Horizon stretches them to the container), so width/height attributes alone are not enough.
    css_text = "\n".join((ext_of(root) / "assets" / n).read_text(encoding="utf-8")
                         for n in css_names if (ext_of(root) / "assets" / n).is_file())
    markup = body + "\n".join((snippets_dir / f"{n}.liquid").read_text(encoding="utf-8")
                              for n in set(_RENDER.findall(body)) if (snippets_dir / f"{n}.liquid").is_file())
    for tag in _IMG.findall(markup):
        cls = re.search(r'class="([^"]+)"', tag)
        names = cls.group(1).split() if cls else []
        if not any(_css_sets_size(css_text, rf"\.{re.escape(c)}") for c in names) and not _css_sets_size(css_text, r"[^{},]*\bimg"):
            problems.append(f"<img{' class=' + repr(cls.group(1)) if cls else ''} has no explicit width/height in the block's CSS (themes stretch images)")

    # rule 19: a rule that sets `color` AND fills its background with currentColor paints the fill in that new colour
    # (white text on a "currentColor" fill = white on white; found 6 Oct 2026 on a tick that never showed). Put the text colour on a child.
    for selector, declarations in re.findall(r"([^{}]+)\{([^{}]*)\}", re.sub(r"/\*.*?\*/", "", css_text, flags=re.S)):
        solid_fill = re.search(r"background(-color)?\s*:\s*(var\([^;]*?currentcolor\s*\)|currentcolor)\s*(;|$)", declarations, re.I)  # a tint such as color-mix(...) is not a solid fill
        if solid_fill and re.search(r"(^|[;\s])color\s*:", declarations):
            problems.append(f"css rule '{' '.join(selector.split())[:60]}' sets color and a currentColor background: the fill takes the new colour (set color on a child element)")
    return problems


LIQUID_BUDGET_KB = 100  # Shopify: size of Liquid across all files in one app extension is capped (enforced)
WARN_AT_KB = 85


def liquid_budget(root: Path = ROOT) -> tuple[float, int]:
    ext = ext_of(root)
    files = list((ext / "blocks").glob("*.liquid")) + list((ext / "snippets").glob("*.liquid"))
    return sum(f.stat().st_size for f in files) / 1024, len(list((ext / "blocks").glob("*.liquid")))


def main() -> int:
    failed = False
    for manifest_path in sorted((ROOT / "manifests").glob("*.json")):
        problems = check_block(manifest_path)
        print(("FAIL " if problems else "ok   ") + manifest_path.stem)
        for p in problems:
            print("   -", p)
        failed = failed or bool(problems)
    kb, count = liquid_budget()
    level = "OVER THE LIMIT" if kb > LIQUID_BUDGET_KB else ("close to the limit" if kb >= WARN_AT_KB else "ok")
    print(f"\nsize budget: {kb:.1f} KB of {LIQUID_BUDGET_KB} KB Liquid, {count} of 30 blocks ({level})")
    return 1 if failed or kb > LIQUID_BUDGET_KB or count > 30 else 0


if __name__ == "__main__":
    sys.exit(main())
