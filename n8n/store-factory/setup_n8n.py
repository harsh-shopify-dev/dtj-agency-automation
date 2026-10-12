"""Check, and on request build, the n8n side of the store factory from this repo. Everything is found BY NAME, so the same command
works on DTJ's n8n today and on a brand-new n8n server (a fresh Claude Code session can set everything up with it).

    python n8n/store-factory/setup_n8n.py                 the check (read only, same as --check): a plain checklist, the ids it found
                                                          and the exact fix for each problem. Exit 0 = everything ready, 1 = not yet.
    python n8n/store-factory/setup_n8n.py --apply         make n8n match the repo: create a missing data table (tables.json) or workflow
                                                          (its *.workflow.json export), add missing columns, copy code nodes that
                                                          differ, attach missing credentials. Never deletes anything, never publishes.
    python n8n/store-factory/setup_n8n.py --publish       publish the workflows whose draft is not live yet, each one only after a fresh
                                                          check of it passes. Publishing changes what runs for real: only with the
                                                          person's go-ahead (Harsh's yes). --only "<workflow name>" narrows it to one.
    python n8n/store-factory/setup_n8n.py --save-tables   (read only) write tables.json from the live tables: column names and types.

What it checks: the data tables dtj_client_intake, dtj_stores and dtj_bot_users have the columns in tables.json; the workflows
"Store Factory: Page Design", "Store Factory: New Page" and "Store Factory: Telegram Bot" exist, are published, live = draft, every
code node equals the repo export, nodes / connections / links to the tables and workflows match the export, every node that needs a
credential has one; the credentials the exports use (Telegram API "DTJ Page Bot", Header Auth "DTJ Catcher Bot Key") exist.
A structural difference (a node or connection missing or extra) is reported, never changed here: the deploy_*.py scripts own that.
Secrets live only in n8n: this script never sees, prints or writes one, and it never reads table rows.
"""
from __future__ import annotations

import argparse
import http.client
import json
import re
import sys
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from n8n_mcp import N8N_HOST  # noqa: E402

HERE = Path(__file__).resolve().parent
TABLES_FILE = HERE / "tables.json"
TABLE_NAMES = ("dtj_client_intake", "dtj_stores", "dtj_bot_users")
# in creation order: each workflow only points at the tables and at the workflows above it
WORKFLOWS = {"Store Factory: Page Design": "page_design.workflow.json",
             "Store Factory: New Page": "new_page.workflow.json",
             "Store Factory: Telegram Bot": "telegram_bot.workflow.json"}
DEPLOY = {"Store Factory: Page Design": "deploy_page_design.py (then deploy_telegram_bot.py for Tell the Requester / Send Result)",
          "Store Factory: New Page": "deploy_new_page.py",
          "Store Factory: Telegram Bot": "deploy_telegram_bot.py"}
CREDENTIAL_LABELS = {"telegramApi": "Telegram API", "httpHeaderAuth": "Header Auth"}
NODE_SETTINGS = ("onError", "executeOnce", "alwaysOutputData", "retryOnFail", "maxTries", "waitBetweenTries")
NODE_FIELDS = {"name", "type", "typeVersion", "position", "parameters", "credentials", "notes", "disabled",
               "id", "webhookId"} | set(NODE_SETTINGS)  # id and webhookId are not copied: n8n gives each node its own
WORKFLOW_SETTINGS = ("executionOrder", "callerPolicy", "executionTimeout", "saveDataErrorExecution", "saveDataSuccessExecution",
                     "saveExecutionProgress", "saveManualExecutions", "timezone", "timeSavedPerExecution")
CHUNK = 100  # update_workflow takes at most 100 operations per call
# people paste a product link into this node by hand in n8n (TEAM-GUIDE Part C, the other way): never compared, never overwritten
EDITABLE = {"What to Design (edit me)"}
CODE_HEADER = re.compile(r'^// n8n Code node "([^"]+)" in "([^"]+)"')  # the first line of every code node's source file here
ERRORS = (urllib.error.URLError, http.client.HTTPException, RuntimeError, OSError, ValueError, KeyError)
SELF = "python n8n/store-factory/setup_n8n.py"


# ---- small helpers -----------------------------------------------------------------------------------------------------------

def redact(text, secrets=()) -> str:
    """An error message with anything token-like hidden (a Bearer value, a JWT, the token itself)."""
    text = re.sub(r"(?i)(bearer\s+)\S+", r"\1[hidden]", str(text))
    text = re.sub(r"eyJ[\w-]{8,}\.[\w-]{8,}\.[\w-]*", "[hidden]", text)
    for s in secrets:
        if s:
            text = text.replace(s, "[hidden]")
    return text


