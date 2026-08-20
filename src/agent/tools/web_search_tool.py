from __future__ import annotations

import json
import urllib.parse
import urllib.request

from langchain_core.tools import tool


@tool(description="Search the public web for external research context when the local paper knowledge base is not enough. Returns sourced snippets with URLs.")
def web_search(query: str) -> str:
    query = query.strip()
    if not query:
        return "Empty query."

    params = urllib.parse.urlencode(
        {
            "q": query,
            "format": "json",
            "no_html": "1",
            "skip_disambig": "1",
        }
    )
    request = urllib.request.Request(
        f"https://api.duckduckgo.com/?{params}",
        headers={"User-Agent": "RAGAgent/0.1"},
    )

    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        return f"Web search failed: {exc}"

    results: list[str] = []
    abstract = str(data.get("AbstractText") or "").strip()
    abstract_url = str(data.get("AbstractURL") or "").strip()
    heading = str(data.get("Heading") or query).strip()
    if abstract or abstract_url:
        results.append(_format_result(1, heading, abstract_url, abstract))

    for topic in _flatten_related_topics(data.get("RelatedTopics", [])):
        if len(results) >= 5:
            break
        text = str(topic.get("Text") or "").strip()
        url = str(topic.get("FirstURL") or "").strip()
        if not text and not url:
            continue
        title = text.split(" - ", 1)[0][:120] if text else url
        results.append(_format_result(len(results) + 1, title, url, text))

    if not results:
        return "No web search results found."
    return "\n\n".join(results)


def _format_result(index: int, title: str, url: str, snippet: str) -> str:
    lines = [f"[{index}] {title or 'Untitled'}"]
    if url:
        lines.append(f"URL: {url}")
    if snippet:
        lines.append(f"Snippet: {snippet}")
    return "\n".join(lines)


def _flatten_related_topics(items):
    flattened = []
    for item in items or []:
        topics = item.get("Topics") if isinstance(item, dict) else None
        if isinstance(topics, list):
            flattened.extend(_flatten_related_topics(topics))
        elif isinstance(item, dict):
            flattened.append(item)
    return flattened