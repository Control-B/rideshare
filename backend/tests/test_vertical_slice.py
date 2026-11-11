from fastapi.testclient import TestClient


def test_guest_cash_trip_end_to_end(
    client: TestClient, rider_auth: dict[str, str], driver_auth: dict[str, str]
):
    quote = client.post(
        "/api/v1/quotes",
        headers=rider_auth,
        json={
            "pickup_address": "100 Main Street",
            "destination_address": "200 Oak Avenue",
            "estimated_miles": 6.2,
            "estimated_minutes": 18,
        },
    )
    assert quote.status_code == 200
    assert quote.json()["fare_cents"] > 700

    booking_payload = {
        "pickup_address": "100 Main Street",
        "destination_address": "200 Oak Avenue",
        "accepted_fare_cents": quote.json()["fare_cents"],
        "payment_method": "CASH",
        "for_someone_else": True,
        "guest_passenger_name": "Morgan Guest",
        "guest_passenger_phone": "+15555550100",
        "guest_communication_consent": True,
        "payment_responsibility": "PASSENGER",
    }
    booking = client.post(
        "/api/v1/bookings",
        headers={**rider_auth, "Idempotency-Key": "test-booking-001"},
        json=booking_payload,
    )
    assert booking.status_code == 201, booking.text
    trip_id = booking.json()["id"]
    assert booking.json()["guest_passenger_name"] == "Morgan Guest"

    duplicate = client.post(
        "/api/v1/bookings",
        headers={**rider_auth, "Idempotency-Key": "test-booking-001"},
        json=booking_payload,
    )
    assert duplicate.status_code == 201
    assert duplicate.json()["id"] == trip_id

    offers = client.get("/api/v1/driver/offers", headers=driver_auth)
    assert offers.status_code == 200
    assert len(offers.json()) == 1

    accepted = client.post(
        f"/api/v1/driver/offers/{offers.json()[0]['id']}/accept", headers=driver_auth
    )
    assert accepted.status_code == 200
    assert accepted.json()["state"] == "ASSIGNED"

    stale_accept = client.post(
        f"/api/v1/driver/offers/{offers.json()[0]['id']}/accept", headers=driver_auth
    )
    assert stale_accept.status_code == 409

    for state in ["DRIVER_EN_ROUTE", "DRIVER_ARRIVED", "IN_PROGRESS"]:
        transition = client.post(
            f"/api/v1/trips/{trip_id}/transition",
            headers=driver_auth,
            json={"new_state": state},
        )
        assert transition.status_code == 200, transition.text

    missing_cash = client.post(
        f"/api/v1/trips/{trip_id}/transition",
        headers=driver_auth,
        json={"new_state": "COMPLETED", "cash_collected": False},
    )
    assert missing_cash.status_code == 422

    completed = client.post(
        f"/api/v1/trips/{trip_id}/transition",
        headers=driver_auth,
        json={"new_state": "COMPLETED", "cash_collected": True},
    )
    assert completed.status_code == 200
    assert completed.json()["state"] == "COMPLETED"

    cash = client.get(f"/api/v1/trips/{trip_id}/cash", headers=rider_auth)
    assert cash.status_code == 200
    assert cash.json() == {
        "trip_id": trip_id,
        "amount_cents": quote.json()["fare_cents"],
        "status": "REPORTED_COLLECTED",
    }


def test_rider_cannot_use_driver_api(client: TestClient, rider_auth: dict[str, str]):
    profile = client.get("/api/v1/me", headers=rider_auth)
    assert profile.status_code == 200
    assert profile.json()["full_name"] == "Banjah"

    response = client.get("/api/v1/driver/offers", headers=rider_auth)
    assert response.status_code == 403


def test_driver_onboarding_does_not_grant_approval(client: TestClient, rider_auth: dict[str, str]):
    response = client.post("/api/v1/driver/onboarding", headers=rider_auth)
    assert response.status_code == 200
    assert response.json()["driver_approved"] is False
    assert "DRIVER_APPLICANT" in response.json()["roles"]


def test_authenticated_realtime_connection(client: TestClient, rider_auth: dict[str, str]):
    token = rider_auth["Authorization"].removeprefix("Bearer ")
    with client.websocket_connect(f"/api/v1/realtime?token={token}") as websocket:
        assert websocket.receive_json() == {"type": "CONNECTED"}
        websocket.send_text("ping")
        assert websocket.receive_json() == {"type": "pong"}