def _live_secrets() -> list[str]:
    try:
        from n8n_mcp import token
        return [token()]
    except Exception:  # noqa: BLE001 (no token, no registry: nothing to hide)
        return []


def load_exports() -> dict[str, dict]:
    return {name: json.loads((HERE / file).read_text(encoding="utf-8")) for name, file in WORKFLOWS.items()}


def load_spec(path: Path = TABLES_FILE) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def is_trigger(node: dict) -> bool:
    return node.get("type", "").split(".")[-1].lower().endswith("trigger")


def label(ctype: str) -> str:
    return CREDENTIAL_LABELS.get(ctype, ctype)


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def first_id(answer: dict) -> str | None:
    """The id in a create answer, whatever its shape ({id}, {workflowId}, {dataTable: {id}}, {data: {id}})."""
    for key in ("workflowId", "id"):
        if isinstance(answer.get(key), str):
            return answer[key]
    for key in ("dataTable", "data", "workflow"):
        inner = answer.get(key)
        if isinstance(inner, dict) and isinstance(inner.get("id"), str):
            return inner["id"]
    return None


# ---- reading n8n (read only) -------------------------------------------------------------------------------------------------

def find_tables(call, name: str) -> list[dict]:
    return [t for t in call("search_data_tables", {"query": name, "limit": 100}).get("data", []) if t.get("name") == name]


def find_workflows(call, name: str) -> list[dict]:
    found = call("search_workflows", {"query": name, "limit": 50}).get("data", [])
    return [w for w in found if w.get("name") == name and not w.get("isArchived")]


def find_credentials(call) -> list[dict]:
    return call("list_credentials", {"limit": 200}).get("data", [])


def credential_id(creds: list[dict], ctype: str, name: str) -> str | None:
    found = [c for c in creds if c.get("type") == ctype and c.get("name") == name]
    return found[0]["id"] if found else None


def find_project(call, tables: dict[str, list[dict]]) -> str:
    """The project for new tables and workflows: the one that already holds the store-factory workflows, else the one holding the
    tables, else the personal project."""
    projects = call("search_projects", {"limit": 100}).get("data", [])
    for p in projects:
        held = call("search_workflows", {"projectId": p["id"], "query": "Store Factory", "limit": 50}).get("data", [])
        if any(w.get("name") in WORKFLOWS for w in held):
            return p["id"]
    table_projects = {t.get("projectId") for found in tables.values() for t in found}
    for p in projects:
        if p["id"] in table_projects:
            return p["id"]
    for p in sorted(projects, key=lambda p: p.get("type") != "personal"):
        return p["id"]
    raise RuntimeError("no n8n project is visible to this token")


def survey(call, exports: dict, spec: dict) -> dict:
    """Read everything once: tables, credentials, workflows and their live details. ids = this server's id for each name."""
    tables = {name: find_tables(call, name) for name in (spec or dict.fromkeys(TABLE_NAMES))}
    creds = find_credentials(call)
    workflows = {name: find_workflows(call, name) for name in exports}
    ids = {name: found[0]["id"] for name, found in {**tables, **workflows}.items() if found}
    live = {name: call("get_workflow_details", {"workflowId": found[0]["id"]})["workflow"] for name, found in workflows.items() if found}
    return {"tables": tables, "creds": creds, "workflows": workflows, "ids": ids, "live": live}


# ---- comparing an export with the live workflow (no network) -----------------------------------------------------------------

def links(value, path: str = "") -> list[tuple[str, dict]]:
    """Every resource locator inside node parameters that names another n8n object: (JSON path, the locator)."""
    found: list[tuple[str, dict]] = []
    if isinstance(value, dict):
        if value.get("__rl") is True and value.get("cachedResultName"):
            found.append((path, value))
        for k, v in value.items():
            found += links(v, f"{path}/{k}")
    elif isinstance(value, list):
        for i, v in enumerate(value):
            found += links(v, f"{path}/{i}")
    return found


def remap(value, ids: dict[str, str]):
    """A copy of node parameters in which each locator naming one of our tables or workflows points at its id on THIS server."""
    if isinstance(value, list):
        return [remap(v, ids) for v in value]
    if not isinstance(value, dict):
        return value
    out = {k: remap(v, ids) for k, v in value.items()}
    target = out.get("cachedResultName")
    if out.get("__rl") is True and target in ids and ids[target]:
        old, out["value"] = out.get("value"), ids[target]
        if isinstance(out.get("cachedResultUrl"), str) and isinstance(old, str) and old:
            out["cachedResultUrl"] = out["cachedResultUrl"].replace(old, ids[target])
    return out


