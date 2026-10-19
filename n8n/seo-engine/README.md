# The Monday SEO report in Telegram, with one yes per fixes batch

Built 19 Oct 2026. It answers Harsh's question that day: "is the SEO automation ready in n8n?" This is the missing piece:
docs/seo-aeo/README.md, open item 6.

## What happens every Monday
1. GitHub runs **SEO weekly** (`.github/workflows/seo-weekly.yml`). It checks the site and prepares the week's **fixes batch**.
   Nothing on the site changes in this step.
2. That run's last step, `notify_n8n.py`, sends the report and the batch to n8n, **signed**:
   - a JWT signed with the secret `N8N_SEO_REPORT_KEY`;
   - its claims carry the run number, the batch id and the SHA-256 of the report text;
   - it is valid for 10 minutes.
3. n8n's workflow **SEO Engine: Weekly Report** checks it:
   - **The webhook** turns away any request whose signature doesn't verify against the credential "DTJ SEO Report Key".
   - **Check the Report** checks the claims and the SHA-256, then the schema (`schemas/seo-weekly-report.schema.json`).
   - **Anything that fails** goes to the data table `dtj_dead_letter`. The admins get a plain-words alert, and nothing else runs
     (CLAUDE.md rule 8).
4. Every **active admin** in `dtj_bot_users` gets two messages from the DTJ bot:
   - the full report as a file;
   - a short message: the counts, each change a yes would apply, and **Yes / No** buttons.

   There is **no Yes button** when there is nothing to apply, or when the website check missed part of the site. The report itself
   says "run the check again before saying yes" in that case.
5. **A tap.** The bot's "Who Is It" hands every `seo:` button to this workflow's answer lane. That lane checks four things:
   - the person is an active team member;
   - the batch is still waiting;
   - it is the newest batch;
   - it is at most 7 days old.

   Then it records the answer on the batch's row in `dtj_seo_batches` and a row in `dtj_action_log`. The person who tapped and the
   other admins are told.
6. **Who may say yes** (CLAUDE.md rule 2):
   - Harsh: the active bot user whose name contains the word "Harsh".
   - A teammate, only when Harsh can't be reached. They confirm that with a second button, and their yes is recorded as
     `<name> (Harsh not reachable)`.
   - One answer per batch. A second tap at the same moment isn't counted: the row is only updated while it still says "waiting".

## Shadow first (now)
`APPLY_ON = false` in `answer_plan.js` and `report_messages.js` (a test keeps the two the same). In this mode:
- a yes is **recorded only**;
- nothing on the site changes;
- the reply tells the person how to start "SEO apply fixes" by hand, with the run number, their name and the batch id.

**Turning it on is Harsh's yes:**
1. Set both lines to `true`.
2. Run the tests.
3. Run `python n8n/seo-engine/build_workflow.py`, then `python n8n/seo-engine/deploy_seo_engine.py --apply`.
4. Publish.

From then on, a yes starts GitHub's **SEO apply fixes** (`seo-apply.yml`) with:
- `run_id` = the Monday run;
- `approved_by` = the name;
- `batch_id` = the batch.

`seo-apply.yml` refuses to apply anything if that run's batch isn't exactly the approved one.

## Setting it up (each step once; the bold ones need Harsh's yes)
1. **The signing key:** `python n8n/seo-engine/deploy_seo_engine.py --new-key`.
   - It saves the key on this laptop (Windows user variable `DTJ_SEO_REPORT_KEY`) and as the GitHub secret `N8N_SEO_REPORT_KEY`.
   - It is never shown. Keep a copy in DTJ's Bitwarden vault.
2. `python n8n/seo-engine/deploy_seo_engine.py --apply`.
   - It makes the n8n credential **JWT Auth "DTJ SEO Report Key"** from that key. That needs `N8N_API_KEY` on the laptop.
     Without it, make the credential in n8n by hand: Passphrase, HS256.
   - It also creates any missing table or workflow, copies the code and attaches the credentials.
3. `python n8n/store-factory/deploy_telegram_bot.py`: adds "SEO Answer" to the **draft** of the bot.
4. **Publish** both, after a yes:
   - `python n8n/seo-engine/deploy_seo_engine.py --publish`
   - `python n8n/store-factory/setup_n8n.py --publish --only "Store Factory: Telegram Bot"`
5. The GitHub side needs PR #2 (the SEO engine) and this branch on the default branch. The schedule runs only from there.
6. Optional: the repository variable `N8N_SEO_WEBHOOK_URL`, if n8n moves.
   The default is `https://n8n.srv2048145.hstgr.cloud/webhook/dtj-seo-weekly`.

## Files
| File | What it is |
|---|---|
| `notify_n8n.py` | The GitHub side: builds, signs and sends the report. It retries 429/5xx up to 3 times. Without the secret it sends nothing and the run still passes. |
| `check_report.js` | Signature claims, SHA-256 and schema |
| `plan_report.js` | Who gets the report; the batch row; the dead letter |
| `report_messages.js` | The file and the Yes / No message |
| `dead_letter_alert.js` | The admins' alert for a report that failed its checks |
| `answer_plan.js` | The answer rules |
| `answer_messages.js` | The replies and the action-log row |
| `build_workflow.py` | Writes `weekly_report.workflow.json` (the n8n export) from those files. `--check` is part of the tests. |
| `deploy_seo_engine.py` | Check, apply, publish and new key. It reuses `../store-factory/setup_n8n.py`. |
| `tables.json` | The three data tables' columns |
| `sample/` | The 14 Oct 2026 free run (trimmed) and the request built from it. The tests use these; the live key is never saved. |
| `test_seo_engine_n8n.py` | `python -m unittest discover -s n8n/seo-engine -t n8n/seo-engine` |
