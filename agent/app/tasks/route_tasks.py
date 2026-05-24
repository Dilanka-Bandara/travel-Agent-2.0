"""
Task builders. Instead of one giant task asking for all 3 nested routes, we
build a small task that produces ONE RouteOption for ONE theme. The service
calls this once per theme. Each LLM job is shallow -> small models succeed.
"""
from crewai import Task
from app.models.schemas import RouteOption, TripRequest


def build_single_route_task(req: TripRequest, theme: str, agent) -> Task:
    weather_pref_line = (
        f'- Weather preference: "{req.weather_preference}"'
        if req.weather_preference else
        "- Weather preference: none stated"
    )
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
{weather_pref_line}

Steps:
1. Split the journey into {req.duration} evenly paced days. Choose an overnight
   town for each night so daily drives are reasonable.
2. For EACH overnight town, use the Weather Forecast tool to check the weather
   for that day (compute the date from the start date {req.start_date}). Put a
   short forecast in the 'weather' field of that day.
3. Let weather shape the plan: if a day is rainy, prefer indoor/covered
   activities; if hot and clear, outdoor activities are fine. If the traveler
   stated a weather preference, RESPECT IT when choosing stops and activities.
4. For EACH day, pick 2-3 activities matching the vibe AND the weather.
5. For EACH overnight town, recommend ONE real hotel using the Hotel Search
   tool. Suggest a room configuration that fits {req.travelers}
   (e.g. "1 Family Suite", "2 Double Rooms").
6. Leave full_google_maps_url as an empty string "" -- the system builds it.

Produce exactly ONE route option for the "{theme}" theme.
""",
        expected_output="A single populated RouteOption with a per-day breakdown including weather.",
        agent=agent,
        output_pydantic=RouteOption,
    )