def connection_list(conns: dict | None) -> list[tuple]:
    """(source, kind, output index, target, input index) for every connection, in the export's order."""
    out = []
    for source, kinds in (conns or {}).items():
        for kind, outputs in (kinds or {}).items():
            for index, targets in enumerate(outputs or []):
                for t in targets or []:
                    out.append((source, kind, index, t.get("node"), t.get("index", 0)))
    return out


def publish_state(wf: dict) -> tuple[bool, bool]:
    """(published, live version == draft)."""
    published = bool(wf.get("activeVersionId")) or bool(wf.get("active"))
    av = wf.get("activeVersion")
    if isinstance(av, dict) and "sameAsDraft" in av:
        return published, published and bool(av["sameAsDraft"])
    return published, published and bool(wf.get("activeVersionId")) and wf.get("versionId") == wf.get("activeVersionId")


def compare(export: dict, live: dict, ids: dict[str, str], creds: list[dict]) -> dict:
    """What differs between the repo export and the live workflow (draft)."""
    want = {n["name"]: n for n in export.get("nodes", [])}
    have = {n["name"]: n for n in live.get("nodes", [])}
    cred_names = {c["id"]: c.get("name") for c in creds}
    diff: dict = {"missing_nodes": [n for n in want if n not in have], "extra_nodes": [n for n in have if n not in want],
                  "changed_type": [], "code": [], "code_nodes": 0, "credentials": [], "credential_nodes": 0, "links": []}
    for name, node in want.items():
        if "jsCode" in node.get("parameters", {}):
            diff["code_nodes"] += 1
        if node.get("credentials"):
            diff["credential_nodes"] += 1
        got = have.get(name)
        if got is None:
            continue
        if (got.get("type"), got.get("typeVersion")) != (node.get("type"), node.get("typeVersion")):
            diff["changed_type"].append(name)
        if ("jsCode" in node.get("parameters", {}) and name not in EDITABLE
                and got.get("parameters", {}).get("jsCode") != node["parameters"]["jsCode"]):
            diff["code"].append(name)
        for key, c in (node.get("credentials") or {}).items():
            on = (got.get("credentials") or {}).get(key) or {}
            if not on.get("id"):
                diff["credentials"].append((name, key, c.get("name"), "none attached"))
            elif on["id"] not in cred_names:
                diff["credentials"].append((name, key, c.get("name"), "it points at a credential this server does not have"))
            elif cred_names[on["id"]] != c.get("name"):
                diff["credentials"].append((name, key, c.get("name"), f"'{cred_names[on['id']]}' is attached instead"))
        live_links = dict(links(got.get("parameters", {})))
        for path, rl in links(node.get("parameters", {})):
            target = rl.get("cachedResultName")
            if target in ids and (live_links.get(path) or {}).get("value") != ids[target]:
                diff["links"].append((name, target, (live_links.get(path) or {}).get("value"), ids[target]))
    w, h = connection_list(export.get("connections")), connection_list(live.get("connections"))
    diff["missing_connections"] = [c for c in w if c not in set(h)]
    diff["extra_connections"] = [c for c in h if c not in set(w)]
    return diff


def structure_problems(diff: dict) -> list[str]:
    def wire(c):
        return f"{c[0]} (output {c[2]}) -> {c[3]}" + (f" [{c[1]}]" if c[1] != "main" else "")
    out = []
    if diff["missing_nodes"]:
        out.append("nodes missing on n8n: " + ", ".join(diff["missing_nodes"]))
    if diff["extra_nodes"]:
        out.append("nodes on n8n that the export does not have: " + ", ".join(diff["extra_nodes"]))
    if diff["changed_type"]:
        out.append("node type or version differs: " + ", ".join(diff["changed_type"]))
    if diff["missing_connections"]:
        out.append("connections missing on n8n: " + "; ".join(wire(c) for c in diff["missing_connections"]))
    if diff["extra_connections"]:
        out.append("connections on n8n that the export does not have: " + "; ".join(wire(c) for c in diff["extra_connections"]))
    for node, target, got, expected in diff["links"]:
        out.append(f"{node} points at {target} id {got}, but this server's {target} is {expected}")
    return out


def blockers(diff: dict) -> list[str]:
    """Everything that stops a workflow from being ready (publishing aside)."""
    out = []
    if diff["code"]:
        out.append("code differs from the repo in: " + ", ".join(diff["code"]))
    for node, key, name, why in diff["credentials"]:
        out.append(f"{node} needs the {label(key)} credential '{name}': {why}")
    return out + structure_problems(diff)


