"""DataForSEO: keyword data, Google results and AI-assistant answers, with a hard spending cap per run.

Login from DATAFORSEO_LOGIN / DATAFORSEO_PASSWORD at call time (never stored, never logged). Every response states its own cost in
USD; the client adds it up and refuses further calls once DFS_MAX_USD (default 3.00) is reached, so a run can never overspend.
Endpoints and field names checked against docs.dataforseo.com on 14 Oct 2026:
  dataforseo_labs/google/keyword_ideas/live   items[].keyword, keyword_info.search_volume/cpc, keyword_properties.keyword_difficulty,
                                              search_intent_info.main_intent
  serp/google/organic/live/advanced           items[] with type "organic", rank_group, url, title, domain
  ai_optimization/<engine>/llm_responses/live items[] type "message", sections[].text, sections[].annotations[].url
"""
from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request
from typing import Callable, Mapping

API = "https://api.dataforseo.com/v3/"
INDIA = 2356
DEFAULT_CAP_USD = 3.00
# Base model names resolve to the latest version (DataForSEO docs); check them with each engine's llm_responses/models endpoint.
LLM_MODELS = {"chat_gpt": "gpt-4.1", "perplexity": "sonar", "gemini": "gemini-2.5-flash"}

Opener = Callable[[urllib.request.Request], dict]


class DataForSEOError(Exception):
    pass


class BudgetExceeded(DataForSEOError):
    pass


def _open(req: urllib.request.Request) -> dict:
    try:
        with urllib.request.urlopen(req, timeout=150) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise DataForSEOError(f"HTTP {exc.code}") from None
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        raise DataForSEOError(type(exc).__name__) from None


def available(env: Mapping[str, str] | None = None) -> bool:
    env = os.environ if env is None else env
    return bool(env.get("DATAFORSEO_LOGIN") and env.get("DATAFORSEO_PASSWORD"))


class Client:
    def __init__(self, *, cap_usd: float | None = None, opener: Opener = _open, env: Mapping[str, str] | None = None):
        self._env = os.environ if env is None else env
        self.cap = cap_usd if cap_usd is not None else float(self._env.get("DFS_MAX_USD") or DEFAULT_CAP_USD)
        self.spent = 0.0
        self.calls = 0
        self._opener = opener

    def _auth(self) -> str:
        login, password = self._env.get("DATAFORSEO_LOGIN"), self._env.get("DATAFORSEO_PASSWORD")
        if not login or not password:
            raise DataForSEOError("DATAFORSEO_LOGIN and DATAFORSEO_PASSWORD are not set")
        return base64.b64encode(f"{login}:{password}".encode()).decode()

    def post(self, path: str, task: dict) -> dict:
        """One task; returns tasks[0].result[0] (or {}). Raises on an error status or when the cap is reached."""
        if self.spent >= self.cap:
            raise BudgetExceeded(f"spending cap reached (${self.spent:.2f} of ${self.cap:.2f})")
        req = urllib.request.Request(API + path, data=json.dumps([task]).encode(), method="POST",
                                     headers={"Authorization": f"Basic {self._auth()}", "Content-Type": "application/json"})
        body = self._opener(req)
        self.calls += 1
        self.spent += float(body.get("cost") or 0)
        tasks = body.get("tasks") or []
        if not tasks:
            raise DataForSEOError(f"{path}: no task in the answer ({body.get('status_message')})")
        t = tasks[0]
        if t.get("status_code") != 20000:
            raise DataForSEOError(f"{path}: {t.get('status_code')} {t.get('status_message')}")
        return (t.get("result") or [{}])[0] or {}

    # Keywords -------------------------------------------------------------------------------------------------------------------
    def keyword_ideas(self, seeds: list[str], *, location_code: int = INDIA, limit: int = 300) -> list[dict]:
        res = self.post("dataforseo_labs/google/keyword_ideas/live",
                        {"keywords": seeds[:200], "location_code": location_code, "language_code": "en", "limit": limit})
        out = []
        for it in res.get("items") or []:
            info, props, intent = it.get("keyword_info") or {}, it.get("keyword_properties") or {}, it.get("search_intent_info") or {}
            out.append({"keyword": it.get("keyword"), "volume": info.get("search_volume"), "cpc": info.get("cpc"),
                        "kd": props.get("keyword_difficulty"), "intent": intent.get("main_intent")})
        return [k for k in out if k["keyword"]]

    # Google results -------------------------------------------------------------------------------------------------------------
    def serp(self, keyword: str, *, location_name: str | None = None, depth: int = 10) -> list[dict]:
        task = {"keyword": keyword, "language_code": "en", "depth": depth, "device": "mobile"}
        task.update({"location_name": location_name} if location_name else {"location_code": INDIA})
        res = self.post("serp/google/organic/live/advanced", task)
        items = [i for i in res.get("items") or [] if i.get("type") == "organic"]
        return [{"rank": i.get("rank_group"), "url": i.get("url"), "title": i.get("title"), "domain": i.get("domain")} for i in items]

    # AI assistants --------------------------------------------------------------------------------------------------------------
    def llm_answer(self, engine: str, question: str, *, city: str | None = None, model: str | None = None) -> dict:
        task = {"user_prompt": question[:500], "model_name": model or LLM_MODELS[engine], "web_search": True,
                "web_search_country_iso_code": "IN", "max_output_tokens": 2048}
        if city:
            task["web_search_city"] = city
        res = self.post(f"ai_optimization/{engine}/llm_responses/live", task)
        text, urls = [], []
        for item in res.get("items") or []:
            sections = item.get("sections") or (item.get("message") or {}).get("sections") or []
            if item.get("type") not in (None, "message") and not item.get("message"):
                continue
            for s in sections:
                text.append(s.get("text") or "")
                urls += [a.get("url") for a in s.get("annotations") or [] if a.get("url")]
        return {"answer": "\n".join(t for t in text if t).strip(), "cited_urls": urls, "model": res.get("model_name") or task["model_name"]}
