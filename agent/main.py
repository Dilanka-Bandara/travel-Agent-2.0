"""
FastAPI service. This is what you deploy and what aurelia-travel-backend calls
over the internet. Input validation is free (Pydantic TripRequest), and the
response is your rich CustomTripItinerary as JSON.

Run locally:   uvicorn app.api.main:app --reload --port 8000
Docs:          http://localhost:8000/docs
"""
import logging
from fastapi import FastAPI, HTTPException
from app.models.schemas import TripRequest, CustomTripItinerary
from app.services.trip_designer import design_trip

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="AI Multi-Day Trip Designer",
    version="1.0.0",
    description="Generates grounded, group-aware multi-day road-trip itineraries.",
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/design-trip", response_model=CustomTripItinerary)
def design_trip_endpoint(request: TripRequest):
    try:
        return design_trip(request)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    except Exception as exc:  # noqa: BLE001
        logging.exception("Unexpected failure")
        raise HTTPException(status_code=500, detail="Internal error generating trip.")
