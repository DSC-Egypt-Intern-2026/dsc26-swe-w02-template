import pytest
from fastapi.testclient import TestClient

from app.api import create_app
from app.domain import EventType, InvalidTransition, Parcel, ParcelState, apply_event


@pytest.fixture
def client():
    return TestClient(create_app())


def new_parcel(client, ref="ORD-1001", cod=25_000):
    r = client.post("/v1/parcels", json={
        "merchant_ref": ref, "cod_amount_piastres": cod,
        "address_text": "Behind the mosque near the bakery, Faisal, Giza",
    })
    assert r.status_code == 201, r.text
    return r.json()


def test_dispatch_then_deliver():
    p = Parcel(id="pcl_x", merchant_ref="ORD-1", cod_amount_piastres=0, address_text="Nasr City")
    p = apply_event(p, EventType.DISPATCH)
    assert (p.state, p.attempts) == (ParcelState.OUT_FOR_DELIVERY, 1)
    p = apply_event(p, EventType.DELIVER)
    assert p.state == ParcelState.DELIVERED


def test_delivered_parcel_cannot_fail():
    p = Parcel(id="pcl_x", merchant_ref="ORD-1", cod_amount_piastres=0,
               address_text="Nasr City", state=ParcelState.DELIVERED, attempts=1)
    with pytest.raises(InvalidTransition):
        apply_event(p, EventType.FAIL)


def test_create_returns_201_and_location(client):
    body = new_parcel(client)
    assert body["id"].startswith("pcl_")
    assert body["state"] == "created" and body["attempts"] == 0
    r = client.get(f"/v1/parcels/{body['id']}")
    assert r.status_code == 200 and r.json() == body


def test_unknown_parcel_is_a_problem_document(client):
    r = client.get("/v1/parcels/pcl_does_not_exist")
    assert r.status_code == 404
    assert r.headers["content-type"].startswith("application/problem+json")
    assert {"type", "title", "status"} <= r.json().keys()


def test_invalid_transition_is_409(client):
    p = new_parcel(client)
    r = client.post(f"/v1/parcels/{p['id']}/events", json={"type": "deliver"})
    assert r.status_code == 409
    assert r.json()["status"] == 409