# ---- the checklist ---------------------------------------------------------------------------------------------------------------

class Sheet:
    def __init__(self, out=print):
        self.out, self.problems = out, 0

    def head(self, text: str):
        self.out("")
        self.out(text)

    def ok(self, text: str):
        self.out(f"  [ok] {text}")

    def bad(self, text: str, fix: str):
        self.problems += 1
        self.out(f"  [!!] {text}")
        self.out(f"       fix: {fix}")

    def note(self, text: str):
        self.out(f"  [..] {text}")


def needed_credentials(exports: dict) -> dict[tuple[str, str], list[str]]:
    need: dict[tuple[str, str], list[str]] = {}
    for wf in exports.values():
        for node in wf.get("nodes", []):
            for key, c in (node.get("credentials") or {}).items():
                need.setdefault((key, c.get("name")), []).append(f"{wf['name']} / {node['name']}")
    return need


def code_files(folder: Path = HERE) -> dict[tuple[str, str], tuple[str, str]]:
    """The code nodes' source files in git: (workflow, node) -> (file name, code), found by each file's first line."""
    found = {}
    for f in sorted(folder.glob("*.js")):
        text = f.read_text(encoding="utf-8")
        m = CODE_HEADER.match(text)
        if m:
            found[(m.group(2), m.group(1))] = (f.name, text)
    return found


def stale_files(exports: dict, files: dict) -> list[str]:
    """Source files whose code is not what the export holds: edited in git, not deployed yet (the export is saved by deploy_*.py)."""
    stale = []
    for (wf, node), (fname, text) in sorted(files.items()):
        if wf not in exports or node in EDITABLE:
            continue
        n = next((x for x in exports[wf].get("nodes", []) if x.get("name") == node), None)
        if n is None:
            stale.append(f"{fname} (no node '{node}' in {WORKFLOWS.get(wf, wf)})")
        elif (n.get("parameters") or {}).get("jsCode") != text:
            stale.append(f"{fname} ({node})")
    return stale


