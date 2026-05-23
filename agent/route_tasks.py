"""
Task builders. Instead of one giant task asking for all 3 nested routes, we
build a small task that produces ONE RouteOption for ONE theme. The service
calls this once per theme. Each LLM job is shallow -> small models succeed.
"""
from crewai import Task
from app.models.schemas import RouteOption, TripRequest


def build_single_route_task(req: TripRequest, theme: str, agent) -> Task:
    return Task(
        description=f"""
Plan ONE complete travel route for this trip, themed: "{theme}".

Trip details:
- From {req.start_place} to {req.end_place}
- Duration: {req.duration} days, by {req.transport}
- Starts: {req.start_date}
- Group: {req.travelers}
- Budget: {req.budget} per night (whole group)
- Vibe: "{req.vibe}"
- Request: "{req.trip_description}"

Steps:
1. Split the journey into {req.duration} evenly paced days. Choose an overnight
   town for each night so daily drives are reasonable.
2. For EACH day, find 2-3 activities matching the vibe.
3. For EACH overnight town, recommend ONE real hotel. You MUST suggest a room
   configuration that fits {req.travelers} (e.g. "1 Family Suite", "2 Double Rooms").
   Use the Hotel Availability Lookup tool first if available; otherwise web search.
4. Leave full_google_maps_url as an empty string "" -- the system builds it.

Produce exactly ONE route option for the "{theme}" theme.
""",
        expected_output="A single populated RouteOption with a per-day breakdown.",
        agent=agent,
        output_pydantic=RouteOption,
    )
