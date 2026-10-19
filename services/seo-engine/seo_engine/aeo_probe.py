"""AEO check: asks an AI assistant the questions founders ask, with live web search, and records BY CODE whether DTJ is named or its
site is cited, and which sites the answer leaned on.

Engines: Claude with web search (the Claude API key), and ChatGPT, Perplexity and Gemini with web search through DataForSEO's
AI Optimization API (the DataForSEO login, inside its spending cap). Each engine only answers the question; none is asked to judge
whether DTJ was mentioned.
"""
from __future__ import annotations

import re
import time
from collections import Counter
from urllib.parse import urlparse

MODEL = "claude-opus-5-5"
EFFORT = "low"  # a plain search-and-answer, like a founder's quick question
MAX_TOKENS = 8000
MAX_SEARCHES = 4
MAX_CONTINUATIONS = 3
DTJ_NAME = re.compile(r"digital\s*tushar\s*joshi|\bDTJ\b|digitaltusharjoshi", re.I)
DTJ_HOST = "digitaltusharjoshi.com"
SYSTEM = ("Answer the question the way you would for a small business owner in India: search the web, then give a short, direct answer "
          "that names specific companies where the question asks for them.")


def _get(obj, name, default=None):
    return obj.get(name, default) if isinstance(obj, dict) else getattr(obj, name, default)


def _host(url: str) -> str:
    return (urlparse(url).hostname or "").removeprefix("www.")


def tools(place: str | None = None) -> list[dict]:
    tool = {"type": "web_search_20260209", "name": "web_search", "max_uses": MAX_SEARCHES,
            "user_location": {"type": "approximate", "country": "IN", "timezone": "Asia/Kolkata"}}
    if place:
        tool["user_location"]["city"] = place
    return [tool]


def request_params(question: str, place: str | None = None) -> dict:
    return {"model": MODEL, "max_tokens": MAX_TOKENS, "system": SYSTEM, "tools": tools(place),
            "messages": [{"role": "user", "content": question}], "output_config": {"effort": EFFORT}}


def read_answer(content: list) -> dict:
    """Pull the answer text, the sites it searched and the sites it cited out of the response blocks."""
    text, searched, cited = [], [], []
    for block in content or []:
        kind = _get(block, "type")
        if kind == "text":
            text.append(_get(block, "text", "") or "")
            for c in _get(block, "citations", None) or []:
                if _get(c, "url"):
                    cited.append(_get(c, "url"))
        elif kind == "web_search_tool_result":
            results = _get(block, "content")
            if isinstance(results, list):  # an error comes back as one object, not a list
                searched += [_get(r, "url") for r in results if _get(r, "url")]
    answer = "".join(text).strip()
    return {
        "answer": answer,
        "dtj_named": bool(DTJ_NAME.search(answer)),
        "dtj_cited": any(_host(u) == DTJ_HOST for u in cited),
        "dtj_in_search_results": any(_host(u) == DTJ_HOST for u in searched),
        "cited_hosts": [h for h, _ in Counter(_host(u) for u in cited).most_common()],
        "searched_hosts": [h for h, _ in Counter(_host(u) for u in searched).most_common(10)],
    }


def ask(question: str, client, place: str | None = None) -> dict:
    params = request_params(question, place)
    started = time.monotonic()
    try:
        resp = client.messages.create(**params)
        for _ in range(MAX_CONTINUATIONS):  # the server pauses long searches; resend so it resumes where it stopped
            if _get(resp, "stop_reason") != "pause_turn":
                break
            params["messages"] = [{"role": "user", "content": question}, {"role": "assistant", "content": resp.content}]
            resp = client.messages.create(**params)
    except Exception as exc:  # noqa: BLE001 - one failed question must not stop the others
        return {"question": question, "place": place, "status": "api-error", "error": f"{type(exc).__name__}: {str(exc)[:200]}"}
    out = {"question": question, "place": place, "status": _get(resp, "stop_reason"), "engine": f"claude:{_get(resp, 'model')}",
           "seconds": round(time.monotonic() - started, 2)}
    out.update(read_answer(_get(resp, "content")))
    return out


def ask_dfs(question: str, dfs, engine: str, place: str | None = None) -> dict:
    """The same question through DataForSEO (chat_gpt | perplexity | gemini), read by the same code."""
    from .dataforseo import BudgetExceeded
    try:
        res = dfs.llm_answer(engine, question, city=place)
    except BudgetExceeded:
        raise
    except Exception as exc:  # noqa: BLE001 - one engine failing must not stop the others
        return {"question": question, "place": place, "engine": engine, "status": "api-error", "error": str(exc)[:200]}
    cited = res["cited_urls"]
    out = {"question": question, "place": place, "engine": f"{engine}:{res['model']}", "status": "end_turn", "answer": res["answer"],
           "dtj_named": bool(DTJ_NAME.search(res["answer"])), "dtj_cited": any(_host(u) == DTJ_HOST for u in cited),
           "dtj_in_search_results": None, "cited_hosts": [h for h, _ in Counter(_host(u) for u in cited).most_common()],
           "searched_hosts": []}
    return out


def probe(questions: list[dict], client=None, limit: int = 10, dfs=None, engines: tuple = ("chat_gpt", "perplexity", "gemini")) -> dict:
    """questions: [{"q": ..., "place": ..., "tier": ...}]. Dry run (no client and no dfs) returns the plan only."""
    chosen = questions[:limit]
    if client is None and dfs is None:
        return {"mode": "dry-run", "planned": [q["q"] for q in chosen], "results": []}
    results, note = [], None
    for q in chosen:
        if client is not None:
            results.append({**ask(q["q"], client, q.get("place")), "tier": q.get("tier")})
        for eng in engines if dfs is not None else ():
            try:
                results.append({**ask_dfs(q["q"], dfs, eng, q.get("place")), "tier": q.get("tier")})
            except Exception as exc:  # noqa: BLE001 - the spending cap: stop asking, keep what we have
                note = f"stopped early: {exc}"
                break
        if note:
            break
    done = [r for r in results if r.get("dtj_named") is not None]
    by_engine = {}
    for r in done:
        e = r["engine"].split(":")[0]
        by_engine.setdefault(e, {"answered": 0, "dtj_named": 0, "dtj_cited": 0})
        by_engine[e]["answered"] += 1
        by_engine[e]["dtj_named"] += r["dtj_named"]
        by_engine[e]["dtj_cited"] += r["dtj_cited"]
    return {
        "mode": "live", "engine": ", ".join(sorted(by_engine)) or "none answered", "results": results, "note": note,
        "summary": {"asked": len(results), "answered": len(done), "dtj_named": sum(r["dtj_named"] for r in done),
                    "dtj_cited": sum(r["dtj_cited"] for r in done), "by_engine": by_engine,
                    "top_cited_sites": [h for h, _ in Counter(h for r in done for h in r["cited_hosts"]).most_common(10)]},
    }