def check(call, out=print, exports: dict | None = None, spec: dict | None = None, files: dict | None = None) -> int:
    """Read only. Prints the checklist; returns the number of problems."""
    if files is None:
        files = code_files() if exports is None else {}
    exports = exports if exports is not None else load_exports()
    spec = spec if spec is not None else load_spec()
    s = survey(call, exports, spec)
    sheet = Sheet(out)
    out(f"Store factory on n8n ({N8N_HOST}): read-only check")

    sheet.head("Data tables")
    if not spec:
        sheet.bad("tables.json is missing or empty, so the columns cannot be checked", f"{SELF} --save-tables (on a server that has them)")
    for name, want in spec.items():
        found = s["tables"].get(name) or []
        if not found:
            sheet.bad(f"{name}: not on this n8n server", f"{SELF} --apply (creates it with the columns in tables.json)")
            continue
        t = found[0]
        have = {c["name"]: c.get("type") for c in t.get("columns", [])}
        missing = [c["name"] for c in want["columns"] if c["name"] not in have]
        wrong = [f"{c['name']} is {have[c['name']]}, not {c['type']}" for c in want["columns"]
                 if c["name"] in have and have[c["name"]] != c["type"]]
        extra = [n for n in have if n not in {c["name"] for c in want["columns"]}]
        if len(found) > 1:
            sheet.note(f"{len(found)} tables are named {name} (ids {', '.join(x['id'] for x in found)}): using {t['id']}")
        if missing:
            sheet.bad(f"{name} (id {t['id']}): columns missing: {', '.join(missing)}", f"{SELF} --apply (adds them; nothing is removed)")
        if wrong:
            sheet.bad(f"{name} (id {t['id']}): column type differs: {'; '.join(wrong)}",
                      "ask Harsh: a column type cannot be changed without dropping its data, and this tool never does that")
        if not missing and not wrong:
            sheet.ok(f"{name} (id {t['id']}): all {len(want['columns'])} columns" + (f" (+ {len(extra)} more on n8n)" if extra else ""))

    sheet.head("Credentials (the secrets stay in n8n; only names and ids are read)")
    for (ctype, name), users in needed_credentials(exports).items():
        found = [c for c in s["creds"] if c.get("type") == ctype and c.get("name") == name]
        if found:
            sheet.ok(f"{name} ({label(ctype)}, id {found[0]['id']}), used by {len(users)} node(s)")
        else:
            sheet.bad(f"{name} ({label(ctype)}): not on this n8n server; needed by {', '.join(users)}",
                      f"in n8n: Credentials > Create credential > {label(ctype)}, named exactly '{name}'; the person who owns the secret "
                      f"pastes it there (never in git or chat). Then {SELF} --apply attaches it.")

    sheet.head("Workflows")
    for name, export in exports.items():
        found = s["workflows"].get(name) or []
        if not found:
            sheet.bad(f"{name}: not on this n8n server", f"{SELF} --apply (builds it from {WORKFLOWS[name]}, unpublished)")
            continue
        if len(found) > 1:
            sheet.bad(f"{name}: {len(found)} workflows have this exact name (ids {', '.join(w['id'] for w in found)})",
                      "keep one: rename or archive the extra one in n8n yourself (this tool never deletes)")
        live = s["live"][name]
        wf_id = found[0]["id"]
        published, same = publish_state(live)
        diff = compare(export, live, s["ids"], s["creds"])
        if not published:
            sheet.bad(f"{name} (id {wf_id}): not published",
                      f"when the checks below pass and Harsh says yes: {SELF} --publish --only \"{name}\"")
        elif not same:
            sheet.bad(f"{name} (id {wf_id}): published, but the draft has changes that are not live yet",
                      f"when the checks below pass and Harsh says yes: {SELF} --publish --only \"{name}\"")
        else:
            sheet.ok(f"{name} (id {wf_id}): published, live version = draft")
        if diff["code"]:
            sheet.bad(f"{name}: code differs from the repo in: {', '.join(diff['code'])}",
                      f"{SELF} --apply (copies the code from {WORKFLOWS[name]}), then publish")
        else:
            sheet.ok(f"{name}: all {diff['code_nodes']} code nodes match the repo")
        if diff["credentials"]:
            for node, key, cname, why in diff["credentials"]:
                fix = (f"{SELF} --apply (attaches '{cname}' by name)" if credential_id(s["creds"], key, cname)
                       else f"create the {label(key)} credential '{cname}' in n8n first (see Credentials above), then {SELF} --apply")
                if why.endswith("instead"):
                    fix = f"open {node} in n8n and pick the credential '{cname}' (this tool does not swap a credential someone chose)"
                sheet.bad(f"{name} / {node}: needs the {label(key)} credential '{cname}': {why}", fix)
        elif diff["credential_nodes"]:
            sheet.ok(f"{name}: the {diff['credential_nodes']} node(s) that need a credential have one")
        else:
            sheet.ok(f"{name}: no node needs a credential")
        problems = structure_problems(diff)
        if problems:
            sheet.bad(f"{name}: differs from {WORKFLOWS[name]}: " + " | ".join(problems),
                      f"python n8n/store-factory/{DEPLOY[name]}; if n8n holds the newer version, re-export it instead")
        else:
            sheet.ok(f"{name}: nodes, connections and links to tables/workflows match the export")

    if files:
        sheet.head("Code files in git (n8n/store-factory/*.js)")
        stale = stale_files(exports, files)
        if stale:
            sheet.bad("edited in git but not deployed to n8n yet: " + ", ".join(stale),
                      "run the matching deploy_*.py (it copies the files into n8n and saves the export), then publish with Harsh's yes")
        else:
            sheet.ok(f"all {len(files)} code files match the exports")
    out("")
    if sheet.problems:
        out(f"NOT READY: {sheet.problems} problem(s). Fix them in the order above, then run this check again.")
    else:
        out("READY: n8n matches the repo.")
    return sheet.problems


# ---- building (only with --apply) ----------------------------------------------------------------------------------------------

def trigger_code(export: dict, ids: dict[str, str]) -> str:
    """Workflow SDK code with ONLY the trigger node(s) of an export (type, version, name, position, parameters)."""
    def key(k: str) -> str:
        return k if re.fullmatch(r"[A-Za-z_$][\w$]*", k) else json.dumps(k)

    lines, names = ["import { workflow, trigger, newCredential } from '@n8n/workflow-sdk';", ""], []
    for i, node in enumerate(n for n in export["nodes"] if is_trigger(n)):
        creds = node.get("credentials") or {}
        keys = ", ".join(f"{key(k)}: newCredential({json.dumps(c.get('name') or k)})" for k, c in creds.items())
        lines.append(f"const trigger{i} = trigger({{ type: {json.dumps(node['type'])}, version: {json.dumps(node['typeVersion'])}, "
                     f"config: {{ name: {json.dumps(node['name'], ensure_ascii=False)}, position: {json.dumps(node.get('position', [0, 0]))}, "
                     f"parameters: {json.dumps(remap(node.get('parameters', {}), ids), ensure_ascii=False)}"
                     + (f", credentials: {{ {keys} }}" if keys else "") + " } });")
        names.append(f"trigger{i}")
    if not names:
        raise ValueError(f"{export['name']}: the export has no trigger node")
    chain = "".join(f"\n  .add({v})" for v in names)
    lines += ["", f"export default workflow({json.dumps(slug(export['name']))}, {json.dumps(export['name'], ensure_ascii=False)}){chain};"]
    return "\n".join(lines) + "\n"


