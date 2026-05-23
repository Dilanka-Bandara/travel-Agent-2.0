"""
A single normalized hotel shape that BOTH providers (RapidAPI Booking.com and
Amadeus) get mapped into. The rest of the app only ever sees HotelResult, so
the agent code never cares which provider the data came from. This is what
makes swapping providers a pure config change.
"""
from typing import Optional, List
from pydantic import BaseModel


class HotelResult(BaseModel):
    name: str
    price_per_night: Optional[str] = None     # kept as string, e.g. "LKR 12,000"
    currency: Optional[str] = None
    rating: Optional[float] = None
    address: Optional[str] = None
    room_options: Optional[str] = None        # free-text room/capacity note
    source: str = "unknown"                    # "booking" | "amadeus" | "web"

    def to_line(self) -> str:
        """One-line summary the LLM can read directly."""
        bits = [self.name]
        if self.price_per_night:
            bits.append(f"price: {self.price_per_night}")
        if self.rating:
            bits.append(f"rating: {self.rating}")
        if self.room_options:
            bits.append(f"rooms: {self.room_options}")
        bits.append(f"[{self.source}]")
        return " | ".join(bits)


def results_to_text(results: List[HotelResult]) -> str:
    if not results:
        return "No hotels found from the booking provider."
    return "\n".join(r.to_line() for r in results)
