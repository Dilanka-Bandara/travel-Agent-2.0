"""
CLI entry point. Preserves your original interactive experience for local use,
but now it just collects input into a TripRequest and calls the same service
the API uses -- so there is one source of truth.

Run:  python -m app.cli
"""
from app.models.schemas import TripRequest
from app.services.trip_designer import design_trip


def collect_request() -> TripRequest:
    print("\n🌍 Welcome to the AI Multi-Day Trip Designer!")
    print("-" * 70)
    return TripRequest(
        start_place=input("📍 Starting Point? (e.g., Jaffna): "),
        end_place=input("🏁 Final Destination? (e.g., Colombo): "),
        start_date=input("📅 Trip start date? (e.g., Dec 15, 2026): "),
        duration=int(input("⏳ How many days? (e.g., 3): ")),
        travelers=input("👥 Who is traveling? (e.g., 2 adults, 2 children): "),
        vibe=input("✨ Main vibe? (e.g., historical, relaxed): "),
        budget=input("💰 Hotel budget/night for the WHOLE GROUP? (e.g., $100 total): "),
        transport=input("🚗 Transport? (e.g., driving own car): "),
        trip_description=input("📝 Describe your dream trip: "),
    )


def print_itinerary(plan, req: TripRequest):
    print("\n" + "=" * 80)
    print(f"🗺️  YOUR {req.duration}-DAY CUSTOM TRAVEL PLAN")
    print(f"👥 Group: {req.travelers} | 📅 Starting: {req.start_date}")
    print("=" * 80)
    print(f"\n🤖 Overview: {plan.trip_summary}\n")

    for i, route in enumerate(plan.routes, 1):
        print("=" * 80)
        print(f"🌟 OPTION {i}: {route.path_name.upper()}")
        print(f"🗺️  Map: {route.full_google_maps_url}")
        print(f"✨ Why it fits: {route.why_it_fits}")
        print("-" * 80)
        for day in route.daily_breakdown:
            print(f"   📅 DAY {day.day_number} | Drive: {day.route_segment}")
            print("      🎯 Activities:")
            for act in day.activities:
                print(f"         - {act}")
            print(f"      🏨 Night Stay: {day.hotel_name}")
            print(f"      🛏️  Room Setup: {day.room_configuration}")
            print(f"      💰 Total Cost: {day.hotel_price}\n")


def main():
    req = collect_request()
    print("\n🤖 Pacing the trip, researching activities, checking accommodations...\n")
    plan = design_trip(req)
    print_itinerary(plan, req)


if __name__ == "__main__":
    main()
