"""
A progress-reporting variant of design_trip. Same logic as the original
(per-route generation, validation-retry, deterministic map URL, Python
assembly) but it calls a callback as it moves through real stages so the
frontend animation reflects actual work.

Add this function to app/services/trip_designer.py (or keep it here and import
both). It reuses the existing helpers from trip_designer.
"""
import logging
from typing import Callable, List

from app.config.settings import get_settings
from app.models.schemas import TripRequest, RouteOption, CustomTripItinerary
from app.tools.maps import build_maps_url

logger = logging.getLogger(__name__)

ProgressCb = Callable[[str, int, str], None]


def design_trip_with_progress(req: TripRequest, on_progress: ProgressCb) -> CustomTripItinerary:
    # Imported here to reuse the existing internals without circular imports.
    from app.services.trip_designer import (
        DEFAULT_THEMES, _generate_one_route, _waypoints_from_route,
    )

    settings = get_settings()
    themes = DEFAULT_THEMES[: settings.routes_per_trip]
    total = len(themes)
    routes: List[RouteOption] = []

    for i, theme in enumerate(themes):
        base = int((i / total) * 90)  # leave last 10% for assembly
        on_progress("planning", base + 5,
                    f"Pacing route {i + 1} of {total}: {theme}")

        try:
            # _generate_one_route internally does hotels + weather tool calls.
            on_progress("hotels", base + 12,
                        f"Finding hotels & activities for {theme}")
            route = _generate_one_route(req, theme)
            on_progress("weather", base + 22,
                        f"Checking weather along {theme}")
        except Exception as exc:  # noqa: BLE001
            logger.error("Skipping theme '%s': %s", theme, exc)
            continue

        waypoints = _waypoints_from_route(route)
        route.full_google_maps_url = build_maps_url(req.start_place, waypoints, req.end_place)
        routes.append(route)

    on_progress("assembling", 95, "Putting your itinerary together")

    if not routes:
        raise RuntimeError("No valid routes could be generated. Try a stronger model.")

    summary = (
        f"{len(routes)} route option(s) for a {req.duration}-day {req.transport} trip "
        f"from {req.start_place} to {req.end_place} for {req.travelers}, "
        f"tuned to a '{req.vibe}' vibe."
    )
    return CustomTripItinerary(trip_summary=summary, routes=routes)
