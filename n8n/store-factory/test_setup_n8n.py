"""setup_n8n.py against a fake n8n kept in memory (no network): the check, --apply, --publish and --save-tables.

    python -m unittest discover -s n8n/store-factory -p "test_*.py"
"""
import copy
import io
import json
import re
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import setup_n8n as setup

READS = {"search_workflows", "get_workflow_details", "search_data_tables", "get_data_table_rows", "search_projects", "list_credentials",
         "get_workflow_sdk_reference", "get_node_types", "search_nodes", "search_workflow_executions", "get_workflow_execution"}


def _node(name, ntype, version, pos, params=None, **extra):
    return {"id": f"id-{name}", "name": name, "type": ntype, "typeVersion": version, "position": pos, "parameters": params or {}, **extra}


def _code(name, pos):
    return _node(name, "n8n-nodes-base.code", 2, pos, {"mode": "runOnceForAllItems", "language": "javaScript",
                                                       "jsCode": f"// {name}\nreturn $input.all();"})


def _rl(value, name):
    return {"__rl": True, "mode": "list", "value": value, "cachedResultName": name}


def _wires(*pairs):
    """("Source", output index, "Target") -> n8n's connections object."""
    conns = {}
    for source, index, target in pairs:
        outs = conns.setdefault(source, {"main": []})["main"]
        while len(outs) <= index:
            outs.append([])
        outs[index].append({"node": target, "type": "main", "index": 0})
    return conns


TG = {"telegramApi": {"id": "EXPORT-TG", "name": "DTJ Page Bot"}}
KEY = {"httpHeaderAuth": {"id": "EXPORT-KEY", "name": "DTJ Catcher Bot Key"}}
SEND = {"resource": "message", "operation": "sendMessage", "chatId": "={{ $json.chat_id }}", "text": "={{ $json.text }}"}
# Small stand-ins for the three repo exports (the real ones change while the bot is being built): the same kinds of parts, export ids
EXPORTS = {
    "Store Factory: Page Design": {
        "id": "EXPORT-PD", "name": "Store Factory: Page Design", "description": "page design",
        "settings": {"executionOrder": "v1", "availableInMCP": True, "binaryMode": "separate"},
        "nodes": [_node("When a Brief Is Ready", "n8n-nodes-base.executeWorkflowTrigger", 1.2, [0, 0],
                        {"workflowInputs": {"values": [{"name": "row_id", "type": "number"}]}}),
                  _node("Load Brief", "n8n-nodes-base.dataTable", 1.1, [240, 0], {"operation": "get", "dataTableId": _rl("EXPORT-INTAKE", "dtj_client_intake")}),
                  _code("Request for Claude Code: Page Design", [480, 0]),
                  _node("Wait for Claude Code: Page Design", "n8n-nodes-base.wait", 1.1, [720, 0], {"resume": "webhook", "httpMethod": "POST"},
                        webhookId="2b303f14"),
                  _code("Claude Code Reply: Page Design", [960, 0]),
                  _node("Record Page Design", "n8n-nodes-base.dataTable", 1.1, [1200, 0],
                        {"operation": "update", "dataTableId": _rl("EXPORT-INTAKE", "dtj_client_intake")}),
                  _node("Send Result", "n8n-nodes-base.telegram", 1.2, [1440, 240], SEND, onError="continueRegularOutput", webhookId="6ac8",
                        credentials=TG),
                  _node("Sticky Note a4b3e49a", "n8n-nodes-base.stickyNote", 1, [-48, -416], {"content": "## Page design", "color": 5})],
        "connections": _wires(("When a Brief Is Ready", 0, "Load Brief"), ("Load Brief", 0, "Request for Claude Code: Page Design"),
                              ("Request for Claude Code: Page Design", 0, "Wait for Claude Code: Page Design"),
                              ("Wait for Claude Code: Page Design", 0, "Claude Code Reply: Page Design"),
                              ("Claude Code Reply: Page Design", 0, "Record Page Design"), ("Claude Code Reply: Page Design", 0, "Send Result"))},
    "Store Factory: New Page": {
        "id": "EXPORT-NP", "name": "Store Factory: New Page", "description": "new page", "settings": {"executionOrder": "v1", "availableInMCP": True},
        "nodes": [_node("Run by Hand", "n8n-nodes-base.manualTrigger", 1, [0, 0]),
                  _node("From Another Workflow", "n8n-nodes-base.executeWorkflowTrigger", 1.2, [240, 240],
                        {"inputSource": "workflowInputs", "workflowInputs": {"values": [{"name": "product_link", "type": "string"}]}}),
                  _code("Take the Request", [480, 120]),
                  _node("Load Stores", "n8n-nodes-base.dataTable", 1.1, [720, 120], {"resource": "row", "operation": "get",
                        "dataTableId": _rl("EXPORT-STORES", "dtj_stores")}, executeOnce=True, alwaysOutputData=True),
                  _code("Match the Store", [960, 120]),
                  _node("Matched?", "n8n-nodes-base.if", 2.2, [1200, 120], {"conditions": {"combinator": "and", "conditions": []}}),
                  _node("Save Brief", "n8n-nodes-base.dataTable", 1.1, [1440, 0], {"operation": "insert",
                        "dataTableId": _rl("EXPORT-INTAKE", "dtj_client_intake")}),
                  _node("Start Page Design", "n8n-nodes-base.executeWorkflow", 1.3, [1680, 0],
                        {"workflowId": _rl("EXPORT-PD", "Store Factory: Page Design"), "options": {"waitForSubWorkflow": False}}),
                  _code("Started", [1920, 0]), _code("Not Started", [1440, 240])],
        "connections": _wires(("Run by Hand", 0, "Take the Request"), ("From Another Workflow", 0, "Take the Request"),
                              ("Take the Request", 0, "Load Stores"), ("Load Stores", 0, "Match the Store"), ("Match the Store", 0, "Matched?"),
                              ("Matched?", 0, "Save Brief"), ("Matched?", 1, "Not Started"), ("Save Brief", 0, "Start Page Design"),
                              ("Start Page Design", 0, "Started"))},
    "Store Factory: Telegram Bot": {
        "id": "EXPORT-TB", "name": "Store Factory: Telegram Bot", "description": "bot", "settings": {"executionOrder": "v1", "availableInMCP": True},
        "nodes": [_node("Telegram Message", "n8n-nodes-base.telegramTrigger", 1.5, [0, 120], {"updates": ["message", "callback_query"],
                        "additionalFields": {}}, webhookId="9417", credentials=TG),
                  _code("Read the Message", [240, 120]),
                  _node("Load Bot Users", "n8n-nodes-base.dataTable", 1.1, [480, 120], {"resource": "row", "operation": "get",
                        "dataTableId": _rl("EXPORT-USERS", "dtj_bot_users")}, executeOnce=True, alwaysOutputData=True),
                  _code("Who Is It", [720, 120]),
                  _node("What to Do", "n8n-nodes-base.switch", 3.2, [960, 120], {"rules": {"values": []}}),
                  _node("Ask New Page", "n8n-nodes-base.executeWorkflow", 1.3, [1200, 0], {"workflowId": _rl("EXPORT-NP", "Store Factory: New Page")}),
                  _node("Ask the Switch", "n8n-nodes-base.httpRequest", 4.2, [1200, 240], {"method": "POST", "url": "https://catcher.example/licence",
                        "authentication": "genericCredentialType", "genericAuthType": "httpHeaderAuth"}, onError="continueRegularOutput",
                        credentials=KEY),
                  _node("Send", "n8n-nodes-base.telegram", 1.2, [1440, 120], SEND, onError="continueRegularOutput", webhookId="0706", credentials=TG)],
        "connections": _wires(("Telegram Message", 0, "Read the Message"), ("Read the Message", 0, "Load Bot Users"),
                              ("Load Bot Users", 0, "Who Is It"), ("Who Is It", 0, "What to Do"), ("What to Do", 0, "Ask New Page"),
                              ("What to Do", 1, "Ask the Switch"), ("What to Do", 2, "Send"), ("What to Do", 3, "Send"),
                              ("Ask New Page", 0, "Send"), ("Ask the Switch", 0, "Send"))},
}
SPEC = {"dtj_client_intake": {"columns": [{"name": "status", "type": "string"}, {"name": "samples", "type": "number"}]},
        "dtj_stores": {"columns": [{"name": "store_name", "type": "string"}, {"name": "myshopify_domain", "type": "string"},
                                   {"name": "active", "type": "boolean"}]},
        "dtj_bot_users": {"columns": [{"name": "telegram_user_id", "type": "string"}, {"name": "name", "type": "string"},
                                      {"name": "role", "type": "string"}, {"name": "active", "type": "boolean"}]}}
