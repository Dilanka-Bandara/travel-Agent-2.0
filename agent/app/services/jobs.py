"""
Async job support for the agent.

The trip generation takes minutes (especially on local hardware), which is far
longer than a normal HTTP request survives. So instead of making the caller wait
on one request, we:

  1. POST /design-trip/async  -> starts a background job, returns {job_id} instantly
  2. GET  /design-trip/status/{job_id} -> returns progress + result when ready

Progress is REAL: the trip designer updates the job's stage as it actually works
through planning -> hotels -> weather -> assembling, so the frontend animation
reflects what's truly happening, not a fake timer.

This uses a simple in-memory dict, which is fine for a single-process service.
For multi-worker production you'd swap this for Redis (which aurelia already
uses) -- the interface is small and easy to move.
"""
import uuid
import threading
import logging
from dataclasses import dataclass, field
from typing import Optional, Dict, List

from app.models.schemas import TripRequest, CustomTripItinerary

logger = logging.getLogger(__name__)

# Ordered stages the frontend animates through.
STAGES = ["planning", "hotels", "weather", "assembling", "done"]


@dataclass
class Job:
    id: str
    status: str = "running"          # running | done | error
    stage: str = "planning"          # one of STAGES
    progress: int = 0                # 0-100
    detail: str = "Starting..."      # human-readable current action
    result: Optional[dict] = None    # CustomTripItinerary as dict when done
    error: Optional[str] = None


class JobStore:
    def __init__(self):
        self._jobs: Dict[str, Job] = {}
        self._lock = threading.Lock()

    def create(self) -> Job:
        job = Job(id=str(uuid.uuid4()))
        with self._lock:
            self._jobs[job.id] = job
        return job

    def get(self, job_id: str) -> Optional[Job]:
        with self._lock:
            return self._jobs.get(job_id)

    def update(self, job_id: str, **kwargs):
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            for k, v in kwargs.items():
                setattr(job, k, v)


job_store = JobStore()


def run_trip_job(job_id: str, req: TripRequest):
    """Runs in a background thread. Imports here to avoid heavy imports at module load."""
    from app.services.trip_progress import design_trip_with_progress

    def on_progress(stage: str, progress: int, detail: str):
        job_store.update(job_id, stage=stage, progress=progress, detail=detail)

    try:
        itinerary: CustomTripItinerary = design_trip_with_progress(req, on_progress)
        job_store.update(
            job_id, status="done", stage="done", progress=100,
            detail="Your itinerary is ready.",
            result=itinerary.model_dump(),
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Trip job %s failed", job_id)
        job_store.update(job_id, status="error", error=str(exc),
                         detail="Generation failed.")