def build_ops(export: dict, ids: dict[str, str], creds: list[dict], skip: set[str]) -> tuple[list[dict], list[str], int]:
    """update_workflow operations that rebuild an export on top of its trigger(s). skip = nodes already there (the triggers).
    Returns (operations, warnings, how many credentials could not be attached)."""
    adds, settings, wires, keys, warnings, missing = [], [], [], [], [], 0
    for node in export["nodes"]:
        name = node["name"]
        if name not in skip:
            new = {"name": name, "type": node["type"], "typeVersion": node["typeVersion"], "position": node.get("position", [0, 0]),
                   "parameters": remap(node.get("parameters", {}), ids)}
            for k in ("notes", "disabled"):
                if k in node:
                    new[k] = node[k]
            adds.append({"type": "addNode", "node": new})
        chosen = {k: node[k] for k in NODE_SETTINGS if k in node}
        if chosen:
            settings.append({"type": "setNodeSettings", "nodeName": name, "settings": chosen})
        unknown = sorted(set(node) - NODE_FIELDS)
        if unknown:
            warnings.append(f"{name}: not copied: {', '.join(unknown)}")
        for key, c in (node.get("credentials") or {}).items():
            cid = credential_id(creds, key, c.get("name"))
            if cid:
                keys.append({"type": "setNodeCredential", "nodeName": name, "credentialKey": key, "credentialId": cid,
                             "credentialName": c.get("name")})
            else:
                missing += 1
                warnings.append(f"{name}: no {label(key)} credential named '{c.get('name')}' on this server, so none is attached "
                                f"(create it in n8n, then run --apply again)")
    for source, kind, index, target, tindex in connection_list(export.get("connections")):
        op = {"type": "addConnection", "source": source, "target": target, "sourceIndex": index, "targetIndex": tindex}
        if kind != "main":
            op["connectionType"] = kind
        wires.append(op)
    return adds + settings + wires + keys, warnings, missing


def settings_ops(export: dict, warnings: list[str]) -> list[dict]:
    given = export.get("settings") or {}
    chosen = {k: v for k, v in given.items() if k in WORKFLOW_SETTINGS}
    left = [k for k in given if k not in WORKFLOW_SETTINGS]
    if left:
        warnings.append(f"workflow settings not set through n8n's MCP: {', '.join(left)} (check them in the workflow's Settings; "
                        "'Available in MCP' must be on for this tool and listen.py to see it)")
    return [{"type": "setWorkflowSettings", "settings": chosen}] if chosen else []


def chunks(ops: list[dict], size: int = CHUNK) -> list[list[dict]]:
    return [ops[i:i + size] for i in range(0, len(ops), size)]


def send_ops(call, wf_id: str, ops: list[dict], why: str) -> int:
    parts = chunks(ops)
    for i, part in enumerate(parts, 1):
        call("update_workflow", {"workflowId": wf_id, "operations": part, "versionName": f"setup_n8n.py: {why} ({i}/{len(parts)})"[:80]})
    return len(parts)


def create_workflow(call, export: dict, ids: dict[str, str], creds: list[dict], project: str, out=print) -> tuple[str, int]:
    """Build a missing workflow from its export (unpublished). Returns (its id, credentials that could not be attached)."""
    code = trigger_code(export, ids)
    verdict = call("validate_workflow", {"code": code})
    if verdict.get("valid") is False or verdict.get("errors"):
        raise RuntimeError(f"n8n refused the trigger code for {export['name']}: {json.dumps(verdict)[:600]}")
    made = call("create_workflow_from_code", {"code": code, "name": export["name"], "description": (export.get("description") or "")[:255],
                                              "projectId": project, "versionName": "setup_n8n.py: trigger from the repo export"})
    wf_id = first_id(made) or next((w["id"] for w in find_workflows(call, export["name"])), None)
    if not wf_id:
        raise RuntimeError(f"{export['name']} was sent to n8n but cannot be found afterwards: {json.dumps(made)[:300]}")
    ops, warnings, missing = build_ops(export, ids, creds, skip={n["name"] for n in export["nodes"] if is_trigger(n)})
    ops += settings_ops(export, warnings)
    try:
        calls = send_ops(call, wf_id, ops, "build from the repo export")
    except ERRORS as exc:
        raise RuntimeError(f"{export['name']} (id {wf_id}) was created but not finished: {exc}. Nothing was deleted; finish it with "
                           f"python n8n/store-factory/{DEPLOY[export['name']]} or remove it in n8n yourself and run --apply again") from exc
    for w in warnings:
        out(f"  warning: {w}")
    out(f"  created {export['name']}: id {wf_id} in project {project}, {len(export['nodes'])} nodes, "
        f"{len(connection_list(export.get('connections')))} connections, {len(ops)} operations in {calls} call(s); not published")
    return wf_id, missing


