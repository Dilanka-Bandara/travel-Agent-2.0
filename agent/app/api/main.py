"""
FastAPI service for the trip agent.

Endpoints:
  GET  /health                         -> liveness
  POST /design-trip                    -> SYNC (kept for testing; blocks until done)
  POST /design-trip/async              -> starts a job, returns {job_id} instantly
  GET  /design-trip/status/{job_id}    -> poll progress + result

The aurelia Node backend calls the async pair so long generations never time out.
"""
import logging
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware

from app.models.schemas import TripRequest, CustomTripItinerary
from app.services.trip_designer import design_trip
from app.services.jobs import job_store, run_trip_job

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="AI Multi-Day Trip Designer", version="1.1.0")

# Only the aurelia backend should call this; lock this down in production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5000", "http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/design-trip", response_model=CustomTripItinerary)
def design_trip_endpoint(request: TripRequest):
    """Synchronous — fine for CLI/testing, NOT used by the website."""
    try:
        return design_trip(request)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@app.post("/design-trip/async")
def design_trip_async(request: TripRequest, background: BackgroundTasks):
    """Start a background job; return its id immediately."""
    job = job_store.create()
    background.add_task(run_trip_job, job.id, request)
    return {"job_id": job.id, "status": "running"}


@app.get("/design-trip/status/{job_id}")
def design_trip_status(job_id: str):
    job = job_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "job_id": job.id,
        "status": job.status,
        "stage": job.stage,
        "progress": job.progress,
        "detail": job.detail,
        "result": job.result,
        "error": job.error,
    }
