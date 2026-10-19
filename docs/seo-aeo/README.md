# DTJ search engine: SEO and AEO for digitaltusharjoshi.com

Started 14 Oct 2026 (Harsh: "create an AI Automation that will do the SEO and AEO of DTJ").

**Harsh's decisions, 14 Oct 2026:**
- The Claude **API key** writes, unattended, weekly.
- New pages go into WordPress as **unpublished drafts** only.

**Upgraded the same day** after Harsh shared Jono Catliff's SEO-agent framework. Harsh chose:
- **"b first month":** the engine prepares each week's site fixes, and a person approves the batch with one yes.
- **DataForSEO** for keyword and search data. Harsh: "I have 0 knowledge about SEO", so the engine does the keyword research itself.
- **Plain founder English:** not the parked dhandho/rokda voice (DTJ-CONTEXT.md, 13 Oct).

## The Monday routine (09:00 IST, `.github/workflows/seo-weekly.yml`)
| # | Step | Tier | Paid? |
|---|---|---|---|
| 1 | **Website check**: every page in the sitemap; findings with the page and the evidence | 0 | Free |
| 2 | **Fixes batch**: exact before → after changes. Waits for one yes; nothing is changed here. | prepares Tier 2 | Claude, for descriptions and alt text |
| 3 | **Keyword plan**, refreshed every 28 days | 0 | DataForSEO, inside the cap |
| 4 | **"Do AI assistants name DTJ?"**: Claude, ChatGPT, Perplexity and Gemini, by city, Gujarat, India and DTJ by name | 0 | Claude + DataForSEO |
| 5 | **Page of the week**, alternating a blog article ("tide") and a city service page ("boat"). Before writing, it reads the **top 3 Google results** for the main keyword. | 0 | Both |
| 6 | **Code gate**, then a WordPress **draft** (only in `approve` mode) or a file | 1 | |
| 7 | **Report**, in plain words, every number with its source | | |

**What each step does:**

- **Fixes batch** (`fixer.py`, approved and applied by `apply_batch.py`):
  - **Auto**, written through the DTJ SEO Bridge plugin:
    - hide templates and the Sample Page from Google;
    - new Google titles and descriptions (AI-written, gate-checked);
    - image alt text (AI looks at the image; no numbers);
    - business details: Organization plus one entry per real office, Rajkot and Ahmedabad.
  - **For a person:** the llms.txt tagline, author archives, H1s, question headings, thin pages, and the two posts with claims we can't source.
  - **Apply:** the Yes in Telegram (see "The Telegram yes"); or GitHub > Actions > "SEO apply fixes", with the Monday run number
    and the approver's name (and the batch id). Or, in Claude Code:
    `python -m seo_engine.apply_batch --batch <folder>/fixes.json --approved-by "<name>"`.
  - **Safeguards:**
    - The kill switch must be on and dry run off.
    - A change is skipped if the live page no longer shows the "before" (someone edited it).
    - After writing, the live page is checked up to 3 times.
    - Every old value is logged, and `--undo` restores them, again with a named approver.
- **Keyword plan** (`keywords.py`, data from `dataforseo.py`):
  - Ideas come from the services × places × founder pains in `data/seeds.json`.
  - **Filters** (from the framework):
    - at least 50 searches a month, or at least 10 for a city search (few searches, but close to buying);
    - difficulty 30 or less;
    - cost per click above 0;
    - off-topic words removed (jobs, courses, …).
  - **Intent:** informational → blog article, commercial/transactional → service or city page.
  - **Groups:** keywords whose Google top 10 share at least 3 pages become one page, aiming for 5 or more keywords per page.
- **Top 3** (`serp_skeleton.py`):
  - It reads the headings, length, questions and FAQs of the 3 best real results, skipping directories and social sites.
  - The writer gets that **outline** only. Their text is never stored or sent to the model.
  - The gate blocks any 10-word phrase copied from them.
