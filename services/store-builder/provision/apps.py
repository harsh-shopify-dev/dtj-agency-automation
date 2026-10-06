"""App checklist. The Admin API cannot install apps (the store owner approves each install),
so this writes a to-do list for a person instead of pretending to install anything."""
from __future__ import annotations

# Names only. Which apps a brand needs is a decision for Harsh; nothing here is a recommendation of a vendor.
DEFAULT_CATEGORIES = [
    ("Reviews", "Product reviews with structured data (rating stars in search)"),
    ("Email / SMS", "Lifecycle marketing: abandoned cart, welcome, post-purchase"),
    ("Analytics", "GA4 / Meta pixel / Clarity connected and verified"),
    ("Payments (India)", "COD / prepaid options, if the brand sells in India"),
    ("Shipping", "Courier / tracking app, if used"),
]


def checklist_markdown(brand: dict, chosen: dict[str, str] | None = None) -> str:
    chosen = chosen or {}
    lines = [f"# App checklist - {brand['brand_name']}", "",
             "Install and connect these by hand in the store admin. Tick each one only after it works.", ""]
    for category, purpose in DEFAULT_CATEGORIES:
        app = chosen.get(category, "[[TODO: choose app]]")
        lines.append(f"- [ ] **{category}**: {app}  \n  Purpose: {purpose}")
    lines += ["", "Theme snippets for any app (app embeds, scripts) are added only after Harsh approves the specific app."]
    return "\n".join(lines) + "\n"
