import pytest
from fastapi.testclient import TestClient

from app import main

KEY = {"X-Device-Key": "test-key"}
client = TestClient(main.app)


@pytest.fixture(autouse=True)
def fresh_store():
    main.store.reset()
    main.store.register_device("car1", main.hash_key("test-key"))


def reading(ts="2026-11-23T12:00:00Z", device_id="car1", **extra):
    return {"device_id": device_id, "ts": ts, "lat": 27.95, "lon": -82.46, **extra}


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_rejects_missing_or_bad_key():
    assert client.post("/telematics", json=reading()).status_code == 401
    bad = {"X-Device-Key": "wrong"}
    assert client.post("/telematics", json=reading(), headers=bad).status_code == 401


def test_single_reading_then_location():
    r = client.post("/telematics", json=reading(speed_mph=35), headers=KEY)
    assert r.status_code == 202
    loc = client.get("/vehicles/car1/location").json()["data"]["location"]
    assert loc["latitude"] == 27.95 and loc["speedMph"] == 35


def test_batch_returns_latest():
    batch = [reading("2026-11-23T12:00:00Z"), reading("2026-11-23T12:05:00Z", lat=28.0)]
    r = client.post("/telematics", json=batch, headers=KEY)
    assert r.json() == {"accepted": 2}
    loc = client.get("/vehicles/car1/location").json()["data"]["location"]
    assert loc["latitude"] == 28.0


def test_cannot_post_for_another_device():
    r = client.post("/telematics", json=reading(device_id="car2"), headers=KEY)
    assert r.status_code == 403


def test_faults_and_unknown_vehicle():
    client.post("/telematics", json=reading(fault_codes=["P0301"]), headers=KEY)
    faults = client.get("/vehicles/car1/faults").json()["data"]["faults"]
    assert faults[0]["codes"] == ["P0301"]
    assert client.get("/vehicles/nope/location").status_code == 404