"""
Core orchestration. This is the brain that ties everything together with the
reliability strategy:

  1. Generate routes ONE THEME AT A TIME (shallow tasks -> small models cope).
  2. On each route, retry-with-repair if Pydantic validation fails.
  3. Build the Google Maps URL deterministically in Python (never trust the LLM
     to format a URL).
  4. Assemble the final CustomTripItinerary in Python, not in one LLM call.
"""
import logging
from typing import List

from crewai import Crew, Process
from pydantic import ValidationError

from app.config.settings import get_settings
from app.models.schemas import TripRequest, RouteOption, CustomTripItinerary, DailyPlan
from app.agents.travel_agents import build_experience_specialist
from app.tasks.route_tasks import build_single_route_task
from app.tools.maps import build_maps_url

logger = logging.getLogger(__name__)

# Themes give the 3 routes their distinct character.
DEFAULT_THEMES = ["The Coastal Route", "The Central/Inland Route", "The Fast & Direct Route"]


def _waypoints_from_route(route: RouteOption) -> List[str]:
    """Pull overnight towns out of the daily breakdown to build the map URL.
    We take the destination town of each day except the last (that's the end)."""
    towns: List[str] = []
    for day in route.daily_breakdown[:-1]:
        # route_segment is like "TownA to TownB"; grab the arrival town
        seg = day.route_segment.lower().replace("->", " to ").split(" to ")
        if len(seg) >= 2:
            towns.append(seg[-1].strip().title())
    return towns


def _generate_one_route(req: TripRequest, theme: str) -> RouteOption:
    """Run the crew for a single theme, with validation-retry."""
    settings = get_settings()
    attempts = settings.max_validation_retries + 1

    for attempt in range(1, attempts + 1):
        agent = build_experience_specialist()
        task = build_single_route_task(req, theme, agent)
        crew = Crew(agents=[agent], tasks=[task], process=Process.sequential)
        output = crew.kickoff()

        # Happy path: CrewAI already parsed it into our pydantic model
        if getattr(output, "pydantic", None):
            return output.pydantic

        # Repair path: try to coerce raw text into the schema
        try:
            return RouteOption.model_validate_json(output.raw)
        except (ValidationError, ValueError) as exc:
            logger.warning("Route '%s' attempt %d failed validation: %s", theme, attempt, exc)
            if attempt == attempts:
                raise
    raise RuntimeError("unreachable")


def design_trip(req: TripRequest) -> CustomTripItinerary:
    """Public entry point. Returns a fully assembled, validated itinerary."""
    settings = get_settings()
    themes = DEFAULT_THEMES[: settings.routes_per_trip]

    routes: List[RouteOption] = []
    for theme in themes:
        try:
            route = _generate_one_route(req, theme)
        except Exception as exc:
            logger.error("Skipping theme '%s' after retries: %s", theme, exc)
            continue

        # Deterministically (re)build the map URL from the towns in the plan.
        waypoints = _waypoints_from_route(route)
        route.full_google_maps_url = build_maps_url(req.start_place, waypoints, req.end_place)
        routes.append(route)

    if not routes:
        raise RuntimeError("No valid routes could be generated. Try a stronger model.")

    summary = (
        f"{len(routes)} route option(s) for a {req.duration}-day {req.transport} trip "
        f"from {req.start_place} to {req.end_place} for {req.travelers}, "
        f"tuned to a '{req.vibe}' vibe."
    )
    return CustomTripItinerary(trip_summary=summary, routes=routes)
