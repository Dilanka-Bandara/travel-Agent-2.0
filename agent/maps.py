"""
Maps grounding. Builds a REAL Google Maps directions URL from start, overnight
waypoints, and end. This replaces the LLM "inventing" a URL string (which often
comes out malformed). We construct it deterministically in Python -- the LLM
only supplies the town names, we build a guaranteed-valid URL.

If a Google Maps API key is present we can also validate/geocode; without one
we still produce a correct public directions URL, which is enough for the user.
"""
from urllib.parse import quote_plus
from typing import List


def build_maps_url(start: str, waypoints: List[str], end: str) -> str:
    """Deterministically build a valid Google Maps directions URL.
    No LLM involved, so it is always well-formed."""
    stops = [start, *waypoints, end]
    encoded = "/".join(quote_plus(s.strip()) for s in stops if s and s.strip())
    return f"https://www.google.com/maps/dir/{encoded}"
