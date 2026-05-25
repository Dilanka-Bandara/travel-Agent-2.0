"""
Real driving distance & duration via OSRM (free public demo server, no key).

This is the structural fix for "unrealistic routes & pacing": instead of letting
the LLM GUESS how far apart towns are, the Route Architect calls this tool to get
REAL km and drive-time, then paces the trip around a sensible daily driving cap.
Works on any model -- even a weak local one paces correctly when it isn't guessing.

Two steps, both keyless:
  1. Open-Meteo geocoding: town name -> lat/lon  (same geocoder the weather tool uses)
  2. OSRM route: lat/lon pair -> distance (km) + duration (driving minutes)

The public OSRM demo server (router.project-osrm.org) is fine for development and
light use. For production/heavy use, host your own OSRM or use OpenRouteService
with a free key. Fails soft: any error returns a clear message, never crashes.
"""
import logging
import httpx
from crewai.tools import tool

logger = logging.getLogger(__name__)

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
OSRM_URL = "http://router.project-osrm.org/route/v1/driving"

# Sensible default pacing cap; the prompt references this too.
RECOMMENDED_MAX_DRIVE_HOURS_PER_DAY = 4


def _geocode(client: httpx.Client, town: str):
    r = client.get(GEOCODE_URL, params={"name": town, "count": 1})
    r.raise_for_status()
    results = r.json().get("results") or []
    if not results:
        return None
    hit = results[0]
    return hit["latitude"], hit["longitude"]


@tool("Driving Distance")
def driving_distance(from_town: str, to_town: str) -> str:
    """Get the REAL driving distance and time between two Sri Lankan towns.
    Returns kilometres and driving hours. Use this to pace a trip so no single
    day has too much driving (aim for at most about 4 hours of driving per day),
    and to choose sensible overnight stops along a long route."""
    try:
        with httpx.Client(timeout=20) as client:
            a = _geocode(client, f"{from_town}, Sri Lanka")
            b = _geocode(client, f"{to_town}, Sri Lanka")
            if not a or not b:
                missing = from_town if not a else to_town
                return f"Could not locate {missing}. Cannot compute distance."

            # OSRM expects lon,lat order
            coords = f"{a[1]},{a[0]};{b[1]},{b[0]}"
            r = client.get(f"{OSRM_URL}/{coords}", params={"overview": "false"})
            r.raise_for_status()
            data = r.json()
    except httpx.HTTPError as exc:
        logger.warning("OSRM/geocode failed %s->%s: %s", from_town, to_town, exc)
        return f"Distance unavailable for {from_town} to {to_town} ({exc})."

    routes = data.get("routes") or []
    if not routes:
        return f"No driving route found between {from_town} and {to_town}."

    km = round(routes[0]["distance"] / 1000, 1)
    hours = round(routes[0]["duration"] / 3600, 1)
    pacing = ""
    if hours > RECOMMENDED_MAX_DRIVE_HOURS_PER_DAY:
        pacing = (f" This exceeds ~{RECOMMENDED_MAX_DRIVE_HOURS_PER_DAY}h/day; "
                  f"split it with an overnight stop in between.")
    return (f"{from_town} to {to_town}: {km} km, about {hours} h driving.{pacing}")
