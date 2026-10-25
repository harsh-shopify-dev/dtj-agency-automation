"""Shopify Admin GraphQL client with an operation allowlist, cost-aware throttling and safe retries.

Rules from CLAUDE.md / RUNBOOK section 6:
- retry 429 / 5xx / THROTTLED up to 3 times with backoff; 401 or a missing scope halts (no retry)
- only the mutations in ALLOWED_MUTATIONS can be sent; anything with "delete" in it never can
- in dry-run mode a mutation is described, not sent
"""
from __future__ import annotations

import json
import random
import re
import time
import urllib.error
import urllib.request
from typing import Callable

ALLOWED_MUTATIONS = frozenset({"productCreate", "productVariantsBulkUpdate", "stagedUploadsCreate", "fileCreate",
                               # the brand copy (brand_copy.py, 21 Oct 2026): create only; never update what a store has
                               "productSet", "collectionCreate", "publishablePublish", "shopPolicyUpdate"})
MAX_RETRIES = 3
MAX_WAIT_SECONDS = 60.0


class GraphQLError(Exception):
    pass


class OperationNotAllowed(GraphQLError):
    pass


class AuthError(GraphQLError):
    """401, 403 or ACCESS_DENIED. Halt and ask the human to check the token scopes."""


class RetryExhausted(GraphQLError):
    pass


class UserErrors(GraphQLError):
    pass


# ---- reading a GraphQL document without a full parser (fail closed on anything odd) ----

_STRINGS = re.compile(r'"""[\s\S]*?"""|"(?:\\.|[^"\\])*"')


def _clean(query: str) -> str:
    return re.sub(r"#[^\n]*", "", _STRINGS.sub('""', query))


def _skip_group(q: str, i: int, open_c: str, close_c: str) -> int:
    depth = 0
    while i < len(q):
        if q[i] == open_c:
            depth += 1
        elif q[i] == close_c:
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    raise ValueError("unbalanced brackets")


def _root_fields(q: str, start: int) -> tuple[list[str], int]:
    """q[start] is the opening brace of a selection set. Returns its top-level field names."""
    end = _skip_group(q, start, "{", "}")
    i, fields = start + 1, []
    while i < end - 1:
        c = q[i]
        if c.isspace() or c == ",":
            i += 1
        elif q.startswith("...", i):
            fields.append("...")  # spreads can hide fields: not allowed in a mutation
            i += 3
        elif c.isalpha() or c == "_":
            m = re.match(r"[A-Za-z_]\w*", q[i:])
            name = m.group(0)
            i += len(name)
            while q[i].isspace():
                i += 1
            if q[i] == ":":  # alias
                i += 1
                while q[i].isspace():
                    i += 1
                m = re.match(r"[A-Za-z_]\w*", q[i:])
                name = m.group(0)
                i += len(name)
            fields.append(name)
            while i < end - 1:
                while q[i].isspace():
                    i += 1
                if q[i] == "(":
                    i = _skip_group(q, i, "(", ")")
                elif q[i] == "@":
                    i += 1
                    i += len(re.match(r"\w+", q[i:]).group(0))
                elif q[i] == "{":
                    i = _skip_group(q, i, "{", "}")
                else:
                    break
        else:
            raise ValueError(f"unexpected character {c!r}")
    return fields, end


def operations(query: str) -> list[tuple[str, list[str]]]:
    """List of (kind, root_fields) for each query/mutation/subscription. Fragments are skipped."""
    q, i, ops = _clean(query), 0, []
    while i < len(q):
        if q[i].isspace() or q[i] == ",":
            i += 1
            continue
        if q[i] == "{":
            kind, j = "query", i
        else:
            m = re.match(r"(query|mutation|subscription|fragment)\b", q[i:])
            if not m:
                raise ValueError("unrecognised GraphQL document")
            kind, j = m.group(1), i + m.end()
            while j < len(q) and q[j] != "{":  # skip name, variables, directives
                j = _skip_group(q, j, "(", ")") if q[j] == "(" else j + 1
        if j >= len(q):
            raise ValueError("operation has no body")
        if kind == "fragment":
            i = _skip_group(q, j, "{", "}")
            continue
        fields, i = _root_fields(q, j)
        ops.append((kind, fields))
    return ops


def check_operation(query: str) -> str:
    """Returns 'query' or 'mutation', or raises OperationNotAllowed."""
    try:
        ops = operations(query)
    except (ValueError, IndexError, AttributeError) as exc:
        raise OperationNotAllowed(f"cannot read this GraphQL safely ({exc}); refusing") from exc
    if len(ops) != 1:
        raise OperationNotAllowed("send exactly one operation per request")
    kind, fields = ops[0]
    if kind == "subscription":
        raise OperationNotAllowed("subscriptions are not allowed")
    if kind == "mutation":
        for field in fields:
            if "delete" in field.lower():
                raise OperationNotAllowed(f"{field}: tier 3, destructive operations are forbidden")
            if field not in ALLOWED_MUTATIONS:
                raise OperationNotAllowed(f"{field} is not on the mutation allowlist")
    return kind


