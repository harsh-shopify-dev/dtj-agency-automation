"""Deploy "Store Factory: New Store" to DTJ's n8n: an admin's store link in Telegram becomes one Claude Code hand-off on a DTJ laptop
(Harsh, 21 Oct 2026: "i just share the brand store link and it starts designing the store and it asks the specific questions it needs
along with the app installation").

    python n8n/store-factory/deploy_new_store.py --dry-run     print the generated workflow code, change nothing
    python n8n/store-factory/deploy_new_store.py               create it (or refresh its code nodes when it exists)

From the Telegram Bot (link, note, requested_by, chat_id) -> Request for Claude Code: New Store -> Wait for Claude Code: New Store
(7 days: the store owner's installs can take days) -> Claude Code Reply: New Store -> Tell the Requester -> Send Result.
The laptop's Claude Code follows the skill dtj-new-store (store_job.py asks the questions and the Approve taps in Telegram; the answers
come back through the bot's "Save the Answer" into dtj_bot_answers). Same shape and checks as deploy_add_shop.py; created UNPUBLISHED;
the export is new_store.workflow.json.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from deploy_add_shop import deploy, handoff_code  # noqa: E402

NEW_STORE = {
    "name": "Store Factory: New Store", "slug": "store-factory-new-store", "step": "New Store", "days": 7,
    "inputs": ["link", "note", "requested_by", "chat_id"],
    "code": {"request": "new_store_request.js", "reply": "new_store_reply.js", "tell": "new_store_notify.js"},
    "export": "new_store.workflow.json", "version": "A whole store from one link",
    "description": ("Store factory: an admin's store link from the Telegram bot; Claude Code on a DTJ laptop asks the questions in "
                    "Telegram, makes the draft copy and the DTJ apps, and designs each part chosen into the draft (Approve taps)."),
    "sticky": ("## A whole store from one link\n"
               "Started by the Telegram bot when an admin sends a store's own link (no /products/ in it).\n\n"
               "The run pauses at **Wait for Claude Code: New Store** (up to 7 days). A Claude Code session in the dtj-agency-automation "
               "folder (listening, or told \"handle the Claude Code trigger in n8n\") follows the skill dtj-new-store: store_job.py asks "
               "the questions and the Approve taps in Telegram, then the draft copy, the apps, the brand data and every page. Nothing is "
               "published; the live theme is never written.\n\n"
               "Source in git: `n8n/store-factory/` (store_job.py, bot_ask.py) and `.claude/skills/dtj-new-store`."),
}


def sdk_code() -> str:
    return handoff_code(NEW_STORE)


def main(argv=None) -> int:
    return deploy(NEW_STORE, argv)


if __name__ == "__main__":
    raise SystemExit(main())
