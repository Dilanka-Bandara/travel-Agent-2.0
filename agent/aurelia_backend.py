"""
Aurelia backend grounding. THIS is what turns the agent from "makes up
plausible hotels" into "grounded in real, bookable inventory."

It calls your aurelia-travel-backend (Node/Express on :5000) to fetch real
hotels and room availability for a town, dates, and group size. The agent
then describes real options instead of hallucinating them.

The exact endpoints/fields below are placeholders matched to a typical
booking API shape -- adjust the paths and JSON keys to match your real routes
once you wire it up. Everything fails soft so a backend outage never crashes
the agent.
"""
import httpx
from crewai.tools import tool
from app.config.settings import get_settings


def _headers(settings) -> dict:
    h = {"Accept": "application/json"}
    if settings.aurelia_api_key:
        h["Authorization"] = f"Bearer {settings.aurelia_api_key}"
    return h


@tool("Hotel Availability Lookup")
def hotel_availability(town: str, check_in: str, group: str) -> str:
    """Look up REAL hotels and room availability in a town for given dates and
    group size, using the aurelia travel backend. Returns hotel names, room
    configurations that fit the group, and prices. Prefer this over web search
    for hotel/room/price facts -- this data is real and bookable."""
    settings = get_settings()
    if not settings.enable_aurelia_backend:
        return "Aurelia backend disabled. Use web search for hotel info instead."

    url = f"{settings.aurelia_base_url}/api/hotels/availability"
    params = {"town": town, "checkIn": check_in, "group": group}

    try:
        with httpx.Client(timeout=20) as client:
            resp = client.get(url, params=params, headers=_headers(settings))
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as exc:
        return f"Backend lookup failed ({exc}). Fall back to web search for {town}."

    hotels = data.get("hotels", [])
    if not hotels:
        return f"No bookable hotels found in {town} for {check_in} ({group})."

    lines = []
    for h in hotels[:3]:
        lines.append(
            f"{h.get('name')} | rooms: {h.get('roomConfiguration')} | "
            f"price: {h.get('pricePerNight')} | fits group: {h.get('capacityNote', 'n/a')}"
        )
    return "\n".join(lines)
