import hashlib
import os

from fastapi import FastAPI, Header, HTTPException
from mangum import Mangum

from .models import Reading
from .store import InMemoryStore

app = FastAPI(title="Sammy Telemetry API", version="0.1.0")
store = InMemoryStore()


def hash_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


# Local dev: register one device from env vars so you can test without a database.
if os.environ.get("DEV_DEVICE_KEY"):
    store.register_device(
        os.environ.get("DEV_DEVICE_ID", "dev-car"),
        hash_key(os.environ["DEV_DEVICE_KEY"]),
    )


def authenticate(x_device_key: str | None) -> str:
    """Return the device_id that owns this key, or reject with 401."""
    if not x_device_key:
        raise HTTPException(status_code=401, detail="missing device key")
    device_id = store.device_for_key_hash(hash_key(x_device_key))
    if device_id is None:
        raise HTTPException(status_code=401, detail="unknown device key")
    return device_id


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/telemetry", status_code=202)
def post_telemetry(
    body: Reading | list[Reading],
    x_device_key: str | None = Header(default=None),
):
    device_id = authenticate(x_device_key)
    readings = body if isinstance(body, list) else [body]
    # A device may only post its own readings.
    if any(r.device_id != device_id for r in readings):
        raise HTTPException(status_code=403, detail="device_id does not match key")
    store.save(readings)
    return {"accepted": len(readings)}


@app.get("/vehicles/{device_id}/location")
def get_location(device_id: str):
    r = store.latest(device_id)
    if r is None:
        raise HTTPException(status_code=404, detail="no readings")
    # Shaped loosely like Samsara's vehicle location response
    return {
        "data": {
            "id": device_id,
            "location": {
                "time": r.ts.isoformat(),
                "latitude": r.lat,
                "longitude": r.lon,
                "speedMph": r.speed_mph,
            },
        }
    }


@app.get("/vehicles/{device_id}/faults")
def get_faults(device_id: str, limit: int = 20):
    faults = store.recent_faults(device_id, limit)
    return {
        "data": {
            "id": device_id,
            "faults": [{"time": r.ts.isoformat(), "codes": r.fault_codes} for r in faults],
        }
    }


handler = Mangum(app)  # Lambda entry point (used from Day 2)