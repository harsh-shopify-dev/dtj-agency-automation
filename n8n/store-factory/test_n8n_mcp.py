"""n8n_mcp.call against a stand-in n8n: no initialize once n8n shows it keeps no sessions, a 429 waited out, and every workflow
update published at once (23 Oct 2026: four workflows ran their old versions all day). Nothing reaches n8n.

    python -m unittest discover -s n8n/store-factory -t n8n/store-factory -p "test_n8n_mcp.py"
"""
import io
import json
import unittest
import urllib.error
from unittest import mock

import n8n_mcp


class FakeN8n:
    def __init__(self, fail_429=0):
        self.sent, self.fail_429 = [], fail_429

    def __call__(self, req, timeout=0):
        body = json.loads(req.data)
        self.sent.append(body.get("method") if body["method"] == "initialize" else body["params"]["name"])
        if body["method"] == "tools/call" and self.fail_429:
            self.fail_429 -= 1
            raise urllib.error.HTTPError(req.full_url, 429, "Too Many Requests", {}, io.BytesIO(b""))
        if body["method"] == "initialize":
            result = {"protocolVersion": "2025-06-18"}
        elif body["params"]["name"] == "publish_workflow":
            result = {"content": [{"text": json.dumps({"success": True, "activeVersionId": "v2"})}]}
        else:
            result = {"content": [{"text": json.dumps({"appliedOperations": 1})}]}
        resp = mock.MagicMock()
        resp.read.return_value = ("data: " + json.dumps({"jsonrpc": "2.0", "id": body["id"], "result": result})).encode()
        resp.headers = {}
        resp.__enter__.return_value = resp
        return resp


class Call(unittest.TestCase):
    def setUp(self):
        n8n_mcp._SESSION.update(id=None, at=0.0, stateless=False)
        self.addCleanup(n8n_mcp._SESSION.update, id=None, at=0.0, stateless=False)

    def run_with(self, fake, *calls):
        with mock.patch.object(n8n_mcp, "token", return_value="t"), mock.patch.object(n8n_mcp.urllib.request, "urlopen", fake):
            return [n8n_mcp.call(tool, args, sleep=lambda s: None) for tool, args in calls]

    def test_an_update_is_published_at_once(self):
        fake = FakeN8n()
        out = self.run_with(fake, ("update_workflow", {"workflowId": "WF1", "operations": []}))[0]
        self.assertEqual(out, {"appliedOperations": 1, "published": "v2"})
        self.assertEqual(fake.sent, ["initialize", "update_workflow", "publish_workflow"])

    def test_no_initialize_once_n8n_is_stateless_and_a_429_is_waited_out(self):
        fake = FakeN8n(fail_429=1)
        self.run_with(fake, ("search_workflows", {}), ("search_workflows", {}))
        self.assertEqual(fake.sent, ["initialize", "search_workflows", "search_workflows", "search_workflows"])  # one 429, then fine


if __name__ == "__main__":
    unittest.main()
