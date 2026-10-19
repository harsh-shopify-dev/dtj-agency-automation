"""Put "SEO Engine: Weekly Report" and its data tables on DTJ's n8n, the same way setup_n8n.py builds the store factory.

    python n8n/seo-engine/deploy_seo_engine.py               the check (read only): tables, credentials, workflow vs the repo export
    python n8n/seo-engine/deploy_seo_engine.py --apply       create what is missing (tables dtj_seo_batches, dtj_dead_letter,
                                                              dtj_action_log; the workflow, unpublished), copy code nodes that differ,
                                                              attach credentials, point the bot's "SEO Answer" at the workflow.
                                                              Never deletes, never publishes.
    python n8n/seo-engine/deploy_seo_engine.py --publish     publish it (the webhook goes live and the answer lane can be called).
                                                              Only with Harsh's yes (or a named teammate's when he can't be reached).
    python n8n/seo-engine/deploy_seo_engine.py --new-key     make the shared signing key once: saved as this laptop's Windows user
                                                              variable DTJ_SEO_REPORT_KEY and as the GitHub secret N8N_SEO_REPORT_KEY
                                                              (through gh). Never printed. Then --apply makes the n8n credential.
Order on a new server: --new-key (once), --apply, then python n8n/store-factory/deploy_telegram_bot.py (adds "SEO Answer" to the bot),
then, with the yes, --publish here and the bot's publish (setup_n8n.py --publish --only "Store Factory: Telegram Bot").
Credentials it needs on n8n: JWT Auth "DTJ SEO Report Key" (passphrase = DTJ_SEO_REPORT_KEY, HS256; --apply creates it when this
laptop has N8N_API_KEY and DTJ_SEO_REPORT_KEY), Telegram API "DTJ Page Bot" and Bearer Auth "DTJ GitHub Actions" (both exist already).
"""
from __future__ import annotations

import argparse
import json
import secrets
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FACTORY = HERE.parent / "store-factory"
sys.path.insert(0, str(FACTORY))
import setup_n8n as setup  # noqa: E402

NAME = "SEO Engine: Weekly Report"
EXPORT = HERE / "weekly_report.workflow.json"
BOT = "Store Factory: Telegram Bot"
KEY_VAR = "DTJ_SEO_REPORT_KEY"
GITHUB_SECRET = "N8N_SEO_REPORT_KEY"
REPO = "harsh-shopify-dev/dtj-agency-automation"
SELF = "python n8n/seo-engine/deploy_seo_engine.py"

# what setup_n8n.py needs to know about this workflow (its helpers are shared, its own lists stay as they are)
setup.CREDENTIAL_LABELS.setdefault("jwtAuth", "JWT Auth")
setup.CREDENTIAL_RECIPES[("jwtAuth", "DTJ SEO Report Key")] = {"keyType": "passphrase", "secret": f"${KEY_VAR}", "algorithm": "HS256"}
setup.DEPLOY.setdefault(NAME, f"../seo-engine/deploy_seo_engine.py --apply (from {SELF})")


def exports() -> dict:
    return {NAME: json.loads(EXPORT.read_text(encoding="utf-8"))}


def spec() -> dict:
    """The new tables plus dtj_bot_users (already there; listed so the workflow's links to it are re-pointed by name)."""
    mine = json.loads((HERE / "tables.json").read_text(encoding="utf-8"))
    factory = json.loads((FACTORY / "tables.json").read_text(encoding="utf-8"))
    return {"dtj_bot_users": factory["dtj_bot_users"], **mine}


