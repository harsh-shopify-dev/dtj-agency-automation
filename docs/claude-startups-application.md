# Claude for Startups: application draft (13 Oct 2026)

Copy each answer into the matching field of the Console form. `[confirm]` = check or fill before sending; don't send anything
that isn't true (the program re-reviews applications). Organization type in the Console sign-up: **Small or medium business**.

**Company:** Digital Tushar Joshi (DTJ) · https://digitaltusharjoshi.com · India [confirm city: Rajkot, Gujarat?]
**Stage / funding:** Bootstrapped [confirm]. **Team:** [confirm number] people in-house (media buyers, creative strategists,
CRO & landing page experts, copywriters, data & performance analysts). **Founder:** Tushar Joshi.

## One line
DTJ is an AI-native growth partner for Indian D2C brands: we run their ads, stores and landing pages, and we are rebuilding
the agency's repeatable work (product pages, audits, landing pages, reporting) as Claude-powered automation.

## What are you building with Claude? (short)
A "store factory" for D2C brands. A teammate sends a product link to our Telegram bot; n8n workflows gather the store's data;
Claude designs the full product page from our own block library, runs design and conversion checks, and writes it to the
store's draft (unpublished) theme for a human to approve. Around it we have built Claude skills for our audit work (Meta ads,
COD/RTO, unit economics, landing pages) and use Claude Code to build and test our own lead pages.

## How do you use Claude today?
- Claude Code builds and maintains our code: the store-factory workflows (n8n), the Shopify page builder, and our landing pages.
- Claude does the AI step inside the store factory (research, page design, checks) while a teammate is in the loop.
- Strict guardrails are in the code, not just prompts: draft themes only, every client-visible or money-moving action needs a
  named human's yes, numbers must come from data, no secrets in prompts.

## How would credits and support help?
We are moving the unattended AI steps (page design, audits, monitoring) onto the Claude API so they run without a laptop in
the loop. Credits and higher rate limits would cover that move and our first client volume; Applied AI office hours would help
us design the multi-step page-design agent and its evaluations (we already keep golden test sets).

## Expected usage [confirm]
Claude API for page design and audits across [__] client stores; Claude Code for the team's development work.

## Anything else
Built and run from India for Indian D2C founders, most of them non-technical; our pages and reports are written in plain founder
language. [Add one real result if you want: e.g. a store-factory page shipped to a client draft theme, with the date.]
