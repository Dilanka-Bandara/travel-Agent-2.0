"""
The tool the agent actually calls. It tries the configured real booking provider
first; if that returns nothing (disabled, no key, API error, or no inventory),
it transparently falls back to web search so the agent always gets *something*.
"""
import logging
from crewai.tools import tool

from app.tools.hotel_providers import get_hotel_provider
from app.models.hotel import results_to_text
from app.tools.web_search import web_search  # your existing hardened search

logger = logging.getLogger(__name__)


@tool("Hotel Search")
def hotel_search(town: str, check_in: str, check_out: str, adults: int = 2) -> str:
    """Find real hotels in a Sri Lankan town for given dates and number of adults.
    Returns hotel names, prices, ratings, and room notes. Use this for all
    hotel/price/availability facts. Dates must be YYYY-MM-DD."""
    provider = get_hotel_provider()

    if provider is not None:
        results = provider.search(town, check_in, check_out, adults)
        if results:
            return results_to_text(results)
        logger.info("Provider returned no hotels for %s; falling back to web search.", town)

    # Fallback path
    return web_search.run(f"hotels in {town} Sri Lanka price per night booking")
