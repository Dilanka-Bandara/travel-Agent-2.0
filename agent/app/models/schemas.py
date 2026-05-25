"""
Pydantic schemas.

KEY DESIGN DECISION: we keep the final response richly nested (great for the
consumer/API), but we DO NOT ask the LLM to produce that whole nested tree in
one shot. Small local models break on depth. Instead the LLM only ever fills
in ONE RouteOption at a time (a much shallower task), and we assemble the final
CustomTripItinerary in plain Python. This is the single biggest reliability win.
"""
from typing import List
from pydantic import BaseModel, Field


class DailyPlan(BaseModel):
    day_number: int = Field(description="Which day of the trip this is")
    route_segment: str = Field(description="Starting and ending town for this day")
    activities: List[str] = Field(description="2-3 specific activities matching the vibe")
    hotel_name: str = Field(description="Name of the recommended hotel for this night")
    room_configuration: str = Field(description="Room setup for the group size, e.g. '1 Family Suite'")
    hotel_price: str = Field(description="Estimated price per night for the whole group")
    weather: str = Field(default="", description="Weather forecast for this day's stop, e.g. 'partly cloudy, 24-31C, rain 20%'")


class RouteOption(BaseModel):
    """This is the unit the LLM actually generates per call."""
    path_name: str = Field(description="Theme/name of this route, e.g. 'The Historical Inland Route'")
    full_google_maps_url: str = Field(description="Google Maps URL with all overnight waypoints")
    daily_breakdown: List[DailyPlan] = Field(description="Day-by-day breakdown of the journey")
    why_it_fits: str = Field(description="Why this route fits the user's request")


class CustomTripItinerary(BaseModel):
    """Final assembled response. Built in Python, not generated in one LLM call."""
    trip_summary: str = Field(description="Brief overview of how the trip was customized")
    routes: List[RouteOption] = Field(description="The distinct route options")


# ---- Input schema: replaces the old input() calls, enables the API ----
class TripRequest(BaseModel):
    start_place: str = Field(examples=["Jaffna"])
    end_place: str = Field(examples=["Colombo"])
    start_date: str = Field(examples=["Dec 15, 2026"])
    duration: int = Field(ge=1, le=30, examples=[3])
    travelers: str = Field(examples=["2 adults, 2 children"])
    vibe: str = Field(examples=["historical and relaxed"])
    budget: str = Field(examples=["$100 total per night"])
    transport: str = Field(examples=["driving own car"])
    trip_description: str = Field(examples=["A scenic family road trip with cultural stops"])
    weather_preference: str = Field(default="", description="Any weather preferences/constraints, e.g. 'avoid rainy beach days, prefer cool weather'", examples=["prefer dry weather for outdoor activities"])
    amenities: List[str] = Field(default_factory=list, description="Must-have hotel amenities, e.g. ['Free WiFi', 'Pool']", examples=[["Free WiFi", "Breakfast"]])
