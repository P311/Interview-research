"""Web search via Tavily (https://tavily.com), a dedicated search API decoupled from
whichever chat model is configured. None of the cheap models this pipeline targets
offer a hosted search tool the way Claude or Gemini do, so retrieval lives here and
only synthesis goes through the LLM."""

import requests

from jobagent.config import TAVILY_API_KEY

TAVILY_URL = "https://api.tavily.com/search"


def search(query: str, max_results: int = 5) -> str:
    if not TAVILY_API_KEY:
        raise RuntimeError("Set TAVILY_API_KEY to enable company research (https://tavily.com).")

    response = requests.post(
        TAVILY_URL,
        json={"api_key": TAVILY_API_KEY, "query": query, "max_results": max_results, "include_answer": False},
        timeout=20,
    )
    response.raise_for_status()
    results = response.json().get("results", [])
    if not results:
        raise ValueError(f"no search results for query: {query!r}")

    return "\n\n".join(
        f"Source: {r.get('url')}\nTitle: {r.get('title')}\n{r.get('content', '')}" for r in results
    )