CREDS = [{"id": "C-tg", "name": "DTJ Page Bot", "type": "telegramApi"}, {"id": "C-key", "name": "DTJ Catcher Bot Key", "type": "httpHeaderAuth"},
         {"id": "C-gh", "name": "DTJ GitHub Actions", "type": "httpBearerAuth"}, {"id": "C-other", "name": "Serper", "type": "httpHeaderAuth"}]
# made-up test values (not real shops, people or keys)
SEED = [{"store_name": "Shop One", "myshopify_domain": "shop-one.myshopify.com", "active": True}]
ADMIN = {"telegram_user_id": "900000001", "name": "Test Admin", "role": "admin", "active": True}
API_KEY, BOT_TOKEN, BOT_KEY, GH_TOKEN = "n8n-api-key-TEST-0001", "123456:TEST-bot-token-abcdef", "c" * 64, "github_pat_TEST_0001"
KEYS = {"N8N_API_KEY": API_KEY, "DTJ_TELEGRAM_BOT_TOKEN": BOT_TOKEN, "DTJ_CATCHER_BOT_KEY": BOT_KEY, "DTJ_GITHUB_ACTIONS_TOKEN": GH_TOKEN}
_real = {}


def no_keys(name):
    return ""


def no_network(method, url, headers, body=None):
    raise AssertionError(f"a test tried to reach the network: {method} {url}")


def setUpModule():  # no test may read this laptop's real keys or call n8n's API
    _real.update(rest=setup.rest, user_var=setup.user_var)
    setup.rest, setup.user_var = no_network, no_keys


def tearDownModule():
    setup.rest, setup.user_var = _real["rest"], _real["user_var"]


class FakeApi:
    """n8n's public REST API: the credential forms, creating a credential (into the fake server), one workflow read."""

    FORMS = {"telegramApi": {"type": "object", "additionalProperties": False, "required": ["accessToken"],
                             "properties": {"accessToken": {"type": "string"}, "baseUrl": {"type": "string"}}},
             "httpHeaderAuth": {"type": "object", "additionalProperties": False, "required": ["name", "value"],
                                "properties": {"name": {"type": "string"}, "value": {"type": "string"}}},
             "httpBearerAuth": {"type": "object", "additionalProperties": False, "required": ["token"],
                                "properties": {"token": {"type": "string"}}}}

    def __init__(self, server, forms=None, post_status=200, post_answer=None):
        self.server, self.requests = server, []
        self.forms = forms or self.FORMS
        self.post_status, self.post_answer = post_status, post_answer

    def __call__(self, method, url, headers, body=None):
        self.requests.append((method, url, dict(headers), copy.deepcopy(body)))
        path = url.split("/api/v1", 1)[1]
        if headers.get("X-N8N-API-KEY") != API_KEY:
            return 401, {"message": "unauthorized"}
        if method == "GET" and path.startswith("/credentials/schema/"):
            return 200, self.forms[path.rsplit("/", 1)[1]]
        if method == "GET" and path.startswith("/workflows"):
            return 200, {"data": [{"id": "W1", "name": "x"}], "nextCursor": None}
        if method == "POST" and path == "/credentials":
            if self.post_status != 200:
                return self.post_status, self.post_answer or {"message": "refused"}
            cid = self.server.new_id("C")
            self.server.creds.append({"id": cid, "name": body["name"], "type": body["type"]})
            return 200, {"id": cid, "name": body["name"], "type": body["type"], "createdAt": "2026-10-12T10:00:00.000Z"}
        raise AssertionError(f"unexpected API call {method} {path}")

    def posts(self):
        return [r for r in self.requests if r[0] == "POST"]


def _after(line: str, marker: str):
    """The JSON value that follows `marker` in a line of generated SDK code."""
    return json.JSONDecoder().raw_decode(line, line.index(marker) + len(marker))[0]