def raise_on_user_errors(body: dict, field: str) -> dict:
    """Shopify reports most mutation failures in userErrors with HTTP 200."""
    payload = (body.get("data") or {}).get(field) or {}
    errors = payload.get("userErrors") or []
    if errors:
        raise UserErrors(f"{field}: " + "; ".join(f"{e.get('field')}: {e.get('message')}" for e in errors))
    return payload


# ---- transport and client ----

Transport = Callable[[str, dict, bytes], "tuple[int, dict, dict]"]


def urllib_transport(url: str, headers: dict, body: bytes) -> tuple[int, dict, dict]:
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, {k.lower(): v for k, v in resp.headers.items()}, json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as exc:
        try:
            data = json.loads(exc.read() or b"{}")
        except ValueError:
            data = {}
        return exc.code, {k.lower(): v for k, v in exc.headers.items()}, data


class GraphQLClient:
    def __init__(self, store_domain: str, api_version: str, get_token: Callable[[], str], *, dry_run: bool = True,
                 transport: Transport = urllib_transport, sleep: Callable[[float], None] = time.sleep,
                 rand: Callable[[], float] = random.random):
        self.url = f"https://{store_domain}/admin/api/{api_version}/graphql.json"
        self._get_token = get_token
        self.dry_run = dry_run
        self._transport = transport
        self._sleep = sleep
        self._rand = rand
        self._available: float | None = None
        self._restore_rate: float = 50.0
        self._last_cost: float = 0.0

    def execute(self, query: str, variables: dict | None = None) -> dict:
        kind = check_operation(query)
        if kind == "mutation" and self.dry_run:
            return {"dry_run": True, "data": None, "would_send": {"query": query, "variables": variables or {}}}
        body = json.dumps({"query": query, "variables": variables or {}}).encode()
        attempt = 0
        while True:
            self._wait_for_budget()
            headers = {"Content-Type": "application/json", "X-Shopify-Access-Token": self._get_token()}
            status, resp_headers, data = self._transport(self.url, headers, body)
            if status in (401, 403):
                raise AuthError(f"HTTP {status}: stop and check the token and its scopes (e.g. write_products, write_files)")
            errors = data.get("errors") if isinstance(data, dict) else None
            codes = [(e.get("extensions") or {}).get("code") for e in errors or [] if isinstance(e, dict)]
            if "ACCESS_DENIED" in codes:
                raise AuthError("ACCESS_DENIED: " + "; ".join(str(e.get("message")) for e in errors))
            retryable = status == 429 or status >= 500 or "THROTTLED" in codes
            if not retryable:
                if status != 200:
                    detail = "; ".join(str(e.get("message")) for e in errors or [] if isinstance(e, dict))
                    raise GraphQLError(f"HTTP {status}" + (f": {detail}" if detail else ""))
                if errors:
                    raise GraphQLError("; ".join(str(e.get("message")) for e in errors if isinstance(e, dict)))
                self._read_cost(data)
                return data
            attempt += 1
            if attempt > MAX_RETRIES:
                raise RetryExhausted(f"gave up after {MAX_RETRIES} retries (last status {status}, codes {codes})")
            self._sleep(self._backoff(attempt, resp_headers.get("retry-after")))

    def _backoff(self, attempt: int, retry_after: str | None) -> float:
        try:
            if retry_after is not None:
                return min(MAX_WAIT_SECONDS, max(0.0, float(retry_after)))
        except ValueError:
            pass
        return min(MAX_WAIT_SECONDS, (2 ** attempt) * (0.5 + self._rand()))

    def _read_cost(self, data: dict) -> None:
        cost = ((data.get("extensions") or {}).get("cost")) or {}
        status = cost.get("throttleStatus") or {}
        if "currentlyAvailable" in status:
            self._available = float(status["currentlyAvailable"])
        if status.get("restoreRate"):
            self._restore_rate = float(status["restoreRate"])
        self._last_cost = float(cost.get("requestedQueryCost") or 0)

    def _wait_for_budget(self) -> None:
        """If the last reply says we do not have enough points for a similar request, wait for them to refill."""
        if self._available is not None and self._available < self._last_cost:
            self._sleep(min(MAX_WAIT_SECONDS, (self._last_cost - self._available) / self._restore_rate))
            self._available = self._last_cost
