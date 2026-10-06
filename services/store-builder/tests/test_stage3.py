import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from provision import cli_gql, config, gql, stage3
from provision.actionlog import ActionLog

SHEET = {"products": [
    {"handle": "p-one", "title": "One", "price": "10.00", "images": [{"file": "a.jpg", "alt": "A"}, {"file": "b.jpg", "alt": "B"}]},
    {"handle": "p-two", "title": "Two", "price": "20.00", "images": [{"file": "c.jpg", "alt": "C"}]},
]}


def live_cfg(**extra):
    env = {"AUTOMATION_ENABLED": "true", "DRY_RUN": "false", "AUTOMATION_MODE": "approve", "SHOPIFY_DOMAIN": "t.myshopify.com",
           "SHOPIFY_API_VERSION": "2026-07", "CLIENT_ID": "t", **extra}
    return config.load(env)


class FakeStore:
    """Answers GraphQL by operation name; records every request."""

    def __init__(self, existing=None, fail_create=False, status=200):
        self.existing = existing or []
        self.fail_create = fail_create
        self.status = status
        self.sent = []

    def __call__(self, url, headers, body):
        req = json.loads(body)
        q = req["query"]
        self.sent.append(q.split("(")[0].split()[-1])
        if self.status != 200:
            return self.status, {}, {}
        if "query Existing" in q:
            nodes = [{"handle": h, "variants": {"nodes": [{"price": p}]}} for h, p in self.existing]
            return 200, {}, {"data": {"products": {"nodes": nodes, "pageInfo": {"hasNextPage": False, "endCursor": None}}}}
        if "stagedUploadsCreate" in q:
            n = len(req["variables"]["input"])
            targets = [{"url": "https://up.example/x", "resourceUrl": f"https://res/{i}", "parameters": [{"name": "k", "value": "v"}]} for i in range(n)]
            return 200, {}, {"data": {"stagedUploadsCreate": {"stagedTargets": targets, "userErrors": []}}}
        if "productCreate" in q:
            if self.fail_create:
                return 200, {}, {"data": {"productCreate": {"product": None, "userErrors": [{"field": ["title"], "message": "bad"}]}}}
            handle = req["variables"]["product"]["handle"]
            return 200, {}, {"data": {"productCreate": {"product": {"id": f"gid://p/{handle}", "handle": handle, "status": "DRAFT",
                             "variants": {"nodes": [{"id": f"gid://v/{handle}"}]}}, "userErrors": []}}}
        if "productVariantsBulkUpdate" in q:
            return 200, {}, {"data": {"productVariantsBulkUpdate": {"productVariants": [], "userErrors": []}}}
        raise AssertionError("unexpected operation " + q[:60])


def run_stage(store, cfg=None, approved="Harsh", sheet=SHEET, post_status=201):
    cfg = cfg or live_cfg()
    with tempfile.TemporaryDirectory() as d:
        imgs = Path(d, "imgs")
        imgs.mkdir()
        for n in ("a.jpg", "b.jpg", "c.jpg"):
            (imgs / n).write_bytes(b"x")
        client = gql.GraphQLClient("t.myshopify.com", "2026-07", lambda: "", dry_run=cfg.dry_run, transport=store, sleep=lambda s: None)
        log = ActionLog(Path(d, "log.jsonl"), "t")
        posts = []
        report = stage3.create_products(client, cfg, sheet, imgs, log, approved, post=lambda u, b, c: posts.append(u) or post_status)
        rows = [json.loads(l) for l in Path(d, "log.jsonl").read_text().splitlines()]
        return report, rows, posts