class FakeN8n:
    """Answers the MCP tools from memory and refuses what the real server would refuse (>100 operations, unknown nodes...)."""

    def __init__(self, creds=CREDS, projects=None):
        self.calls, self.n = [], 0
        self.tables, self.workflows, self.rows = {}, {}, {}
        self.creds = copy.deepcopy(list(creds))
        self.projects = projects or [{"id": "P-me", "name": "Personal", "type": "personal"}]

    def __call__(self, tool, args):
        self.calls.append((tool, copy.deepcopy(args)))
        if not hasattr(self, "t_" + tool):
            raise AssertionError(f"unexpected tool {tool}")
        return getattr(self, "t_" + tool)(copy.deepcopy(args))

    def new_id(self, prefix):
        self.n += 1
        return f"{prefix}{self.n:03d}"

    def tools(self):
        return [t for t, _ in self.calls]

    # ---- building the fake's state
    def add_table(self, name, columns, project="P-me"):
        tid = self.new_id("T")
        self.tables[tid] = {"id": tid, "name": name, "projectId": project,
                            "columns": [{"id": f"c{i}", "name": c["name"], "type": c["type"], "index": i} for i, c in enumerate(columns)]}
        self.rows[tid] = []
        return tid

    def table(self, name):
        return next(t for t in self.tables.values() if t["name"] == name)

    def put_rows(self, name, rows):
        t = self.table(name)
        cols = {c["name"] for c in t["columns"]}
        for r in rows:
            self.rows[t["id"]].append({**{k: v for k, v in r.items() if k in cols}, "id": len(self.rows[t["id"]]) + 1,
                                       "createdAt": "2026-10-12T10:00:00.000Z", "updatedAt": "2026-10-12T10:00:00.000Z"})

    def add_workflow(self, export, ids, published=True, project="P-me"):
        wid = self.new_id("W")
        nodes = []
        for node in copy.deepcopy(export["nodes"]):
            node["parameters"] = setup.remap(node.get("parameters", {}), ids)
            for key, c in list((node.get("credentials") or {}).items()):
                c["id"] = setup.credential_id(self.creds, key, c["name"])
                if not c["id"]:
                    del node["credentials"][key]
            nodes.append(node)
        version = self.new_id("v")
        self.workflows[wid] = {"id": wid, "name": export["name"], "projectId": project, "nodes": nodes,
                               "connections": copy.deepcopy(export["connections"]), "settings": dict(export.get("settings") or {}),
                               "versionId": version, "activeVersionId": version if published else None, "active": published}
        return wid

    def matching(self, published=True, skip=(), spec=SPEC, exports=EXPORTS):
        """A server that matches the exports (with its own ids), with a shop and an admin."""
        ids = {name: self.add_table(name, t["columns"]) for name, t in spec.items()}
        for name, export in exports.items():
            if name not in skip:
                ids[name] = self.add_workflow(export, ids, published)
        self.put_rows("dtj_stores", SEED)
        self.put_rows("dtj_bot_users", [ADMIN])
        return ids

    def node(self, wid, name):
        return next(n for n in self.workflows[wid]["nodes"] if n["name"] == name)

    def touch(self, wid):
        self.workflows[wid]["versionId"] = self.new_id("v")

    # ---- read tools
    def t_search_workflows(self, a):
        q = (a.get("query") or "").lower()
        data = [{"id": w["id"], "name": w["name"], "active": w["active"]} for w in self.workflows.values()
                if q in w["name"].lower() and a.get("projectId") in (None, w["projectId"])]
        return {"data": data, "count": len(data)}

    def t_get_workflow_details(self, a):
        wf = copy.deepcopy(self.workflows[a["workflowId"]])
        wf["activeVersion"] = {"sameAsDraft": wf["versionId"] == wf["activeVersionId"]} if wf["activeVersionId"] else None
        return {"workflow": wf, "triggerInfo": ""}

    def t_search_data_tables(self, a):
        q = (a.get("query") or "").lower()
        data = [t for t in self.tables.values() if q in t["name"].lower()]
        return {"data": copy.deepcopy(data), "count": len(data)}

    def t_search_projects(self, a):
        return {"data": self.projects, "count": len(self.projects)}

    def t_list_credentials(self, a):
        return {"data": self.creds, "count": len(self.creds)}

    def t_get_data_table_rows(self, a):
        assert a["projectId"] == self.tables[a["dataTableId"]]["projectId"], "get_data_table_rows needs the table's projectId"
        rows = self.rows[a["dataTableId"]]
        for f in (a.get("filter") or {}).get("filters", []):
            assert f.get("condition", "eq") == "eq"
            rows = [r for r in rows if r.get(f["columnName"]) == f["value"]]
        skip, limit = a.get("skip", 0), a.get("limit", 100)
        assert limit <= 100
        return {"rows": copy.deepcopy(rows[skip:skip + limit]), "count": len(rows)}

    def t_add_data_table_rows(self, a):
        t = self.tables[a["dataTableId"]]
        assert a["projectId"] == t["projectId"] and 1 <= len(a["rows"]) <= 1000
        cols = {c["name"] for c in t["columns"]}
        for r in a["rows"]:
            assert set(r) <= cols, f"no such column: {set(r) - cols}"
        self.put_rows(t["name"], a["rows"])
        return {"inserted": len(a["rows"])}

    # ---- write tools (only --apply / --publish use them)
    def t_create_data_table(self, a):
        assert a["projectId"] in {p["id"] for p in self.projects}
        return {"id": self.add_table(a["name"], a["columns"], a["projectId"]), "name": a["name"]}

    def t_add_data_table_column(self, a):
        t = self.tables[a["dataTableId"]]
        t["columns"].append({"id": "new", "name": a["name"], "type": a["type"], "index": len(t["columns"])})
        return {"ok": True}

    def t_validate_workflow(self, a):
        return {"valid": True}

    def t_create_workflow_from_code(self, a):
        nodes = []
        for line in a["code"].splitlines():
            if line.startswith("const "):
                assert "trigger({" in line, "only trigger nodes may be in the create code"
                nodes.append({"name": _after(line, "config: { name: "), "type": _after(line, "type: "), "typeVersion": _after(line, "version: "),
                              "position": _after(line, "position: "), "parameters": _after(line, "parameters: ")})
        wid = self.new_id("W")
        self.workflows[wid] = {"id": wid, "name": a["name"], "projectId": a.get("projectId", "P-me"), "nodes": nodes, "connections": {},
                               "settings": {}, "versionId": self.new_id("v"), "activeVersionId": None, "active": False}
        return {"workflowId": wid, "url": f"https://n8n.example/workflow/{wid}"}

    def t_update_workflow(self, a):
        ops = a["operations"]
        if not 1 <= len(ops) <= 100:
            raise RuntimeError(f"update_workflow refused: {len(ops)} operations (1 to 100)")
        wf = copy.deepcopy(self.workflows[a["workflowId"]])
        names = {n["name"]: n for n in wf["nodes"]}
        for op in ops:
            kind = op["type"]
            if kind == "addNode":
                assert op["node"]["name"] not in names, f"duplicate node {op['node']['name']}"
                assert set(op["node"]) <= {"name", "type", "typeVersion", "position", "parameters", "notes", "disabled"}, op["node"]
                names[op["node"]["name"]] = dict(op["node"])
                wf["nodes"].append(names[op["node"]["name"]])
            elif kind == "setNodeSettings":
                names[op["nodeName"]].update(op["settings"])
            elif kind == "addConnection":
                assert op["source"] in names and op["target"] in names, op
                outs = wf["connections"].setdefault(op["source"], {}).setdefault(op.get("connectionType", "main"), [])
                while len(outs) <= op.get("sourceIndex", 0):
                    outs.append([])
                outs[op.get("sourceIndex", 0)].append({"node": op["target"], "type": op.get("connectionType", "main"),
                                                       "index": op.get("targetIndex", 0)})
            elif kind == "setNodeCredential":
                assert op["credentialId"] in {c["id"] for c in self.creds}, "a credential id this server does not have"
                names[op["nodeName"]].setdefault("credentials", {})[op["credentialKey"]] = {"id": op["credentialId"], "name": op["credentialName"]}
            elif kind == "updateNodeParameters":
                names[op["nodeName"]]["parameters"].update(op["parameters"])
            elif kind == "setWorkflowSettings":
                wf["settings"].update(op["settings"])
            else:
                raise RuntimeError(f"the fake does not do {kind}")
        self.workflows[a["workflowId"]] = wf
        self.touch(a["workflowId"])
        return {"appliedOperations": len(ops)}

    def t_publish_workflow(self, a):
        wf = self.workflows[a["workflowId"]]
        wf["activeVersionId"], wf["active"] = wf["versionId"], True
        return {"ok": True}


def run(fn, fake, **kw):
    lines = []
    if fn in (setup.check, setup.apply):
        kw = {"seed": SEED, "env": no_keys, "http": no_network, **kw}
    result = fn(fake, out=lines.append, exports=EXPORTS, spec=SPEC, **kw)
    return result, "\n".join(lines)


class Check(unittest.TestCase):
    def test_check_passes_on_a_matching_server_and_only_reads(self):
        fake = FakeN8n()
        ids = fake.matching()
        problems, text = run(setup.check, fake)
        self.assertEqual(problems, 0, text)
        self.assertIn("READY", text)
        for name, wid in ids.items():
            self.assertIn(wid, text)  # every id it found is printed
        self.assertIn("C-tg", text)
        self.assertTrue(set(fake.tools()) <= READS, fake.tools())
        read = {a["dataTableId"] for t, a in fake.calls if t == "get_data_table_rows"}
        self.assertEqual(read, {fake.table("dtj_stores")["id"], fake.table("dtj_bot_users")["id"]})  # rows of these two only
        self.assertIn("dtj_stores: 1 shop(s)", text)
        self.assertIn("dtj_bot_users: 1 people, 1 admins, 0 designers, 0 requesters", text)
        self.assertNotIn(ADMIN["telegram_user_id"], text)
        self.assertNotIn(ADMIN["name"], text)

    def test_main_exit_codes(self):
        fake = FakeN8n()
        fake.matching(spec=setup.load_spec(), exports=setup.load_exports())  # main() reads the checked-in files
        with redirect_stdout(io.StringIO()):
            self.assertEqual(setup.main([], call=lambda t, a: fake(t, a)), 0)
        wf = next(iter(fake.workflows.values()))
        code_node = next(n for n in wf["nodes"] if "jsCode" in n["parameters"])
        code_node["parameters"]["jsCode"] = "return [];"
        with redirect_stdout(io.StringIO()) as out:
            self.assertEqual(setup.main(["--check"], call=lambda t, a: fake(t, a)), 1)
        self.assertIn(f"code differs from the repo in: {code_node['name']}", out.getvalue())

    def test_not_published_and_draft_ahead_are_reported(self):
        fake = FakeN8n()
        ids = fake.matching()
        fake.workflows[ids["Store Factory: New Page"]].update(activeVersionId=None, active=False)
        fake.touch(ids["Store Factory: Telegram Bot"])
        problems, text = run(setup.check, fake)
        self.assertEqual(problems, 2, text)
        self.assertIn("Store Factory: New Page (id W", text)
        self.assertIn("not published", text)
        self.assertIn("draft has changes that are not live yet", text)
        self.assertIn('--publish --only "Store Factory: Telegram Bot"', text)


