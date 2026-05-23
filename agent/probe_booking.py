"""
probe_booking.py  --  run this ONCE after you have a RapidAPI key.

It does the two-step Booking.com flow (resolve destination -> search hotels)
and prints the RAW JSON so we can confirm the exact field names, then fix the
_map() function in hotel_providers.py to match your account's response.

USAGE (PowerShell):
    setx RAPIDAPI_KEY "your_key_here"     # then open a NEW terminal
    python probe_booking.py

Or just paste your key into the KEY variable below temporarily (don't commit it).
"""
import os
import json
import httpx

# --- config ---
KEY = os.environ.get("RAPIDAPI_KEY", "PASTE_YOUR_KEY_HERE")
HOST = "booking-com15.p.rapidapi.com"   # change if you subscribed to a different listing
BASE = f"https://{HOST}"

TOWN = "Kandy, Sri Lanka"
ARRIVAL = "2026-07-01"
DEPARTURE = "2026-07-02"
ADULTS = 2

HEADERS = {"x-rapidapi-key": KEY, "x-rapidapi-host": HOST}


def main():
    if KEY in ("", "PASTE_YOUR_KEY_HERE"):
        print("❌ Set RAPIDAPI_KEY env var or paste your key into the script first.")
        return

    with httpx.Client(timeout=30) as client:
        # Step 1: resolve town -> destination id
        print("=== STEP 1: searchDestination ===")
        r1 = client.get(
            f"{BASE}/api/v1/hotels/searchDestination",
            params={"query": TOWN},
            headers=HEADERS,
        )
        print("status:", r1.status_code)
        dest = r1.json()
        print(json.dumps(dest, indent=2)[:2000])  # first chunk only

        items = dest.get("data") or []
        if not items:
            print("⚠️ No destination found. Inspect the JSON above for the right field.")
            return
        # Prefer a city (not a region), and among cities the one with most hotels.
        cities = [d for d in items if d.get("dest_type") == "city"]
        pool = cities or items
        best = max(pool, key=lambda d: d.get("nr_hotels", 0))
        dest_id = best.get("dest_id")
        print(f"\n>>> Using dest_id: {dest_id} ({best.get('label')}, {best.get('nr_hotels')} hotels)")

        # Step 2: search hotels
        print("\n=== STEP 2: searchHotels ===")
        r2 = client.get(
            f"{BASE}/api/v1/hotels/searchHotels",
            params={
                "dest_id": dest_id,
                "search_type": "CITY",
                "arrival_date": ARRIVAL,
                "departure_date": DEPARTURE,
                "adults": ADULTS,
                "currency_code": "USD",
            },
            headers=HEADERS,
        )
        print("status:", r2.status_code)
        hotels = r2.json()
        # Print enough structure to see the field names for ONE hotel
        print(json.dumps(hotels, indent=2)[:3500])
        print("\n✅ Copy the output above and send it back to fix the mapping.")


if __name__ == "__main__":
    main()