def sync_workflow(call, name: str, export: dict, live: dict, ids: dict[str, str], creds: list[dict], out=print) -> int:
    """Copy code nodes that differ and attach missing credentials; report everything else. Returns the problems left."""
    diff = compare(export, live, ids, creds)
    want = {n["name"]: n for n in export["nodes"]}
    ops = [{"type": "updateNodeParameters", "nodeName": n, "parameters": {"jsCode": want[n]["parameters"]["jsCode"]}} for n in diff["code"]]
    left = 0
    for node, key, cname, why in diff["credentials"]:
        cid = credential_id(creds, key, cname)
        if cid and (why == "none attached" or why.startswith("it points at")):
            ops.append({"type": "setNodeCredential", "nodeName": node, "credentialKey": key, "credentialId": cid, "credentialName": cname})
        elif not cid:
            left += 1
            out(f"  {name} / {node}: no {label(key)} credential named '{cname}' on this server: create it in n8n, then run --apply again")
        else:
            left += 1
            out(f"  {name} / {node}: {why}; not changed (pick '{cname}' in n8n if that is wrong)")
    if ops:
        send_ops(call, live["id"], ops, "code and credentials from the repo")
        synced = ", ".join(op["nodeName"] for op in ops if op["type"] == "updateNodeParameters") or "none"
        attached = ", ".join(op["nodeName"] for op in ops if op["type"] == "setNodeCredential") or "none"
        out(f"  {name}: code copied to: {synced}; credentials attached to: {attached}")
    else:
        out(f"  {name}: code and credentials already match the repo")
    problems = structure_problems(diff)
    if problems:
        left += 1
        out(f"  {name}: NOT changed (structure): " + " | ".join(problems))
        out(f"       advice: run python n8n/store-factory/{DEPLOY[name]}")
    return left


def apply(call, out=print, exports: dict | None = None, spec: dict | None = None) -> int:
    """Make n8n match the repo without deleting or publishing anything. Returns the problems left."""
    exports = exports if exports is not None else load_exports()
    spec = spec if spec is not None else load_spec()
    if not spec:
        out(f"tables.json is missing: run {SELF} --save-tables on a server that has the tables first")
        return 1
    s = survey(call, exports, spec)
    ids, left, project = dict(s["ids"]), 0, None

    def project_id() -> str:
        nonlocal project
        if project is None:
            project = find_project(call, s["tables"])
        return project

    out(f"Store factory on n8n ({N8N_HOST}): apply (never deletes, never publishes)")
    out("Data tables")
    for name, want in spec.items():
        found = s["tables"].get(name) or []
        if not found:
            made = call("create_data_table", {"projectId": project_id(), "name": name, "columns": want["columns"]})
            ids[name] = first_id(made) or next((t["id"] for t in find_tables(call, name)), None)
            if not ids[name]:
                raise RuntimeError(f"data table {name} was sent to n8n but cannot be found afterwards")
            out(f"  created {name}: id {ids[name]} in project {project_id()}, {len(want['columns'])} columns")
            continue
        t = found[0]
        have = {c["name"]: c.get("type") for c in t.get("columns", [])}
        for col in want["columns"]:
            if col["name"] not in have:
                call("add_data_table_column", {"dataTableId": t["id"], "projectId": t.get("projectId") or project_id(),
                                               "name": col["name"], "type": col["type"]})
                out(f"  {name}: added column {col['name']} ({col['type']})")
            elif have[col["name"]] != col["type"]:
                left += 1
                out(f"  {name}: column {col['name']} is {have[col['name']]}, not {col['type']}: not changed (ask Harsh)")
        out(f"  {name} (id {t['id']}): columns in place")

    out("Workflows")
    creds = s["creds"]
    for name, export in exports.items():  # in creation order, so each one can point at those before it
        if name not in s["live"]:
            ids[name], missing = create_workflow(call, export, ids, creds, project_id(), out)
            left += missing
    for name, live in s["live"].items():
        left += sync_workflow(call, name, exports[name], live, ids, creds, out)

    need = []
    for name in exports:
        published, same = publish_state(call("get_workflow_details", {"workflowId": ids[name]})["workflow"])
        if not (published and same):
            need.append(f"{name} (id {ids[name]}, {'draft ahead of live' if published else 'not published'})")
    out("")
    if need:
        out("Needs publishing (its draft is not live yet): " + "; ".join(need))
        out(f"Publishing changes what runs for real: only with Harsh's go-ahead, run {SELF} --publish --only \"<workflow name>\"")
    else:
        out("Nothing to publish: every workflow's live version equals its draft.")
    out(f"Done. Problems left: {left}." + (f" Run {SELF} for the full checklist." if left else ""))
    return left