class Apply(unittest.TestCase):
    def test_a_differing_code_node_is_reported_and_apply_syncs_exactly_that_node(self):
        fake = FakeN8n()
        ids = fake.matching()
        wid = ids["Store Factory: New Page"]
        fake.node(wid, "Match the Store")["parameters"]["jsCode"] = "// an older version\nreturn [];"
        problems, text = run(setup.check, fake)
        self.assertEqual(problems, 1, text)
        self.assertIn("code differs from the repo in: Match the Store", text)

        fake.calls.clear()
        left, text = run(setup.apply, fake)
        self.assertEqual(left, 0, text)
        updates = [a for t, a in fake.calls if t == "update_workflow"]
        self.assertEqual(len(updates), 1)
        self.assertEqual(updates[0]["workflowId"], wid)
        want = next(n for n in EXPORTS["Store Factory: New Page"]["nodes"] if n["name"] == "Match the Store")["parameters"]["jsCode"]
        self.assertEqual(updates[0]["operations"], [{"type": "updateNodeParameters", "nodeName": "Match the Store", "parameters": {"jsCode": want}}])
        self.assertEqual(fake.node(wid, "Match the Store")["parameters"]["jsCode"], want)
        self.assertNotIn("publish_workflow", fake.tools())
        self.assertIn("Needs publishing", text)
        self.assertIn("Store Factory: New Page (id W", text)
        # afterwards only the publishing is left
        problems, text = run(setup.check, fake)
        self.assertEqual(problems, 1, text)
        self.assertIn("draft has changes that are not live yet", text)

    def test_a_missing_workflow_is_built_from_its_export(self):
        fake = FakeN8n()
        ids = fake.matching(skip=("Store Factory: Telegram Bot",))
        left, text = run(setup.apply, fake)
        self.assertEqual(left, 0, text)
        created = [a for t, a in fake.calls if t == "create_workflow_from_code"]
        self.assertEqual(len(created), 1)
        self.assertEqual(created[0]["name"], "Store Factory: Telegram Bot")
        self.assertEqual(created[0]["projectId"], "P-me")
        code = created[0]["code"]
        self.assertIn("type: \"n8n-nodes-base.telegramTrigger\", version: 1.5", code)
        self.assertIn("name: \"Telegram Message\", position: [0, 120]", code)
        self.assertIn('"updates": ["message", "callback_query"]', code)
        self.assertIn("telegramApi: newCredential(\"DTJ Page Bot\")", code)
        self.assertEqual(code.count("const "), 1)  # only the trigger
        new = next(w for w in fake.workflows.values() if w["name"] == "Store Factory: Telegram Bot")

        updates = [a for t, a in fake.calls if t == "update_workflow" and a["workflowId"] == new["id"]]
        ops = [op for a in updates for op in a["operations"]]
        self.assertTrue(all(len(a["operations"]) <= 100 for a in updates))
        added = {op["node"]["name"]: op["node"] for op in ops if op["type"] == "addNode"}
        self.assertEqual(set(added), {n["name"] for n in EXPORTS["Store Factory: Telegram Bot"]["nodes"]} - {"Telegram Message"})
        # links to other n8n objects point at THIS server's ids, not the export's
        self.assertEqual(added["Load Bot Users"]["parameters"]["dataTableId"]["value"], ids["dtj_bot_users"])
        self.assertEqual(added["Ask New Page"]["parameters"]["workflowId"]["value"], ids["Store Factory: New Page"])
        self.assertEqual(added["Ask New Page"]["parameters"]["workflowId"]["cachedResultName"], "Store Factory: New Page")
        # node settings, branch outputs, credentials by name
        self.assertIn({"type": "setNodeSettings", "nodeName": "Load Bot Users", "settings": {"executeOnce": True, "alwaysOutputData": True}}, ops)
        self.assertIn({"type": "setNodeSettings", "nodeName": "Send", "settings": {"onError": "continueRegularOutput"}}, ops)
        self.assertIn({"type": "addConnection", "source": "What to Do", "target": "Send", "sourceIndex": 3, "targetIndex": 0}, ops)
        self.assertIn({"type": "addConnection", "source": "What to Do", "target": "Ask the Switch", "sourceIndex": 1, "targetIndex": 0}, ops)
        self.assertFalse([op for op in ops if op["type"] == "addNode" and "webhookId" in op["node"]])  # n8n gives its own
        self.assertIn({"type": "setNodeCredential", "nodeName": "Ask the Switch", "credentialKey": "httpHeaderAuth", "credentialId": "C-key",
                       "credentialName": "DTJ Catcher Bot Key"}, ops)
        self.assertIn({"type": "setNodeCredential", "nodeName": "Telegram Message", "credentialKey": "telegramApi", "credentialId": "C-tg",
                       "credentialName": "DTJ Page Bot"}, ops)
        self.assertIn({"type": "setWorkflowSettings", "settings": {"executionOrder": "v1"}}, ops)
        self.assertIn("availableInMCP", text)  # the setting MCP cannot set is named, not silently dropped
        # nothing deleted or published; afterwards the check only wants it published
        self.assertFalse([op for op in ops if op["type"].startswith("remove")])
        self.assertNotIn("publish_workflow", fake.tools())
        problems, text = run(setup.check, fake)
        self.assertEqual(problems, 1, text)
        self.assertIn("Store Factory: Telegram Bot (id W", text)
        self.assertIn("not published", text)

    def test_everything_is_built_on_an_empty_server_in_order(self):
        fake = FakeN8n(projects=[{"id": "P-team", "name": "Team", "type": "team"}, {"id": "P-me", "name": "Me", "type": "personal"}])
        left, text = run(setup.apply, fake)
        self.assertEqual(left, 0, text)
        made = [(t, a) for t, a in fake.calls if t in ("create_data_table", "create_workflow_from_code")]
        self.assertEqual([a["name"] for _, a in made], [*SPEC, *setup.WORKFLOWS])
        self.assertEqual({a["projectId"] for _, a in made}, {"P-me"})  # nothing holds them yet: the personal project
        self.assertEqual(made[0][1]["columns"], SPEC["dtj_client_intake"]["columns"])
        by_name = {w["name"]: w for w in fake.workflows.values()}
        start = next(n for n in by_name["Store Factory: New Page"]["nodes"] if n["name"] == "Start Page Design")
        self.assertEqual(start["parameters"]["workflowId"]["value"], by_name["Store Factory: Page Design"]["id"])
        self.assertIn("dtj_stores was empty: added 1 shop(s) from stores.seed.json", text)
        problems, text = run(setup.check, fake)
        self.assertEqual(problems, 4, text)  # the three "not published" and no admin yet
        self.assertEqual(text.count("not published"), 3)
        self.assertIn("no active admin", text)

    def test_new_tables_go_to_the_project_that_holds_the_workflows(self):
        fake = FakeN8n(projects=[{"id": "P-me", "name": "Me", "type": "personal"}, {"id": "P-team", "name": "Team", "type": "team"}])
        ids = {name: fake.add_table(name, t["columns"], "P-team") for name, t in SPEC.items() if name != "dtj_bot_users"}
        ids["dtj_bot_users"] = "old-id"
        for name, export in EXPORTS.items():
            ids[name] = fake.add_workflow(export, ids, project="P-team")
        left, text = run(setup.apply, fake)
        created = [a for t, a in fake.calls if t == "create_data_table"]
        self.assertEqual([(a["name"], a["projectId"]) for a in created], [("dtj_bot_users", "P-team")])
        self.assertIn("points at dtj_bot_users id old-id", text)  # the stale link is reported, not rewritten
        self.assertEqual(left, 1)

    def test_a_large_export_is_sent_in_chunks_of_at_most_100(self):
        nodes = [{"name": "Start", "type": "n8n-nodes-base.manualTrigger", "typeVersion": 1, "position": [0, 0], "parameters": {}}]
        nodes += [{"name": f"Step {i}", "type": "n8n-nodes-base.noOp", "typeVersion": 1, "position": [200 * i, 0], "parameters": {}}
                  for i in range(1, 121)]
        conns = {nodes[i]["name"]: {"main": [[{"node": nodes[i + 1]["name"], "type": "main", "index": 0}]]} for i in range(120)}
        export = {"name": "Store Factory: Page Design", "nodes": nodes, "connections": conns, "settings": {}}
        fake = FakeN8n()
        wid, missing = setup.create_workflow(fake, export, {}, CREDS, "P-me", out=lambda _: None)
        self.assertEqual(missing, 0)
        sizes = [len(a["operations"]) for t, a in fake.calls if t == "update_workflow"]
        self.assertEqual(sizes, [100, 100, 40])  # 120 nodes + 120 connections
        self.assertEqual(len(fake.workflows[wid]["nodes"]), 121)
        self.assertEqual(setup.connection_list(fake.workflows[wid]["connections"]), setup.connection_list(conns))

    def test_a_missing_credential_is_reported_never_invented(self):
        fake = FakeN8n(creds=[c for c in CREDS if c["name"] != "DTJ Catcher Bot Key"])
        fake.matching(skip=("Store Factory: Telegram Bot",))
        problems, text = run(setup.check, fake)
        self.assertIn("DTJ Catcher Bot Key (Header Auth): not on this n8n server", text)
        self.assertIn("Credentials > Create credential > Header Auth, named exactly 'DTJ Catcher Bot Key'", text)
        left, text = run(setup.apply, fake)
        self.assertEqual(left, 1)  # --apply exits 1: something is still missing
        self.assertIn("no Header Auth credential named 'DTJ Catcher Bot Key' on this server", text)
        ops = [op for t, a in fake.calls if t == "update_workflow" for op in a["operations"]]
        self.assertFalse([op for op in ops if op["type"] == "setNodeCredential" and op["nodeName"] == "Ask the Switch"])
        self.assertFalse([t for t in fake.tools() if "credential" in t and t != "list_credentials"])
        self.assertEqual(len(fake.creds), len(CREDS) - 1)
        problems, text = run(setup.check, fake)
        self.assertIn("Ask the Switch: needs the Header Auth credential 'DTJ Catcher Bot Key': none attached", text)
        self.assertIn("create the Header Auth credential 'DTJ Catcher Bot Key' in n8n first", text)

    def test_a_detached_credential_is_attached_by_name(self):
        fake = FakeN8n()
        ids = fake.matching()
        del fake.node(ids["Store Factory: Page Design"], "Send Result")["credentials"]
        problems, text = run(setup.check, fake)
        self.assertEqual(problems, 1, text)
        left, text = run(setup.apply, fake)
        ops = [op for t, a in fake.calls if t == "update_workflow" for op in a["operations"]]
        self.assertEqual(ops, [{"type": "setNodeCredential", "nodeName": "Send Result", "credentialKey": "telegramApi", "credentialId": "C-tg",
                                "credentialName": "DTJ Page Bot"}])

    def test_structure_differences_are_reported_never_deleted(self):
        fake = FakeN8n()
        ids = fake.matching()
        wid = ids["Store Factory: Telegram Bot"]
        fake.workflows[wid]["nodes"].append({"name": "Someone's Test", "type": "n8n-nodes-base.noOp", "typeVersion": 1, "position": [0, 0],
                                             "parameters": {}})
        fake.workflows[wid]["connections"]["Ask the Switch"]["main"][0].clear()
        problems, text = run(setup.check, fake)
        self.assertIn("nodes on n8n that the export does not have: Someone's Test", text)
        self.assertIn("connections missing on n8n: Ask the Switch (output 0) -> Send", text)
        self.assertIn("deploy_telegram_bot.py", text)
        fake.calls.clear()
        left, text = run(setup.apply, fake)
        self.assertEqual(left, 1)
        self.assertNotIn("update_workflow", fake.tools())
        self.assertIn("NOT changed (structure)", text)
        self.assertIn("Someone's Test", {n["name"] for n in fake.workflows[wid]["nodes"]})
        self.assertNotIn("publish_workflow", fake.tools())


