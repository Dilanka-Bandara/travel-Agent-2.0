"""
Tests for the deterministic parts -- the bits that must NEVER depend on an LLM.
These run instantly with no model, and protect the reliability-critical logic.
Run:  pytest -q
"""
from app.tools.maps import build_maps_url
from app.models.schemas import RouteOption, DailyPlan
from app.services.trip_designer import _waypoints_from_route


def test_map_url_is_well_formed():
    url = build_maps_url("Jaffna", ["Anuradhapura", "Kandy"], "Colombo")
    assert url.startswith("https://www.google.com/maps/dir/")
    assert "Anuradhapura" in url and "Kandy" in url
    assert " " not in url  # spaces must be encoded


def test_map_url_handles_empty_waypoints():
    url = build_maps_url("Jaffna", [], "Colombo")
    assert url == "https://www.google.com/maps/dir/Jaffna/Colombo"


def test_waypoints_extracted_from_segments():
    route = RouteOption(
        path_name="Test",
        full_google_maps_url="",
        why_it_fits="x",
        daily_breakdown=[
            DailyPlan(day_number=1, route_segment="Jaffna to Anuradhapura",
                      activities=["a"], hotel_name="H", room_configuration="r", hotel_price="$1"),
            DailyPlan(day_number=2, route_segment="Anuradhapura to Colombo",
                      activities=["b"], hotel_name="H", room_configuration="r", hotel_price="$1"),
        ],
    )
    # last day is the final destination, so only the first day's arrival is a waypoint
    assert _waypoints_from_route(route) == ["Anuradhapura"]
