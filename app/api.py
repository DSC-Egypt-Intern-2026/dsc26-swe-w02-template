"""HTTP layer for the Tawseel parcel service.

The HTTP layer translates requests into calls to app.domain; the domain decides.
See README.md for the four operations, their operationIds and their errors.
"""
from fastapi import FastAPI

from app.domain import EventType, InvalidTransition, Parcel, ParcelState, apply_event  # noqa: F401


def create_app() -> FastAPI:
    """Return a NEW FastAPI app with its own empty in-memory store.

    Tests call this once per test, so nothing may be shared between two apps
    (no module-level dicts or counters for parcels).
    """
    raise NotImplementedError


# `uvicorn app.api:app` needs a module-level app. Once create_app() works,
# replace the line below with:  app = create_app()
app = None