class Publish(unittest.TestCase):
    def test_publish_only_after_a_fresh_check_passes(self):
        fake = FakeN8n()
        ids = fake.matching()
        wid = ids["Store Factory: New Page"]
        fake.node(wid, "Started")["parameters"]["jsCode"] = "return [];"
        fake.touch(wid)
        left, text = run(setup.publish, fake)
        self.assertEqual(left, 1)
        self.assertIn("NOT published: Store Factory: New Page", text)
        self.assertIn("code differs from the repo in: Started", text)
        self.assertNotIn("publish_workflow", fake.tools())

        run(setup.apply, fake)
        self.assertNotIn("publish_workflow", fake.tools())
        left, text = run(setup.publish, fake, only="Store Factory: New Page")
        self.assertEqual(left, 0, text)
        self.assertEqual([a for t, a in fake.calls if t == "publish_workflow"], [{"workflowId": wid}])
        self.assertIn("published Store Factory: New Page", text)
        problems, text = run(setup.check, fake)
        self.assertEqual(problems, 0, text)

    def test_publish_skips_workflows_already_live(self):
        fake = FakeN8n()
        fake.matching()
        left, text = run(setup.publish, fake)
        self.assertEqual(left, 0)
        self.assertNotIn("publish_workflow", fake.tools())
        self.assertEqual(text.count("nothing to publish"), 3)

    def test_publish_is_never_part_of_plain_apply_or_check(self):
        fake = FakeN8n()
        fake.matching(published=False, spec=setup.load_spec(), exports=setup.load_exports())
        with redirect_stdout(io.StringIO()):
            setup.main(["--apply"], call=lambda t, a: fake(t, a))
            setup.main([], call=lambda t, a: fake(t, a))
        self.assertNotIn("publish_workflow", fake.tools())
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                setup.main(["--check", "--publish"], call=lambda t, a: fake(t, a))


