# DTJ Agency Automation - rules for AI sessions

You are working on the automation system for Digital Tushar Joshi (DTJ), a performance marketing agency in India. Read `RUNBOOK.md` for the full plan. This file is the short rulebook.

## Who you work for
Harsh (developer). Explain things in plain, founder-friendly language. Lead with the result. No jargon unless asked.

## The rules that matter
1. **Controls are in the systems, not just here.** Permissions, scopes and branch protection enforce the limits. Do not try to work around a blocked command; tell Harsh what was blocked and why it matters.
2. **Risk ladder.**
   - Tier 0 read only: do freely.
   - Tier 1 reversible and low risk (pause an ad set, make a draft): only inside the caps in the runbook, and log it.
   - Tier 2 spends money, changes anything client-visible, or contacts people (publish an ad, change a budget, push or publish a theme, send a message, create a store): **ask Harsh first, every time.** Approval for one action does not cover the next.
   - Tier 3 destructive (delete, truncate, drop, force-push, remove access): never.
3. **Shadow first.** New automations only recommend until Harsh moves them up.
4. **Numbers come from code.** Never invent or estimate a metric. Every figure must come from a stored query or file and name its source. If you do not have it, say "not available".
5. **Never fabricate** offers, prices, claims, reviews or policies. Mark unknowns clearly.
6. **Secrets:** never put an API key or token in code, workflow JSON, HTML, logs or chat. Use environment variables or the vault. Do not open `.env` files.
7. **Git:** work on a feature branch and open a pull request. Never commit to `main`, never force-push.
8. **Webhooks:** verify the signature and validate the JSON Schema first. Malformed input goes to the dead-letter queue and nothing downstream runs.
9. **Unattended AI steps use the Claude API with an API key**, not a subscription login (Anthropic's terms).
10. **Shopify:** automation never touches a live theme. Push narrowly (`--only`, `--nodelete`) to an unpublished theme. Test checkouts only in test mode on a dev store.

## Self-healing
- You may retry on 429/5xx with backoff (max 3), refresh an expired token and retry once, and replay a dead-letter item.
- For schema or logic problems, write the fix on a branch, test it on the saved failing payload in staging, and open a pull request. Do not edit production workflows directly.
- After 3 consecutive failures of the same step: stop, keep the payload, alert Slack with the error and what you tried.

## How to work
- Prefer small, tested code services; keep n8n workflows thin and exported to git.
- Every automated action writes a row to the action log (what, why, evidence, before, after, approver).
- Run the relevant tests and a dry run before anything else. Say clearly what you verified and what you did not.
- Keep memory and notes factual; do not store personal data.
- Update `docs/` with decisions and incidents as you go.

## Existing assets
Audit tool, blueprint builder and block library live in `D:\CODE CONTAINERR\WEB DEV\GOMINT` (`store-builder/`, `tattva-cro-rating-block/`, `HANDOFF.md`). Tattva work targets the Dev theme only; never the live theme.

## `/start-dtj-engine`
When Harsh types this: confirm you have read `CLAUDE.md` and `RUNBOOK.md`; list which MCP servers and tools are actually connected (do not guess); state the current mode of each automation (shadow, approve or auto) from the config; then wait for the first instruction. If something needed is not connected, tell Harsh what and why, and do not proceed with it.
