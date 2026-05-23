"""
Hotel data providers. Two real implementations behind one interface:

  - BookingProvider  -> RapidAPI's Booking.com data API (best Sri Lanka coverage)
  - AmadeusProvider  -> Amadeus Self-Service Hotel API (official, chain-heavy)

get_hotel_provider() reads HOTEL_PROVIDER from config and returns the right one.
Everything fails soft: any error returns an empty list, and the calling tool
falls back to web search. Both map their raw JSON into the shared HotelResult.

IMPORTANT: the exact JSON field names from these APIs change over time and by
endpoint. The mapping functions below are written defensively (.get with
fallbacks) and clearly marked so you can adjust field names after you see a
real response from your account. Run each provider once, print the raw JSON,
and tweak the _map_* function to match.
"""
import logging
from typing import List, Protocol
import httpx

from app.config.settings import get_settings
from app.models.hotel import HotelResult

logger = logging.getLogger(__name__)


class HotelProvider(Protocol):
    def search(self, town: str, check_in: str, check_out: str, adults: int) -> List[HotelResult]:
        ...


# ----------------------------------------------------------------------------
# RapidAPI Booking.com  (best Sri Lanka coverage)
# ----------------------------------------------------------------------------
class BookingProvider:
    """Uses a Booking.com data API hosted on RapidAPI.

    Booking.com search is two steps: (1) resolve the town name to a destination
    id, then (2) search hotels for that id + dates. Endpoint paths/hosts differ
    between the various RapidAPI Booking listings, so the host and paths are
    config-driven. Defaults match the common 'booking-com15' style listing.
    """

    def __init__(self):
        s = get_settings()
        self.key = s.rapidapi_key
        self.host = s.rapidapi_booking_host
        self.base = f"https://{self.host}"

    def _headers(self) -> dict:
        return {
            "x-rapidapi-key": self.key,
            "x-rapidapi-host": self.host,
        }

    def _resolve_destination(self, client: httpx.Client, town: str) -> str | None:
        # Step 1: town name -> destination id
        url = f"{self.base}/api/v1/hotels/searchDestination"
        resp = client.get(url, params={"query": town}, headers=self._headers())
        resp.raise_for_status()
        data = resp.json()
        items = data.get("data") or []
        if not items:
            return None
        # Prefer a city (not a region); among cities pick the one with most hotels.
        cities = [d for d in items if d.get("dest_type") == "city"]
        pool = cities or items
        best = max(pool, key=lambda d: d.get("nr_hotels", 0))
        return str(best.get("dest_id") or "")

    def search(self, town: str, check_in: str, check_out: str, adults: int) -> List[HotelResult]:
        if not self.key:
            logger.warning("RAPIDAPI_KEY missing; Booking provider returns nothing.")
            return []
        try:
            with httpx.Client(timeout=25) as client:
                dest_id = self._resolve_destination(client, f"{town}, Sri Lanka")
                if not dest_id:
                    return []

                # Step 2: search hotels
                url = f"{self.base}/api/v1/hotels/searchHotels"
                params = {
                    "dest_id": dest_id,
                    "search_type": "CITY",
                    "arrival_date": check_in,
                    "departure_date": check_out,
                    "adults": adults,
                    "currency_code": "USD",  # LKR is NOT supported by this API
                }
                resp = client.get(url, params=params, headers=self._headers())
                resp.raise_for_status()
                payload = resp.json()
        except httpx.HTTPError as exc:
            logger.warning("Booking provider failed for %s: %s", town, exc)
            return []

        return self._map(payload)

    @staticmethod
    def _map(payload: dict) -> List[HotelResult]:
        """Maps the real DataCrawler booking-com15 /searchHotels response.
        Confirmed shape: data.hotels[].property.{name, reviewScore, reviewCount,
        priceBreakdown.grossPrice.{value,currency}, strikethroughPrice, wishlistName}
        The per-hotel 'accessibilityLabel' carries a human room note we extract.
        """
        hotels = (payload.get("data") or {}).get("hotels") or []
        out: List[HotelResult] = []
        for h in hotels[:5]:
            prop = h.get("property", {})
            gross = (prop.get("priceBreakdown") or {}).get("grossPrice") or {}
            value = gross.get("value")
            currency = gross.get("currency")

            # Round the price for readability (API gives long floats like 33.30000001)
            price_str = None
            if value is not None:
                price_str = f"{currency} {round(float(value))}".strip()

            # Pull a short room note out of the accessibility label if present.
            room_note = None
            label = h.get("accessibilityLabel", "")
            for part in label.split("\n"):
                p = part.strip()
                if "bed" in p.lower() or "room" in p.lower():
                    room_note = p
                    break

            out.append(HotelResult(
                name=prop.get("name", "Unknown hotel"),
                price_per_night=price_str,
                currency=currency,
                rating=prop.get("reviewScore"),
                address=prop.get("wishlistName"),
                room_options=room_note,
                source="booking",
            ))
        return out


# ----------------------------------------------------------------------------
# Amadeus Self-Service  (official, free tier, chain-heavy)
# ----------------------------------------------------------------------------
class AmadeusProvider:
    """Amadeus needs an OAuth token first, then hotel-list by city, then offers."""

    def __init__(self):
        s = get_settings()
        self.client_id = s.amadeus_client_id
        self.client_secret = s.amadeus_client_secret
        # test host is free; switch to api.amadeus.com for production
        self.base = "https://test.api.amadeus.com"

    def _token(self, client: httpx.Client) -> str | None:
        resp = client.post(
            f"{self.base}/v1/security/oauth2/token",
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp.raise_for_status()
        return resp.json().get("access_token")

    def search(self, town: str, check_in: str, check_out: str, adults: int) -> List[HotelResult]:
        if not (self.client_id and self.client_secret):
            logger.warning("Amadeus creds missing; provider returns nothing.")
            return []
        try:
            with httpx.Client(timeout=25) as client:
                token = self._token(client)
                if not token:
                    return []
                auth = {"Authorization": f"Bearer {token}"}

                # Amadeus works by IATA city code; for SL most usable code is CMB (Colombo).
                # For broad coverage you'd geocode the town -> nearest code. Keep simple:
                city_code = "CMB"
                resp = client.get(
                    f"{self.base}/v1/reference-data/locations/hotels/by-city",
                    params={"cityCode": city_code},
                    headers=auth,
                )
                resp.raise_for_status()
                hotels = resp.json().get("data", [])[:5]
        except httpx.HTTPError as exc:
            logger.warning("Amadeus provider failed for %s: %s", town, exc)
            return []

        return [
            HotelResult(
                name=h.get("name", "Unknown hotel"),
                address=(h.get("address") or {}).get("countryCode"),
                source="amadeus",
            )
            for h in hotels
        ]


# ----------------------------------------------------------------------------
# Swap logic
# ----------------------------------------------------------------------------
def get_hotel_provider() -> HotelProvider | None:
    s = get_settings()
    provider = (s.hotel_provider or "").lower()
    if provider == "booking":
        return BookingProvider()
    if provider == "amadeus":
        return AmadeusProvider()
    return None  # disabled -> caller uses web search