class Tables(unittest.TestCase):
    def test_tables_json_holds_column_names_and_types_only(self):
        fake = FakeN8n()
        fake.matching()
        tid = next(t for t in fake.tables.values() if t["name"] == "dtj_stores")
        tid["columns"].reverse()  # written in n8n's column order (index), whatever order the answer has
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "tables.json"
            self.assertEqual(setup.save_tables(fake, path, out=lambda _: None), 0)
            saved = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(saved, {name: {"columns": t["columns"]} for name, t in SPEC.items()})
        self.assertEqual({k for t in saved.values() for c in t["columns"] for k in c}, {"name", "type"})
        self.assertTrue(set(fake.tools()) <= {"search_data_tables"}, fake.tools())

    def test_tables_json_is_not_written_when_a_table_is_missing(self):
        fake = FakeN8n()
        fake.add_table("dtj_stores", SPEC["dtj_stores"]["columns"])
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "tables.json"
            lines = []
            self.assertEqual(setup.save_tables(fake, path, out=lines.append), 1)
            self.assertFalse(path.exists())
        self.assertIn("dtj_client_intake", lines[0])

    def test_the_checked_in_tables_json_covers_the_three_tables(self):
        spec = setup.load_spec()
        self.assertEqual(list(spec), list(setup.TABLE_NAMES))
        for table in spec.values():
            self.assertTrue(table["columns"])
            for c in table["columns"]:
                self.assertEqual(set(c), {"name", "type"})
                self.assertIn(c["type"], ("string", "number", "boolean", "date"))

    def test_a_missing_column_is_added_and_a_wrong_type_only_reported(self):
        fake = FakeN8n()
        fake.matching()
        t = next(t for t in fake.tables.values() if t["name"] == "dtj_bot_users")
        t["columns"] = [{"id": "c0", "name": "telegram_user_id", "type": "number", "index": 0}]
        problems, text = run(setup.check, fake)
        self.assertIn("columns missing: name, role, active", text)
        self.assertIn("telegram_user_id is number, not string", text)
        left, text = run(setup.apply, fake)
        added = [a for tool, a in fake.calls if tool == "add_data_table_column"]
        self.assertEqual([(a["name"], a["type"]) for a in added], [("name", "string"), ("role", "string"), ("active", "boolean")])
        self.assertEqual(left, 1)


def keys(**over):
    """This laptop's Windows user variables for a test (None = the variable is missing)."""
    have = {**KEYS, **over}
    return lambda name: have.get(name) or ""


def server_without(*names):
    fake = FakeN8n(creds=[c for c in CREDS if c["name"] not in names])
    fake.matching()
    return fake


class Credentials(unittest.TestCase):
    def test_a_missing_credential_is_created_from_this_laptops_keys_and_attached(self):
        fake = server_without("DTJ Page Bot", "DTJ Catcher Bot Key")
        api = FakeApi(fake)
        left, text = run(setup.apply, fake, env=keys(), http=api)
        self.assertEqual(left, 0, text)
        posts = api.posts()
        self.assertEqual([b for _, _, _, b in posts], [
            {"name": "DTJ Page Bot", "type": "telegramApi", "data": {"accessToken": BOT_TOKEN}},
            {"name": "DTJ Catcher Bot Key", "type": "httpHeaderAuth", "data": {"name": "X-DTJ-Bot-Key", "value": BOT_KEY}}])
        for method, url, headers, _ in api.requests:
            self.assertTrue(url.startswith(f"https://{setup.N8N_HOST}/api/v1/"), url)
            self.assertEqual(headers, {"X-N8N-API-KEY": API_KEY})
        self.assertEqual([u for m, u, _, _ in api.requests if m == "GET"],
                         [f"https://{setup.N8N_HOST}/api/v1/credentials/schema/telegramApi",
                          f"https://{setup.N8N_HOST}/api/v1/credentials/schema/httpHeaderAuth"])  # the form is read before each create
        self.assertIn("created credential DTJ Page Bot (Telegram API", text)
        for secret in (API_KEY, BOT_TOKEN, BOT_KEY):
            self.assertNotIn(secret, text)
        tg = next(c["id"] for c in fake.creds if c["name"] == "DTJ Page Bot")
        wid = next(w["id"] for w in fake.workflows.values() if w["name"] == "Store Factory: Telegram Bot")
        self.assertEqual(fake.node(wid, "Send")["credentials"]["telegramApi"]["id"], tg)  # then attached as before
        problems, text = run(setup.check, fake, env=keys(), http=api)
        self.assertEqual(problems, 2, text)  # only publishing is left: the attachments changed Page Design's and the bot's drafts
        self.assertIn("[ok] n8n API key: works", text)

    def test_the_github_key_for_intake_is_created_as_bearer_auth(self):
        exports = copy.deepcopy(EXPORTS)
        bot = exports["Store Factory: Telegram Bot"]
        bot["nodes"].append(_node("Start Brand Intake", "n8n-nodes-base.httpRequest", 4.2, [1200, 480],
                                  {"method": "POST", "url": "https://api.example/dispatches", "authentication": "genericCredentialType",
                                   "genericAuthType": "httpBearerAuth"}, onError="continueRegularOutput",
                                  credentials={"httpBearerAuth": {"id": "EXPORT-GH", "name": "DTJ GitHub Actions"}}))
        fake = FakeN8n(creds=[c for c in CREDS if c["name"] != "DTJ GitHub Actions"])
        fake.matching(exports=exports)
        api = FakeApi(fake)
        lines = []
        setup.apply(fake, out=lines.append, exports=exports, spec=SPEC, env=keys(), http=api, seed=SEED)
        text = "\n".join(lines)
        self.assertEqual([b for _, _, _, b in api.posts()],
                         [{"name": "DTJ GitHub Actions", "type": "httpBearerAuth", "data": {"token": GH_TOKEN}}])
        self.assertIn("created credential DTJ GitHub Actions (Bearer Auth", text)
        self.assertNotIn(GH_TOKEN, text)
        wid = next(w["id"] for w in fake.workflows.values() if w["name"] == "Store Factory: Telegram Bot")
        gh = next(c["id"] for c in fake.creds if c["name"] == "DTJ GitHub Actions")
        self.assertEqual(fake.node(wid, "Start Brand Intake")["credentials"]["httpBearerAuth"]["id"], gh)

    def test_a_form_that_needs_more_fields_is_refused_and_nothing_is_created(self):
        fake = server_without("DTJ Page Bot")
        forms = copy.deepcopy(FakeApi.FORMS)
        forms["telegramApi"]["required"].append("baseUrl")
        api = FakeApi(fake, forms=forms)
        left, text = run(setup.apply, fake, env=keys(), http=api)
        self.assertEqual(api.posts(), [])
        self.assertIn("not created: n8n's Telegram API form needs baseUrl, which this tool does not fill (it guesses nothing)", text)
        self.assertGreater(left, 0)
        self.assertEqual(len(fake.creds), len(CREDS) - 1)

    def test_a_form_without_one_of_our_fields_is_refused(self):
        fake = server_without("DTJ Catcher Bot Key")
        forms = copy.deepcopy(FakeApi.FORMS)
        forms["httpHeaderAuth"] = {"type": "object", "required": ["value"], "properties": {"value": {"type": "string"}}}
        api = FakeApi(fake, forms=forms)
        left, text = run(setup.apply, fake, env=keys(), http=api)
        self.assertEqual(api.posts(), [])
        self.assertIn("form has no name", text)

    def test_without_the_api_key_or_a_value_nothing_is_created_and_the_advice_says_what_is_missing(self):
        for missing, why in (("N8N_API_KEY", "this laptop has no N8N_API_KEY"), ("DTJ_TELEGRAM_BOT_TOKEN", "this laptop has no DTJ_TELEGRAM_BOT_TOKEN")):
            fake = server_without("DTJ Page Bot")
            api = FakeApi(fake)
            env = keys(**{missing: None})
            problems, text = run(setup.check, fake, env=env, http=api)
            self.assertIn(why, text)
            self.assertIn("pull it from the vault: python tools/team-setup/vault.py pull", text)
            self.assertIn("or create it in n8n by hand", text)
            left, text = run(setup.apply, fake, env=env, http=api)
            self.assertIn(f"DTJ Page Bot (Telegram API): not created: {why}", text)
            self.assertEqual(api.posts(), [])
            self.assertGreater(left, 0)
            for secret in (API_KEY, BOT_TOKEN):
                self.assertNotIn(secret, text)

    def test_the_check_says_when_apply_can_create_it(self):
        fake = server_without("DTJ Catcher Bot Key")
        problems, text = run(setup.check, fake, env=keys(), http=FakeApi(fake))
        self.assertIn("--apply creates it through n8n's API from this laptop's DTJ_CATCHER_BOT_KEY and attaches it", text)
        self.assertEqual(fake.creds, [c for c in CREDS if c["name"] != "DTJ Catcher Bot Key"])  # the check created nothing
        self.assertNotIn(BOT_KEY, text)

    def test_a_refusal_that_repeats_a_secret_is_hidden(self):
        fake = server_without("DTJ Page Bot")
        api = FakeApi(fake, post_status=400, post_answer={"message": f"accessToken {BOT_TOKEN} is not valid (key {API_KEY})"})
        left, text = run(setup.apply, fake, env=keys(), http=api)
        self.assertIn("not created: n8n answered HTTP 400", text)
        self.assertNotIn(BOT_TOKEN, text)
        self.assertNotIn(API_KEY, text)

    def test_the_api_key_line(self):
        fake = FakeN8n()
        fake.matching()
        _, text = run(setup.check, fake, env=keys(N8N_API_KEY="a-wrong-key"), http=FakeApi(fake))
        self.assertIn("[..] n8n API key: refused (HTTP 401)", text)  # a note while nothing needs it
        _, text = run(setup.check, fake)
        self.assertIn("this laptop has no N8N_API_KEY (only needed to create a missing credential)", text)
        fake = server_without("DTJ Page Bot")
        problems, text = run(setup.check, fake, env=keys(N8N_API_KEY="a-wrong-key"), http=FakeApi(fake))
        self.assertIn("[!!] n8n API key: refused (HTTP 401)", text)  # a problem when a credential has to be created
        self.assertNotIn("a-wrong-key", text)

    def test_the_rest_call_sends_json_with_our_user_agent_and_never_reaches_out_in_tests(self):
        seen = {}

        class Answer:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def read(self):
                return b'{"id": "C9"}'

        def opener(req, timeout):
            seen.update(url=req.full_url, method=req.get_method(), body=json.loads(req.data), ua=req.get_header("User-agent"),
                        key=req.get_header("X-n8n-api-key"), ctype=req.get_header("Content-type"))
            return Answer()

        real = setup.urllib.request.urlopen
        setup.urllib.request.urlopen = opener
        try:
            status, answer = _real["rest"]("POST", "https://n8n.example/api/v1/credentials", {"X-N8N-API-KEY": "k"}, {"name": "x"})
        finally:
            setup.urllib.request.urlopen = real
        self.assertEqual((status, answer), (200, {"id": "C9"}))
        self.assertEqual(seen, {"url": "https://n8n.example/api/v1/credentials", "method": "POST", "body": {"name": "x"},
                                "ua": "dtj-setup/1", "key": "k", "ctype": "application/json"})


