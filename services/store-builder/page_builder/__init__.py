"""Page builder: brand profile + product facts -> a validated Shopify product page template made only of DTJ blocks.

The design JUDGMENT lives here as code and data, not in a prompt:
  direction.py   brand -> design direction (colours with checked contrast, shape, type treatment, density, motion), each choice with its reason
  recipes/       the conversion-minded page structure per category (what goes where and why)
  sections.py    facts -> block settings; a section whose facts are missing is OMITTED, never filled with invented copy
  rules.py       lint rules that fail a page that breaks the judgment (contrast, gutters, rhythm, bands, provenance, traceable numbers)
  copy_contract  the only thing a Claude API step may do: write short structure copy inside a validated contract
See docs/page-builder-design-judgment.md for the why behind every rule.
"""
