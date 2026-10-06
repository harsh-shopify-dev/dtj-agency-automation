# Block library as a Shopify theme app extension (design, 5 Oct 2026)

Status (updated 6 Oct 2026): **Route 3 is built and released.** App "DTJ Blocks" is installed on the test store `elevate-with-harsh`, the licence kill switch is proven in the theme editor, and 7 blocks are live (release `dtj-blocks-12`, 69.4 KB of the 100 KB cap). Where this design says "design only" or "[VERIFY]" below, it is the original text: the current facts, limits learned from Shopify's deploy checks and all errors are in `docs/HANDOFF.md` (sections 8 to 11). Visual look and the Add-ons cart behaviour are not yet verified.
Original status: decision made by Harsh: Route 3 (theme app extension).
Why Harsh chose it: our proprietary block code stays on Shopify's side under our app, not in the client's theme files, and access can be switched off if a client churns.

## What this gives and what it does not (be honest with clients and ourselves)
- **Protects:** the Liquid source and settings of our blocks are not in the client's theme, so a theme export or duplicate does not contain them. No theme-file patching per theme family.
- **Does not protect:** the rendered HTML, CSS and JavaScript sent to shoppers is public in any browser. IP protection here is about the source and the licence, not about hiding the front end.
- **Revoking on churn, two ways:**
  1. Client uninstalls the app (needs the client; a churned client may not).
  2. **Licence flag (ours, works without the client):** each block starts with a check of an app-DATA metafield (stored on the app installation, hidden from the admin, per store; Liquid: `app.metafields.dtj.licence`; written with ownerId = `currentAppInstallation.id`; it cannot be created through `shopify.app.toml`); we set it to inactive through our app's token and the block renders nothing. Takes effect on the next page render (cache delay possible). **[VERIFY]** that app-owned metafields are readable from app blocks and that writing them needs only our app's own scope.
- **Left behind after revocation:** the block *references* in the client's template JSON (they show as empty or "app removed"), plus the client's own text in those block settings (it is their copy). We never delete things in a client's theme (tier 3). Any metafields/metaobjects our blocks created also remain.
- **Contract:** the revocation right and what the client keeps should be written into the service agreement (confirm with a qualified professional).

## FINDING (5 Oct 2026): the "our side" kill switch needs a hosted service for client stores
Writing the licence flag needs an access token for that store.
- **Stores in our own Shopify organization:** the app's client credentials grant works (client id + secret from the Dev Dashboard, token valid 24 h). Docs: "client credentials cannot reach a store outside your organization, including a client's store". This is what `tools/licence.py` uses, and it is enough for our own test stores.
- **Client stores (outside our org):** the app is installed through a custom-distribution link, and we only get a token if a backend catches the install (authorization code grant) and keeps that store's offline token in a secure vault. So the instant revoke promised to clients needs: a small hosted service (OAuth callback, token vault, one endpoint that sets `dtj.licence`), uptime monitoring and a runbook. Without it, revocation depends on the client uninstalling.
- **Alternative to consider:** serve the block markup from our server through an app proxy so no markup ships unless the licence is active. Stronger IP protection, but adds latency and an uptime dependency to every page view. Not planned.
- Needs Harsh's decision before any client install: build the backend (suggested next phase after the proof), or accept uninstall-only revocation for now.
- Also found: `shopify app dev` and `shopify app execute` only see **Dev**-type stores; a **Client Transfer** store such as `elevate-with-harsh` is invisible to them. Install worked through a custom-distribution link.

## Architecture
```
dtj-block-library/                (new repo, ours)  <- single source of truth
  app/                            Shopify app (custom distribution, owned by DTJ's Partner org)
    extensions/dtj-blocks/        theme app extension
      blocks/<id>.liquid          one app block per library block, {% schema %} generated from the manifest
      assets/<id>.css / .js       scoped to .dtj-<id>, tokens --dtj-*, JS as plain custom elements
      snippets/                   shared pieces, incl. the licence check
  manifests/<id>.json             settings schema, content slots, placement, data needs, reference image
  recipes/                        ordered block lists per page type and niche + slot bindings to brand-config fields
  tools/                          build (manifest -> block files), install (recipe+brand+copy -> template JSON), verify
```
Master theme (Horizon fork) becomes a **clean base with no proprietary blocks**; our blocks arrive only through the app.

## How automation places blocks
1. Deploy the extension (a Tier 2 action: `shopify app deploy` creates a version) and install the app on the target store (client approves the install link).
2. The installer adds app-block entries to the unpublished theme's template JSON (`shopify://apps/<app>/blocks/<block>/<uuid>`) inside a section that accepts `@app`, fills each block's settings from the brand copy, and pushes only those files.
3. Blocks with an unfilled required slot are not added; the run report lists them. Never invent copy.

## Checked so far in the master theme (read-only)
- Horizon `sections/product-information.liquid` declares `"type": "@app"`. `blocks/group.liquid` and `sections/section.liquid` also accept `@app`, so a Group block inside the product details can hold app blocks. **[VERIFY]** by actually placing one in the test theme.
- `templates/product.json` main section has top-level blocks `_product-media-gallery`, `_product-details`, `disclosures`. App blocks must go in the details column through a nested accepting block. Placement depth is the thing to prove first.

## Limits and risks to prove before committing the whole library
- App blocks support a **subset of setting types** and no section presets. Existing pack sections use `font_picker`, big settings lists and a few JS assets. **[VERIFY]** which settings carry over; some need redesign.
- App blocks can only sit where the theme exposes `@app`. Dawn's `main-product` does; custom client themes may not. Themes that are not Online Store 2.0 are unsupported.
- Needs a Shopify Partner app, per-store install and approval, and `shopify app deploy` versions. Extension size/count limits **[VERIFY]**.
- Product-bound data (`closest.product` in Horizon) is `product` in app blocks on product templates; blocks must be written for that.
- Performance: confirm with Lighthouse on the test theme.

## Plan (each store/GitHub/app action needs approval)
0. Harsh: confirm a Partner org exists and create the app (custom distribution) in the Partner dashboard, or authorise `shopify app init` scaffolding locally.
1. **Proof (one block):** scaffold the app and a theme app extension with ONE simple block (e.g. a trust row) plus the licence check; run `shopify app dev` against `elevate-with-harsh`; place it in the unpublished theme's product page; confirm it renders, then flip the licence flag and confirm it disappears.
2. Write the manifest format and the builder; convert blocks one by one from Harsh's reference images (have / partial / missing table first).
3. Installer + recipes; brand copy; Lighthouse and checkout tests.
4. Unattended AI copy (Claude API key, evals) and the Slack/n8n hand-off.

## Open decisions for Harsh
- Partner org and app name; new GitHub repo `harsh-shopify-dev/dtj-block-library` (creating it is an outward action).
- Reference images folder (e.g. `.work/block-refs/`).
- First block for the proof (suggest a trust row, it is on the known missing list).