class Shops(unittest.TestCase):
    def test_the_seed_goes_only_into_an_empty_table(self):
        fake = FakeN8n()
        fake.matching()
        fake.rows[fake.table("dtj_stores")["id"]].clear()
        seed = SEED + [{"store_name": "Shop Two", "myshopify_domain": "shop-two.myshopify.com", "active": False, "id": 7,
                        "createdAt": "2026-01-01T00:00:00.000Z"}]
        problems, text = run(setup.check, fake, seed=seed)
        self.assertIn("dtj_stores: 0 shops", text)
        self.assertIn("--apply (restores the 2 shop(s) in stores.seed.json)", text)
        left, text = run(setup.apply, fake, seed=seed)
        added = [a for t, a in fake.calls if t == "add_data_table_rows"]
        self.assertEqual(len(added), 1)
        self.assertEqual(added[0]["rows"], [SEED[0], {"store_name": "Shop Two", "myshopify_domain": "shop-two.myshopify.com", "active": False}])
        self.assertEqual(added[0]["projectId"], "P-me")
        fake.calls.clear()
        left, text = run(setup.apply, fake, seed=seed)  # it has rows now: never touched again
        self.assertNotIn("add_data_table_rows", fake.tools())
        self.assertIn("dtj_stores: 2 shop(s) already there (not touched)", text)

    def test_an_empty_table_without_a_seed_is_a_problem(self):
        fake = FakeN8n()
        fake.matching()
        fake.rows[fake.table("dtj_stores")["id"]].clear()
        problems, text = run(setup.check, fake, seed=[])
        self.assertEqual(problems, 1, text)
        self.assertIn("add the shops in n8n (Data tables > dtj_stores)", text)
        left, text = run(setup.apply, fake, seed=[])
        self.assertEqual(left, 1)
        self.assertNotIn("add_data_table_rows", fake.tools())

    def test_save_stores_drops_system_columns_and_writes_one_shop_per_line(self):
        fake = FakeN8n()
        fake.matching()
        fake.put_rows("dtj_stores", [{"store_name": f"Shop {i:03d}", "myshopify_domain": f"shop-{i:03d}.myshopify.com", "active": True}
                                     for i in range(150, 0, -1)])
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "stores.seed.json"
            self.assertEqual(setup.save_stores(fake, path, out=lambda _: None, spec=SPEC), 0)
            text = path.read_text(encoding="utf-8")
        shops = json.loads(text)
        self.assertEqual(len(shops), 151)  # read in pages of 100
        self.assertEqual(len([t for t, _ in fake.calls if t == "get_data_table_rows"]), 2)
        self.assertEqual({k for s in shops for k in s}, {"store_name", "myshopify_domain", "active"})
        self.assertEqual(list(shops[0]), ["store_name", "myshopify_domain", "active"])  # the table's column order
        domains = [s["myshopify_domain"] for s in shops]
        self.assertEqual(domains, sorted(domains))
        self.assertEqual(len(text.splitlines()), 151 + 2)
        self.assertTrue(set(fake.tools()) <= READS)

    def test_save_stores_writes_nothing_for_an_empty_table(self):
        fake = FakeN8n()
        fake.add_table("dtj_stores", SPEC["dtj_stores"]["columns"])
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "stores.seed.json"
            self.assertEqual(setup.save_stores(fake, path, out=lambda _: None, spec=SPEC), 1)
            self.assertFalse(path.exists())

    def test_the_checked_in_seed_has_no_system_columns(self):
        seed = setup.load_seed()
        self.assertTrue(seed)
        for shop in seed:
            self.assertFalse(set(shop) & set(setup.SYSTEM_COLUMNS))
            self.assertTrue(shop.get("myshopify_domain", "").endswith(".myshopify.com"))


