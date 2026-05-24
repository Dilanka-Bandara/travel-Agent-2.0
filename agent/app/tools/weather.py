"""
Weather grounding via Open-Meteo (free, no API key).

Two steps, both keyless:
  1. Geocoding API: town name -> latitude/longitude
  2. Forecast API: lat/lon + date -> daily min/max temp, rain, condition

Open-Meteo forecasts reach ~16 days ahead. If the trip date is beyond that
horizon we say so honestly rather than inventing a forecast -- this matters for
a real product (don't pretend to forecast 3 months out).

WMO weather codes are translated to plain English so the LLM gets readable text.
"""
import logging
from datetime import date, datetime
from typing import Optional

import httpx
from crewai.tools import tool

logger = logging.getLogger(__name__)

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
MAX_FORECAST_DAYS = 16

# Minimal WMO weather-code -> description map (the codes the API returns)
WMO = {
    0: "clear sky", 1: "mainly clear", 2: "partly cloudy", 3: "overcast",
    45: "fog", 48: "rime fog",
    51: "light drizzle", 53: "drizzle", 55: "heavy drizzle",
    61: "light rain", 63: "rain", 65: "heavy rain",
    66: "freezing rain", 67: "heavy freezing rain",
    71: "light snow", 73: "snow", 75: "heavy snow",
    80: "light showers", 81: "showers", 82: "violent showers",
    95: "thunderstorm", 96: "thunderstorm with hail", 99: "severe thunderstorm with hail",
}


def _geocode(client: httpx.Client, town: str) -> Optional[tuple]:
    resp = client.get(GEOCODE_URL, params={"name": town, "count": 1})
    resp.raise_for_status()
    results = resp.json().get("results") or []
    if not results:
        return None
    r = results[0]
    return r["latitude"], r["longitude"], r.get("name", town)


def _days_ahead(target: str) -> Optional[int]:
    try:
        d = datetime.strptime(target, "%Y-%m-%d").date()
    except ValueError:
        return None
    return (d - date.today()).days


@tool("Weather Forecast")
def weather_forecast(town: str, day: str) -> str:
    """Get the weather forecast for a Sri Lankan town on a specific date.
    'day' must be YYYY-MM-DD. Returns temperature range, rain chance, and a
    plain-English condition. Use this to judge whether outdoor activities suit
    the day, and to warn the traveler about rain or heat."""
    ahead = _days_ahead(day)
    if ahead is None:
        return f"Invalid date '{day}'. Use YYYY-MM-DD."
    if ahead < 0:
        return f"{day} is in the past; no forecast."
    if ahead > MAX_FORECAST_DAYS:
        return (f"{day} is {ahead} days away — beyond the 16-day forecast horizon. "
                f"Use seasonal/monsoon knowledge for {town} instead of a live forecast.")

    try:
        with httpx.Client(timeout=20) as client:
            geo = _geocode(client, f"{town}, Sri Lanka")
            if not geo:
                return f"Could not locate {town} for weather."
            lat, lon, resolved = geo

            resp = client.get(FORECAST_URL, params={
                "latitude": lat, "longitude": lon,
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max,weather_code",
                "timezone": "auto",
                "start_date": day, "end_date": day,
            })
            resp.raise_for_status()
            daily = resp.json().get("daily", {})
    except httpx.HTTPError as exc:
        logger.warning("Weather lookup failed for %s: %s", town, exc)
        return f"Weather unavailable for {town} ({exc})."

    if not daily.get("time"):
        return f"No forecast data for {town} on {day}."

    tmax = daily["temperature_2m_max"][0]
    tmin = daily["temperature_2m_min"][0]
    rain_mm = daily["precipitation_sum"][0]
    rain_pct = daily.get("precipitation_probability_max", [None])[0]
    code = daily["weather_code"][0]
    condition = WMO.get(code, "unknown")

    rain_note = f"{rain_pct}% chance" if rain_pct is not None else f"{rain_mm} mm"
    return (f"{resolved} on {day}: {condition}, "
            f"{round(tmin)}-{round(tmax)}°C, rain {rain_note}.")
