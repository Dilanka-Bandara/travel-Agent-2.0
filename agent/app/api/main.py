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
import secrets
from typing import Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Header
from fastapi.middleware.cors import CORSMiddleware

from app.config.settings import get_settings
from app.models.schemas import TripRequest, CustomTripItinerary
from app.services.trip_designer import design_trip
from app.services.jobs import job_store, run_trip_job

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="AI Multi-Day Trip Designer", version="1.1.0")

# Only the aurelia backend should call this; origins come from CORS_ORIGINS.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in get_settings().cors_origins.split(",") if o.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)


def require_agent_key(x_agent_key: Optional[str] = Header(default=None)):
    """Reject callers that don't present the shared AGENT_API_KEY.
    If no key is configured (local testing), everything is allowed."""
    expected = get_settings().agent_api_key
    if expected and not (x_agent_key and secrets.compare_digest(x_agent_key, expected)):
        raise HTTPException(status_code=401, detail="Invalid or missing X-Agent-Key")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/design-trip", response_model=CustomTripItinerary, dependencies=[Depends(require_agent_key)])
def design_trip_endpoint(request: TripRequest):
    """Synchronous — fine for CLI/testing, NOT used by the website."""
    try:
        return design_trip(request)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@app.post("/design-trip/async", dependencies=[Depends(require_agent_key)])
def design_trip_async(request: TripRequest, background: BackgroundTasks):
    """Start a background job; return its id immediately."""
    job = job_store.create()
    background.add_task(run_trip_job, job.id, request)
    return {"job_id": job.id, "status": "running"}


@app.get("/design-trip/status/{job_id}", dependencies=[Depends(require_agent_key)])
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