class People(unittest.TestCase):
    PEOPLE = [ADMIN, {"telegram_user_id": "900000002", "name": "Test Designer", "role": "designer", "active": True},
              {"telegram_user_id": "900000003", "name": "Test Requester", "role": "requester", "active": True},
              {"telegram_user_id": "900000004", "name": "Old Admin", "role": "admin", "active": False}]

    def test_counts_only_never_a_number_or_a_name(self):
        fake = FakeN8n()
        fake.matching()
        fake.put_rows("dtj_bot_users", self.PEOPLE[1:])
        problems, text = run(setup.check, fake)
        self.assertEqual(problems, 0, text)
        self.assertIn("dtj_bot_users: 3 people, 1 admins, 1 designers, 1 requesters (1 inactive not counted)", text)
        for p in self.PEOPLE:
            self.assertNotIn(p["telegram_user_id"], text)
            self.assertNotIn(p["name"], text)

    def test_no_active_admin_is_a_problem_with_the_way_to_add_one(self):
        fake = FakeN8n()
        fake.matching()
        fake.rows[fake.table("dtj_bot_users")["id"]].clear()
        fake.put_rows("dtj_bot_users", self.PEOPLE[1:])
        problems, text = run(setup.check, fake)
        self.assertEqual(problems, 1, text)
        self.assertIn("no active admin", text)
        self.assertIn('the person messages @DtjPageDesignerBot, it replies with their number; then (with Harsh\'s yes) '
                      'python n8n/store-factory/setup_n8n.py --add-admin <number> --name "<name>"', text)
        self.assertNotIn("Old Admin", text)

    def test_add_admin_adds_the_right_row_and_never_prints_the_number(self):
        fake = FakeN8n()
        fake.matching()
        lines = []
        self.assertEqual(setup.add_admin(fake, "900000077", "  New   Admin ", out=lines.append, spec=SPEC), 0)
        self.assertEqual(lines, ["added an admin (New Admin) to dtj_bot_users"])
        added = [a for t, a in fake.calls if t == "add_data_table_rows"]
        self.assertEqual(added[0]["rows"], [{"telegram_user_id": "900000077", "name": "New Admin", "role": "admin", "active": True}])
        looked = [a for t, a in fake.calls if t == "get_data_table_rows"][0]
        self.assertEqual(looked["filter"], {"type": "and", "filters": [{"columnName": "telegram_user_id", "condition": "eq",
                                                                        "value": "900000077"}]})

    def test_add_admin_refuses_duplicates_and_bad_numbers(self):
        fake = FakeN8n()
        fake.matching()
        for number in ("abc", "1234", "1" * 16, "12 345 678", "+919000000"):
            lines = []
            self.assertEqual(setup.add_admin(fake, number, "Someone", out=lines.append, spec=SPEC), 1)
            self.assertIn("5 to 15 digits", lines[0])
        lines = []
        self.assertEqual(setup.add_admin(fake, ADMIN["telegram_user_id"], "Someone", out=lines.append, spec=SPEC), 1)
        self.assertIn("already in dtj_bot_users", lines[0])
        self.assertNotIn(ADMIN["telegram_user_id"], lines[0])
        self.assertEqual(setup.add_admin(fake, "900000078", "", out=lines.append, spec=SPEC), 1)
        self.assertNotIn("add_data_table_rows", fake.tools())

    def test_add_admin_from_the_command_line_prints_no_number(self):
        fake = FakeN8n()
        fake.matching(spec=setup.load_spec(), exports=setup.load_exports())
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = setup.main(["--add-admin", "900000099", "--name", "Cli Admin"], call=lambda t, a: fake(t, a))
        self.assertEqual(code, 0)
        self.assertEqual(out.getvalue().strip(), "added an admin (Cli Admin) to dtj_bot_users")
        self.assertNotIn("900000099", out.getvalue() + err.getvalue())
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                setup.main(["--add-admin", "900000099"], call=lambda t, a: fake(t, a))  # --name is needed


class RepoExports(unittest.TestCase):
    """The real exports and tables.json in this folder, whatever they hold today."""

    def test_each_repo_export_rebuilds_on_an_empty_server_and_then_checks_clean(self):
        exports, spec = setup.load_exports(), setup.load_spec()
        fake = FakeN8n()
        lines = []
        self.assertEqual(setup.apply(fake, out=lines.append, exports=exports, spec=spec), 0, "\n".join(lines))
        self.assertTrue(all(len(a["operations"]) <= 100 for t, a in fake.calls if t == "update_workflow"))
        self.assertNotIn("publish_workflow", fake.tools())
        for name, export in exports.items():
            built = next(w for w in fake.workflows.values() if w["name"] == name)
            self.assertEqual(sorted(n["name"] for n in built["nodes"]), sorted(n["name"] for n in export["nodes"]))
        lines = []
        self.assertEqual(setup.check(fake, out=lines.append, exports=exports, spec=spec), len(exports) + 1, "\n".join(lines))
        self.assertEqual("\n".join(lines).count("not published"), len(exports))
        self.assertIn("no active admin", "\n".join(lines))  # the one thing a person still does (with Harsh's yes)

    def test_each_repo_export_has_a_trigger_and_names_the_workflow_it_is_for(self):
        for name, export in setup.load_exports().items():
            self.assertEqual(export["name"], name)
            code = setup.trigger_code(export, {})
            self.assertGreaterEqual(code.count("trigger({"), 1)
            self.assertNotIn("jsCode", code)


class Pieces(unittest.TestCase):
    def test_remap_points_known_names_at_this_server_only(self):
        params = {"a": {"__rl": True, "mode": "list", "value": "OLD", "cachedResultName": "dtj_stores", "cachedResultUrl": "/data-tables/OLD"},
                  "b": [{"__rl": True, "value": "X", "cachedResultName": "someone else's table"}], "c": "OLD"}
        out = setup.remap(params, {"dtj_stores": "NEW"})
        self.assertEqual(out["a"]["value"], "NEW")
        self.assertEqual(out["a"]["cachedResultUrl"], "/data-tables/NEW")
        self.assertEqual(out["b"][0]["value"], "X")
        self.assertEqual(out["c"], "OLD")
        self.assertEqual(params["a"]["value"], "OLD")  # the export itself is untouched

    def test_trigger_code_holds_only_the_triggers(self):
        code = setup.trigger_code(EXPORTS["Store Factory: New Page"], {})
        self.assertEqual(re.findall(r"const (\w+) = (\w+)\(", code), [("trigger0", "trigger"), ("trigger1", "trigger")])
        self.assertIn('workflow("store-factory-new-page", "Store Factory: New Page")\n  .add(trigger0)\n  .add(trigger1);', code)
        self.assertNotIn("jsCode", code)

    def test_redact_hides_tokens(self):
        text = setup.redact("401 Authorization: Bearer abc.def.ghi and eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0In0.c2lnbmF0dXJl and tok-123",
                            ["tok-123"])
        for secret in ("abc.def.ghi", "eyJhbGciOiJIUzI1NiJ9", "tok-123"):
            self.assertNotIn(secret, text)


class SourceFiles(unittest.TestCase):
    """The .js files are the source of the code nodes: one edited in git but not deployed is reported; the hand-edited node is not."""

    def test_a_file_edited_but_not_deployed_is_reported(self):
        files = {("Store Factory: New Page", "Started"): ("started.js", "// Started\nreturn $input.all();"),
                 ("Store Factory: New Page", "Match the Store"): ("match_store.js", "// changed in git\nreturn [];"),
                 ("Store Factory: Telegram Bot", "Gone"): ("gone.js", "x")}
        self.assertEqual(setup.stale_files(EXPORTS, files), ["match_store.js (Match the Store)",
                                                              "gone.js (no node 'Gone' in telegram_bot.workflow.json)"])

    def test_the_real_files_have_headers_and_the_hand_edited_node_is_left_alone(self):
        files = setup.code_files()
        self.assertIn(("Store Factory: Telegram Bot", "Pick the Shop"), files)
        export = copy.deepcopy(EXPORTS["Store Factory: New Page"])
        export["nodes"].append(_code("What to Design (edit me)", [240, 0]))
        live = copy.deepcopy(export)
        next(n for n in live["nodes"] if n["name"] == "What to Design (edit me)")["parameters"]["jsCode"] = "const product_link = `https://x`;"
        self.assertEqual(setup.compare(export, live, {}, CREDS)["code"], [])  # a pasted link is not "code that differs"


if __name__ == "__main__":
    unittest.main()
