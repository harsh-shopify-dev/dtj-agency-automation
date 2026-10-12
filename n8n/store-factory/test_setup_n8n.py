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
SPEC ={"dtj_client_intake": {"columns": [{"name": "status", "type": "string"}, {"name": "samples", "type": "number"}]},
        "dtj_stores": {"columns": [{"name": "myshopify_domain", "type": "string"}, {"name": "active", "type": "boolean"}]},
        "dtj_bot_users": {"columns": [{"name": "telegram_user_id", "type": "string"}, {"name": "role", "type": "string"}]}}
CREDS = [{"id": "C-tg", "name": "DTJ Page Bot", "type": "telegramApi"}, {"id": "C-key", "name": "DTJ Catcher Bot Key", "type": "httpHeaderAuth"},
         {"id": "C-other", "name": "Serper", "type": "httpHeaderAuth"}]


def _after(line: str, marker: str):
    """The JSON value that follows `marker` in a line of generated SDK code."""
    return json.JSONDecoder().raw_decode(line, line.index(marker) + len(marker))[0]


class FakeN8n:
    """Answers the MCP tools from memory and refuses what the real server would refuse (>100 operations, unknown nodes...)."""

    def __init__(self, creds=CREDS, projects=None):
        self.calls, self.n = [], 0
        self.tables, self.workflows = {}, {}
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
        return tid

    def add_workflow(self, export, ids, published=True, project="P-me"):
        wid = self.new_id("W")
        nodes = []
        for node in copy.deepcopy(export["nodes"]):
            node["parameters"] = setup.remap(node.get("parameters", {}), ids)
            for key, c in (node.get("credentials") or {}).items():
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
        """A server that matches the exports (with its own ids)."""
        ids = {name: self.add_table(name, t["columns"]) for name, t in spec.items()}
        for name, export in exports.items():
            if name not in skip:
                ids[name] = self.add_workflow(export, ids, published)
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
        self.assertNotIn("get_data_table_rows", fake.tools())

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
        problems, text = run(setup.check, fake)
        self.assertEqual(problems, 3, text)  # only the three "not published"
        self.assertEqual(text.count("not published"), 3)

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
        self.assertEqual(len(fake.creds), 2)
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
        self.assertIn("columns missing: role", text)
        self.assertIn("telegram_user_id is number, not string", text)
        left, text = run(setup.apply, fake)
        added = [a for tool, a in fake.calls if tool == "add_data_table_column"]
        self.assertEqual([(a["name"], a["type"]) for a in added], [("role", "string")])
        self.assertEqual(left, 1)


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
        self.assertEqual(setup.check(fake, out=lines.append, exports=exports, spec=spec), len(exports), "\n".join(lines))
        self.assertEqual("\n".join(lines).count("not published"), len(exports))

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
