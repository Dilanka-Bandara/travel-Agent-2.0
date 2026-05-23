"""
Web search grounding. Same DuckDuckGo source you had, but hardened:
- never crashes the agent (returns a usable string on failure)
- trims noise so the LLM gets cleaner context
"""
from crewai.tools import tool

try:
    from ddgs import DDGS
except ImportError:  # package was renamed historically; tolerate both
    from duckduckgo_search import DDGS


@tool("Web Search")
def web_search(query: str) -> str:
    """Search the internet and return the top results as text.
    Use this to find activities, attractions, and general hotel information
    along a route."""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5))
    except Exception as exc:  # network down, rate limited, etc.
        return f"Search unavailable ({exc}). Rely on general knowledge for: {query}"

    if not results:
        return "No results found."

    return "\n\n".join(
        f"{r.get('title', '')}\n{r.get('href', '')}\n{r.get('body', '')}"
        for r in results
    )