class Stage3Tests(unittest.TestCase):
    def test_creates_draft_products_and_logs_each(self):
        store = FakeStore()
        report, rows, posts = run_stage(store)
        self.assertEqual([c["handle"] for c in report["created"]], ["p-one", "p-two"])
        self.assertEqual(len(posts), 3)  # one upload per image
        self.assertEqual([r["result"] for r in rows], ["success", "success"])
        self.assertTrue(all(r["approved_by"] == "Harsh" for r in rows))
        self.assertNotIn("Delete", " ".join(store.sent))

    def test_no_approver_means_nothing_is_sent(self):
        store = FakeStore()
        report, rows, _ = run_stage(store, approved=None)
        self.assertEqual(store.sent, [])
        self.assertIn("approver", report["stopped"])
        self.assertEqual(rows[0]["result"], "blocked")

    def test_dry_run_and_shadow_send_nothing(self):
        for cfg in (live_cfg(DRY_RUN="true"), live_cfg(AUTOMATION_MODE="shadow"), live_cfg(AUTOMATION_ENABLED="false")):
            store = FakeStore()
            report, _, _ = run_stage(store, cfg=cfg)
            self.assertEqual(store.sent, [])
            self.assertTrue(report["stopped"])

    def test_existing_handles_are_never_touched(self):
        store = FakeStore(existing=[("p-one", "10.00"), ("p-two", "99.00")])
        report, rows, posts = run_stage(store)
        self.assertEqual(report["skipped"], ["p-one"])
        self.assertEqual(report["differs"], ["p-two"])
        self.assertEqual(report["created"], [])
        self.assertEqual(posts, [])
        self.assertNotIn("productCreate", " ".join(store.sent))

    def test_user_error_is_logged_and_run_continues_until_breaker(self):
        sheet = {"products": [{**SHEET["products"][1], "handle": f"p-{i}"} for i in range(4)]}
        report, rows, _ = run_stage(FakeStore(fail_create=True), sheet=sheet)
        self.assertEqual(len(report["failed"]), 3)  # the 4th is never tried
        self.assertIn("circuit breaker", report["stopped"])
        self.assertTrue(all(r["result"] == "failed" for r in rows))

    def test_auth_failure_halts_immediately(self):
        report, rows, _ = run_stage(FakeStore(status=401))
        self.assertIn("auth problem", report["stopped"])

    def test_failed_upload_is_reported_not_swallowed(self):
        report, _, _ = run_stage(FakeStore(), post_status=403)
        self.assertEqual(report["created"], [])
        self.assertEqual(report["failed"][0]["step"], "upload")

    def test_multipart_puts_parameters_before_the_file(self):
        body, ctype = stage3.multipart([("key", "k1"), ("policy", "p1")], "a.jpg", b"DATA", "image/jpeg")
        self.assertLess(body.index(b'name="key"'), body.index(b'name="file"'))
        self.assertLess(body.index(b'name="policy"'), body.index(b'name="file"'))
        self.assertIn(ctype.split("boundary=")[1].encode(), body)

    def test_non_https_upload_target_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d, "a.jpg")
            p.write_bytes(b"x")
            with self.assertRaises(stage3.UploadError):
                stage3.upload_staged({"url": "http://insecure.example/x", "parameters": []}, p, post=lambda *a: 201)


class CliTransportTests(unittest.TestCase):
    def runner(self, code, out):
        calls = []

        def run(cmd):
            calls.append(list(cmd))
            return subprocess.CompletedProcess(cmd, code, out, "")

        run.calls = calls
        return run

    def send(self, runner, query):
        t = cli_gql.make_cli_transport("t.myshopify.com", "2026-07", runner)
        return t("", {}, json.dumps({"query": query, "variables": {}}).encode())

    def test_read_has_no_mutation_flag_and_parses_data(self):
        r = self.runner(0, 'Loading...\n<hint x="1" />\n{\n "shop": {"name": "X"}\n}\n')
        status, _, data = self.send(r, "query { shop { name } }")
        self.assertEqual((status, data), (200, {"data": {"shop": {"name": "X"}}}))
        self.assertNotIn("--allow-mutations", r.calls[0])
        self.assertIn("2026-07", r.calls[0])

    def test_allowed_mutation_gets_the_flag(self):
        r = self.runner(0, '{"productCreate": {"userErrors": []}}')
        self.send(r, "mutation { productCreate(product: {title: \"x\"}) { userErrors { message } } }")
        self.assertIn("--allow-mutations", r.calls[0])

    def test_delete_never_reaches_the_cli(self):
        r = self.runner(0, "{}")
        with self.assertRaises(gql.OperationNotAllowed):
            self.send(r, 'mutation { productDelete(input: {id: "1"}) { deletedProductId } }')
        self.assertEqual(r.calls, [])

    def test_error_box_is_mapped(self):
        box = '╭─ error ─╮\n│ {\n "errors": [{"message": "Access denied for productCreate field."}]\n}\n'
        self.assertEqual(self.send(self.runner(1, box), "query { shop { name } }")[0], 401)
        box2 = '{"errors": [{"message": "Throttled"}]}'
        self.assertEqual(self.send(self.runner(1, box2), "query { shop { name } }")[0], 429)
        box3 = '{"errors": [{"message": "Field x doesn\'t exist"}]}'
        status, _, data = self.send(self.runner(1, box3), "query { shop { name } }")
        self.assertEqual(status, 400)
        self.assertIn("doesn't exist", data["errors"][0]["message"])


if __name__ == "__main__":
    unittest.main()