def point_the_bot(call, out=print) -> int:
    """The bot's "SEO Answer" must call this workflow by its id on this server. Returns problems left."""
    seo = setup.find_workflows(call, NAME)
    bots = setup.find_workflows(call, BOT)
    if not seo or not bots:
        out(f"  bot link: {'the SEO workflow' if not seo else 'the bot'} is not on this server yet")
        return 1
    bot = call("get_workflow_details", {"workflowId": bots[0]["id"]})["workflow"]
    node = next((n for n in bot["nodes"] if n["name"] == "SEO Answer"), None)
    if node is None:
        out("  bot link: the bot has no \"SEO Answer\" yet: run python n8n/store-factory/deploy_telegram_bot.py")
        return 1
    wf = node["parameters"].get("workflowId") or {}
    if wf.get("value") == seo[0]["id"]:
        out(f"  bot link: \"SEO Answer\" already calls {NAME} (id {seo[0]['id']})")
        return 0
    params = dict(node["parameters"], workflowId={"__rl": True, "mode": "list", "value": seo[0]["id"], "cachedResultName": NAME})
    call("update_workflow", {"workflowId": bots[0]["id"], "versionName": "SEO Answer -> SEO Engine: Weekly Report",
                             "operations": [{"type": "updateNodeParameters", "nodeName": "SEO Answer", "parameters": params}]})
    out(f"  bot link: \"SEO Answer\" now calls {NAME} (id {seo[0]['id']}); the bot's draft changed, publish it with the yes")
    return 0


def check(call, out=print) -> int:
    ex, sp = exports(), spec()
    s = setup.survey(call, ex, sp)
    left = 0
    for name in sp:
        found = s["tables"].get(name) or []
        out(f"  table {name}: {'id ' + found[0]['id'] if found else 'MISSING (--apply creates it)'}")
        left += 0 if found else 1
    for (ctype, cname), users in setup.needed_credentials(ex).items():
        have = setup.credential_id(s["creds"], ctype, cname)
        out(f"  credential {cname} ({setup.label(ctype)}): {'on n8n' if have else 'MISSING: ' + setup.by_hand(ctype, cname)}")
        left += 0 if have else 1
    live = s["live"].get(NAME)
    if live is None:
        out(f"  workflow {NAME}: MISSING (--apply creates it, unpublished)")
        return left + 1
    diff = setup.compare(ex[NAME], live, s["ids"], s["creds"])
    problems = setup.structure_problems(diff) + [f"code differs: {', '.join(diff['code'])}"] * bool(diff["code"])
    published, same = setup.publish_state(live)
    out(f"  workflow {NAME} (id {live['id']}): {'; '.join(problems) or 'matches the repo export'}; "
        f"{'published' if published else 'NOT published'}{'' if same or not published else ', draft ahead of live'}")
    return left + len(problems) + (0 if published and same else 1)


def new_key(out=print) -> int:
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_READ | winreg.KEY_SET_VALUE) as k:
        try:
            if str(winreg.QueryValueEx(k, KEY_VAR)[0]).strip():
                out(f"{KEY_VAR} is already set on this laptop: not replaced (replacing it means updating GitHub and n8n together).")
                return 1
        except FileNotFoundError:
            pass
        key = secrets.token_urlsafe(48)
        winreg.SetValueEx(k, KEY_VAR, 0, winreg.REG_SZ, key)
    p = subprocess.run(["gh", "secret", "set", GITHUB_SECRET, "--repo", REPO], input=key, text=True, capture_output=True)
    if p.returncode != 0:
        out(f"Saved {KEY_VAR} on this laptop, but GitHub refused the secret (gh exit {p.returncode}). Set {GITHUB_SECRET} by hand.")
        return 1
    out(f"Made the signing key: Windows user variable {KEY_VAR} and GitHub secret {GITHUB_SECRET} (same value, not shown). "
        f"Also keep it in DTJ's Bitwarden vault. Next: {SELF} --apply (creates the n8n credential from it).")
    return 0


def main(argv=None, call=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--apply", action="store_true")
    g.add_argument("--publish", action="store_true")
    g.add_argument("--new-key", action="store_true")
    a = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if a.new_key:
        return new_key()
    if call is None:
        from n8n_mcp import call  # the token is read inside, never printed
    try:
        if a.apply:
            left = setup.apply(call, exports=exports(), spec=spec(), seed=[])
            left += point_the_bot(call)
        elif a.publish:
            left = setup.publish(call, exports=exports(), spec=spec(), only=NAME)
        else:
            print(f"{NAME} on n8n ({setup.N8N_HOST}): check (read only)")
            left = check(call)
    except setup.ERRORS as exc:
        print(f"stopped: {setup.redact(str(exc))[:600]}", file=sys.stderr)
        return 1
    print(f"Problems left: {left}.")
    return 0 if not left else 1


if __name__ == "__main__":
    raise SystemExit(main())