- **City pages** (`city_page.py`):
  - The grid is the 6 services × Rajkot, Ahmedabad, Surat and Vadodara.
  - A page is written **only** when the city has real proof in `data/local_proof.json`: at least 1 client from there who agreed
    to be named, with a result, plus an office, a review or a photo.
  - It is blocked if more than 25% of its 5-word phrases also appear on another city page (Google's doorway-page penalty).
  - It never mentions an office in a city where DTJ has none.
- **Voice** (`prompts/writer.md`):
  - Plain founder English with personality: "you", short lines, an opinion with the reason in money terms (orders, rupees, profit), real checks the founder can do today.
  - No Gujlish, no agency filler.
  - It may cite official help pages (Shopify, Meta, Google, Amazon Seller Central, government).
- **The gate** (`gates.py`) stays. It blocks:
  - numbers that aren't in `facts.json` or the city's proof;
  - best/#1 claims, guarantees, response times, contract terms;
  - a "call with Tushar";
  - a COD/RTO promise;
  - talk of how DTJ works inside;
  - links to other agencies.

  This is CLAUDE.md rule 5, not an AEO choice.

## The strategy: local → state → national, with answers from week 1
Harsh, 14 Oct: "local SEO then state wise then nationally".

**Track A, the place ladder:**
1. **Local, weeks 1-6: Rajkot (head office) and Ahmedabad.**
   - A Google Business Profile for each.
   - The same name, address and phone everywhere.
   - Office details in the format Google reads (in the fixes batch).
   - City pages once there is proof.
   - Client reviews that name the service and city.
2. **State, weeks 6-14: Gujarat.**
   - A Gujarat page.
   - Surat and Vadodara only with real clients there.
   - Industry pages where there is proof: food (Royal Dosa Paper), sarees and textiles (Sindhoi Patola Arts).
   - Gujarat press and associations.
3. **National, month 4+.**
   - The six "…agency in India" pages strengthened with case studies.
   - Clutch and GoodFirms listings and reviews.

**Track B, problem-answer articles**, across India every week from week 1.

**Not in scope:** the Australia and Canada offices.

**How we know it works:**
- Count of tracked questions per assistant that name or cite DTJ.
- Website-check counts.
- Keyword positions once Search Console is connected.

No predictions. Harsh sets the targets for moving between phases.

## First real run (14 Oct 2026, free, `.work/seo/2026-10-14/`)
- **24 pages:** 3 to fix now, 52 soon, 49 later.
- **Fixes batch `fix-2026-10-14`:** 4 ready to apply:
  - hide `/elementor-hf/footer/`, `/elementor-hf/header/` and `/sample-page/` from Google;
  - add the Rajkot and Ahmedabad business details.
- **Written on the first live run:** 15 titles/descriptions and 10 image alt texts.
- **6 tasks for a person:**
  - llms.txt "#1" tagline;
  - author archive `dream-dev`;
  - 18 pages without exactly one H1;
  - 13 pages without question headings;
  - 3 thin pages;
  - the two posts with claims we can't source.

## Running it
```
cd services/seo-engine
python -m unittest discover -s tests          # 52 tests
python -m seo_engine.run_weekly               # free: check + plans
python -m seo_engine.run_weekly --live        # + AI and data steps (keys below)
python -m seo_engine.apply_batch --batch ../../.work/seo/<date>/fixes.json --approved-by "<name>"
```
The schedules start once both workflow files are on the default branch.

**GitHub settings** (Settings > Secrets and variables > Actions):

| Kind | Name | Notes |
|---|---|---|
| Secret | `ANTHROPIC_API_KEY` | From Bitwarden |
| Secret | `DATAFORSEO_LOGIN`, `DATAFORSEO_PASSWORD` | From Bitwarden |
| Secret | `WP_USER`, `WP_APP_PASSWORD` | A WordPress application password for an **Editor** |
| Variable | `SEO_LIVE` | `true` turns on the AI and data steps |
| Variable | `DFS_MAX_USD` | DataForSEO cap per run; default 3 |
| Variable | `AUTOMATION_ENABLED`, `SEO_DRY_RUN` | Kill switch and dry run |
| Variable | `SEO_MODE` | `shadow` keeps drafts as files; `approve` puts drafts into WordPress |

**Costs:**
- **DataForSEO:** stops itself at `DFS_MAX_USD` per run. It adds up the cost each answer states.
- **Claude:** each run reports its cost from the usage figures. Set a monthly cap in the Anthropic Console too.

## The Telegram yes (n8n, built 19 Oct 2026)
Full details and setup: `n8n/seo-engine/README.md`.
- **Monday:** after "SEO weekly", its last step sends the report and the batch to n8n, signed (secret `N8N_SEO_REPORT_KEY`). The
  DTJ bot then sends every active admin the report file plus the fixes, with **Yes / No**.
- **No Yes button** when nothing is ready, or when the check missed part of the site.
- **Who may say yes:** Harsh; or, when he can't be reached, a teammate by name, who confirms that first. The yes is recorded as
  `<name> (Harsh not reachable)`. One answer per batch, the newest batch only, at most 7 days old.
- **Shadow (now):** the answer is recorded in n8n (`dtj_seo_batches`, `dtj_action_log`) and nothing is applied. The reply gives
  the exact "SEO apply fixes" inputs to run by hand.
- **On (Harsh's yes):** a yes starts "SEO apply fixes" itself, with the run number, the name and the batch id. The new optional
  input `batch_id` makes that workflow refuse any batch other than the approved one.
- A report that fails its signature or schema check goes to `dtj_dead_letter`, and the admins are told.

## Not verified yet (be honest about this)
- **The AI steps and DataForSEO** have only run against test data. There are no keys yet.
- **Data that only exists after signing up:**
  - DataForSEO's place names ("Rajkot,Gujarat,India"): the code falls back to all of India if a name is refused;
  - the AI model names (`gpt-4.1`, `sonar`, `gemini-2.5-flash`).

  Both are checked on the first live run.
- **The bridge plugin** (`wordpress-plugin/dtj-seo-bridge.php`) has not run on any WordPress.
  - PHP isn't installed on this laptop, so it isn't even syntax-checked.
  - **Install it on a staging copy first.**
  - Whether Yoast shows a description written this way is exactly what `apply_batch`'s live check reports.

## Open items (need a person)
1. **A Claude API key** and **a DataForSEO account.** Signing up is DTJ's to do; it's pay-as-you-go. Both go into Bitwarden, then GitHub secrets.
2. **A WordPress Editor user and application password.** An administrator installs the bridge plugin, after testing on staging.
3. **Google Business Profiles** for Rajkot and Ahmedabad: do they exist, and who manages them?
4. **City clients** for `data/local_proof.json`: name, result, consent and source.
5. **Search Console access**, for real positions and clicks per keyword. Not built yet.
6. **A Telegram message with the report and the yes/no for the batch** (n8n). **Built 19 Oct 2026, in shadow** (see "The Telegram yes"
   below). It needs the signing key, the n8n credential and Harsh's yes to publish. Until then the report is in the GitHub run summary.
7. **The four unsourced stats** (₹70Cr+, 90+, 16X, 208+) stay blocked until DTJ sources them.
