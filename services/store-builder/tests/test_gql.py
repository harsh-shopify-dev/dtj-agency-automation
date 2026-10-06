import json
import unittest

from provision import gql
from provision.products import CREATE_FILES, CREATE_PRODUCT, SET_VARIANT, STAGED_UPLOADS


def fake(responses):
    """Transport that returns queued (status, headers, body) and counts calls."""
    calls = []

    def transport(url, headers, body):
        calls.append((url, headers, json.loads(body)))
        return responses[min(len(calls) - 1, len(responses) - 1)]

    transport.calls = calls
    return transport


def client(responses, dry_run=False):
    sleeps = []
    c = gql.GraphQLClient("t.myshopify.com", "2026-01", lambda: "tok", dry_run=dry_run,
                          transport=fake(responses), sleep=sleeps.append, rand=lambda: 0.5)
    return c, sleeps


OK = (200, {}, {"data": {"shop": {"name": "x"}}})
Q = "query { shop { name } }"


class AllowlistTests(unittest.TestCase):
    def test_the_four_pipeline_mutations_are_allowed(self):
        for doc in (STAGED_UPLOADS, CREATE_PRODUCT, SET_VARIANT, CREATE_FILES):
            self.assertEqual(gql.check_operation(doc), "mutation")

    def test_reads_are_allowed(self):
        self.assertEqual(gql.check_operation(Q), "query")
        self.assertEqual(gql.check_operation("{ shop { name } }"), "query")

    def test_delete_is_refused(self):
        for name in ("productDelete", "themeDelete", "fileDelete"):
            with self.assertRaises(gql.OperationNotAllowed):
                gql.check_operation(f'mutation {{ {name}(input: {{id: "gid://x/1"}}) {{ userErrors {{ message }} }} }}')

    def test_unlisted_mutation_is_refused(self):
        with self.assertRaises(gql.OperationNotAllowed):
            gql.check_operation("mutation { themePublish(id: \"1\") { userErrors { message } } }")

    def test_alias_cannot_hide_a_delete(self):
        with self.assertRaises(gql.OperationNotAllowed):
            gql.check_operation('mutation { productCreate: productDelete(input: {id: "1"}) { userErrors { message } } }')

    def test_allowed_name_inside_a_string_does_not_count(self):
        with self.assertRaises(gql.OperationNotAllowed):
            gql.check_operation('mutation { themePublish(id: "productCreate") { userErrors { message } } }')

    def test_fragment_spread_in_a_mutation_is_refused(self):
        with self.assertRaises(gql.OperationNotAllowed):
            gql.check_operation("mutation { ...F } fragment F on Mutation { productDelete(input: {id: \"1\"}) { deletedProductId } }")

    def test_two_operations_in_one_request_are_refused(self):
        with self.assertRaises(gql.OperationNotAllowed):
            gql.check_operation(Q + " " + STAGED_UPLOADS)

    def test_garbage_is_refused(self):
        with self.assertRaises(gql.OperationNotAllowed):
            gql.check_operation("mutation { productCreate(")


class ClientTests(unittest.TestCase):
    def test_dry_run_does_not_send_a_mutation(self):
        c, _ = client([OK], dry_run=True)
        out = c.execute(STAGED_UPLOADS, {"input": []})
        self.assertTrue(out["dry_run"])
        self.assertEqual(c._transport.calls, [])

    def test_dry_run_still_allows_reads(self):
        c, _ = client([OK], dry_run=True)
        self.assertEqual(c.execute(Q)["data"]["shop"]["name"], "x")

    def test_blocked_operation_is_never_sent(self):
        c, _ = client([OK])
        with self.assertRaises(gql.OperationNotAllowed):
            c.execute('mutation { productDelete(input: {id: "1"}) { deletedProductId } }')
        self.assertEqual(c._transport.calls, [])

    def test_token_goes_in_the_header_only(self):
        c, _ = client([OK])
        c.execute(Q)
        url, headers, body = c._transport.calls[0]
        self.assertEqual(headers["X-Shopify-Access-Token"], "tok")
        self.assertNotIn("tok", json.dumps(body))
        self.assertTrue(url.endswith("/admin/api/2026-01/graphql.json"))

    def test_401_halts_without_retry(self):
        c, sleeps = client([(401, {}, {})])
        with self.assertRaises(gql.AuthError):
            c.execute(Q)
        self.assertEqual(len(c._transport.calls), 1)
        self.assertEqual(sleeps, [])

    def test_access_denied_halts_without_retry(self):
        denied = (200, {}, {"errors": [{"message": "Access denied for productCreate", "extensions": {"code": "ACCESS_DENIED"}}]})
        c, _ = client([denied])
        with self.assertRaises(gql.AuthError):
            c.execute(Q)
        self.assertEqual(len(c._transport.calls), 1)

    def test_429_honours_retry_after_then_succeeds(self):
        c, sleeps = client([(429, {"retry-after": "2"}, {}), OK])
        self.assertEqual(c.execute(Q)["data"]["shop"]["name"], "x")
        self.assertEqual(sleeps, [2.0])

    def test_5xx_backs_off_exponentially_with_jitter(self):
        c, sleeps = client([(503, {}, {}), (502, {}, {}), OK])
        c.execute(Q)
        self.assertEqual(sleeps, [2.0, 4.0])  # 2**n * (0.5 + 0.5)

    def test_gives_up_after_three_retries(self):
        c, sleeps = client([(500, {}, {})])
        with self.assertRaises(gql.RetryExhausted):
            c.execute(Q)
        self.assertEqual(len(c._transport.calls), 4)  # first try + 3 retries
        self.assertEqual(len(sleeps), 3)

    def test_graphql_throttled_error_is_retried(self):
        throttled = (200, {}, {"errors": [{"message": "Throttled", "extensions": {"code": "THROTTLED"}}]})
        c, sleeps = client([throttled, OK])
        c.execute(Q)
        self.assertEqual(len(sleeps), 1)

    def test_waits_when_cost_balance_is_too_low(self):
        low = (200, {}, {"data": {}, "extensions": {"cost": {"requestedQueryCost": 100, "actualQueryCost": 10,
                         "throttleStatus": {"maximumAvailable": 1000, "currentlyAvailable": 20, "restoreRate": 40}}}})
        c, sleeps = client([low, OK])
        c.execute(Q)
        self.assertEqual(sleeps, [])  # nothing known before the first reply
        c.execute(Q)
        self.assertEqual(sleeps, [2.0])  # (100 - 20) / 40

    def test_user_errors_raise(self):
        body = {"data": {"productCreate": {"product": None, "userErrors": [{"field": ["title"], "message": "can't be blank"}]}}}
        with self.assertRaises(gql.UserErrors):
            gql.raise_on_user_errors(body, "productCreate")
        self.assertEqual(gql.raise_on_user_errors({"data": {"productCreate": {"userErrors": []}}}, "productCreate"),
                         {"userErrors": []})


if __name__ == "__main__":
    unittest.main()