def publish(call, out=print, exports: dict | None = None, spec: dict | None = None, only: str | None = None) -> int:
    """Publish each workflow whose draft is not live, only after a fresh check of it passes. Needs the person's go-ahead."""
    exports = exports if exports is not None else load_exports()
    spec = spec if spec is not None else load_spec()
    s = survey(call, exports, spec)  # read fresh, right before deciding
    left = 0
    for name, export in exports.items():
        if only and name != only:
            continue
        live = s["live"].get(name)
        if live is None:
            left += 1
            out(f"not published: {name} is not on this n8n server ({SELF} --apply builds it)")
            continue
        published, same = publish_state(live)
        if published and same:
            out(f"{name} (id {live['id']}): live version already equals the draft; nothing to publish")
            continue
        stop = blockers(compare(export, live, s["ids"], s["creds"]))
        if stop:
            left += 1
            out(f"NOT published: {name} (id {live['id']}): the fresh check found: " + " | ".join(stop))
            continue
        call("publish_workflow", {"workflowId": live["id"]})
        after = publish_state(call("get_workflow_details", {"workflowId": live["id"]})["workflow"])
        out(f"published {name} (id {live['id']}): published {after[0]}, live = draft {after[1]}")
        left += 0 if all(after) else 1
    return left


def tables_json(spec: dict) -> str:
    """tables.json with one column per line (plain JSON, easy to read in a diff)."""
    parts = []
    for name, table in spec.items():
        cols = ",\n".join(f"  {json.dumps(c, ensure_ascii=False)}" for c in table["columns"])
        parts.append(f" {json.dumps(name)}: {{\"columns\": [\n{cols}\n ]}}")
    return "{\n" + ",\n".join(parts) + "\n}\n"


def save_tables(call, path: Path = TABLES_FILE, out=print) -> int:
    """Read only against n8n: write the column names and types of our tables (never a row)."""
    spec, missing = {}, []
    for name in TABLE_NAMES:
        found = find_tables(call, name)
        if not found:
            missing.append(name)
            continue
        cols = sorted(found[0].get("columns", []), key=lambda c: c.get("index", 0))
        spec[name] = {"columns": [{"name": c["name"], "type": c["type"]} for c in cols]}
    if missing:
        out(f"not written: these tables are not on this n8n server: {', '.join(missing)}")
        return 1
    path.write_text(tables_json(spec), encoding="utf-8")
    out(f"wrote {path.name}: " + ", ".join(f"{n} ({len(v['columns'])} columns)" for n, v in spec.items()))
    return 0


def main(argv=None, call=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="read only (the default)")
    mode.add_argument("--apply", action="store_true", help="create what is missing, copy code, attach credentials; never deletes/publishes")
    mode.add_argument("--save-tables", action="store_true", help="read only: write tables.json (column names and types)")
    ap.add_argument("--publish", action="store_true", help="publish after a fresh check passes (needs Harsh's go-ahead); alone or after --apply")
    ap.add_argument("--only", choices=list(WORKFLOWS), help="with --publish: just this workflow")
    args = ap.parse_args(argv)
    if args.publish and (args.check or args.save_tables):
        ap.error("--publish goes alone or with --apply")
    if args.only and not args.publish:
        ap.error("--only goes with --publish")
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    secrets = None
    if call is None:
        from n8n_mcp import call  # the real server (the token is read inside, never printed)
        secrets = _live_secrets
    try:
        if args.save_tables:
            return save_tables(call)
        if args.apply or args.publish:
            left = apply(call) if args.apply else 0
            if args.publish:
                print("")
                left += publish(call, only=args.only)
            return 1 if left else 0
        return 1 if check(call) else 0
    except ERRORS as exc:
        print(f"stopped: n8n could not be read or refused: {redact(exc, secrets() if secrets else ())}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
