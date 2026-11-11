from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier

from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.config import Settings
from app.database import SessionLocal
from app.geospatial import RouteEstimate, rank_available_drivers, record_driver_location
from app.main import create_user
from app.models import DispatchOffer, DriverPresence, DriverProfile, FraudRiskEvent, Trip, User
from app.schemas import DriverLocationRequest
from app.services import accept_offer


class TrafficFixtureRouting:
    """A deterministic fixture proving ranking uses ETA, not straight-line distance."""

    def estimate(
        self, origin_lat: float, origin_lon: float, destination_lat: float, destination_lon: float
    ) -> RouteEstimate:
        del origin_lon, destination_lat, destination_lon
        if origin_lat < 25.77:
            return RouteEstimate(1.0, 600, "TRAFFIC_FIXTURE", True)
        return RouteEstimate(2.0, 240, "TRAFFIC_FIXTURE", True)


def add_presence(driver_id: str, latitude: float, longitude: float, *, age_seconds: int = 0):
    observed_at = datetime.now(UTC) - timedelta(seconds=age_seconds)
    with SessionLocal() as session:
        session.add(
            DriverPresence(
                driver_id=driver_id,
                latitude=latitude,
                longitude=longitude,
                accuracy_meters=10,
                observed_at=observed_at,
                expires_at=datetime.now(UTC) + timedelta(minutes=5),
            )
        )
        session.commit()


def test_candidates_rank_by_road_eta_and_expand_radius(client: TestClient):
    del client
    with SessionLocal() as session:
        first = session.scalar(
            select(DriverProfile).join(User).where(User.email == "driver@example.test")
        )
        assert first is not None
        second_user = create_user(
            session,
            "driver2@example.test",
            "Second Driver",
            "demo-pass-123",
            approved_driver=True,
        )
        second = second_user.driver_profile
        assert second is not None
        first_id, second_id = first.id, second.id

    add_presence(first_id, 25.762, -80.1918)
    add_presence(second_id, 25.775, -80.1918)

    with SessionLocal() as session:
        ranked = rank_available_drivers(
            session,
            25.7617,
            -80.1918,
            routing_provider=TrafficFixtureRouting(),
        )
        assert [candidate.driver_id for candidate in ranked] == [second_id, first_id]
        assert all(candidate.search_radius_miles == 2 for candidate in ranked)

    with SessionLocal() as session:
        session.query(DriverPresence).delete()
        session.commit()
    add_presence(first_id, 25.805, -80.1918)
    with SessionLocal() as session:
        expanded = rank_available_drivers(session, 25.7617, -80.1918)
        assert len(expanded) == 1
        assert expanded[0].search_radius_miles == 5


def test_stale_and_inaccurate_locations_are_rejected(client: TestClient):
    del client
    with SessionLocal() as session:
        driver = session.scalar(
            select(DriverProfile).join(User).where(User.email == "driver@example.test")
        )
        assert driver is not None
        driver_id = driver.id
    add_presence(driver_id, 25.762, -80.1918, age_seconds=180)

    settings = Settings(driver_location_stale_seconds=90)
    with SessionLocal() as session:
        assert rank_available_drivers(session, 25.7617, -80.1918, settings=settings) == []

        user = session.scalar(select(User).where(User.email == "driver@example.test"))
        assert user is not None
        event, presence = record_driver_location(
            session,
            user,
            DriverLocationRequest(
                latitude=25.7617,
                longitude=-80.1918,
                accuracy_meters=250,
                observed_at=datetime.now(UTC),
            ),
            settings=settings,
        )
        assert presence is None
        assert event.anomaly_code == "LOW_ACCURACY"
        risk = session.scalar(select(FraudRiskEvent).where(FraudRiskEvent.actor_user_id == user.id))
        assert risk is not None


def test_coordinate_booking_creates_ranked_offer(
    client: TestClient, rider_auth: dict[str, str], driver_auth: dict[str, str]
):
    location = client.post(
        "/api/v1/driver/location",
        headers=driver_auth,
        json={
            "latitude": 25.768,
            "longitude": -80.198,
            "accuracy_meters": 12,
            "speed_mps": 0,
            "observed_at": datetime.now(UTC).isoformat(),
        },
    )
    assert location.status_code == 200, location.text
    assert location.json()["accepted"] is True

    booking = client.post(
        "/api/v1/bookings",
        headers={**rider_auth, "Idempotency-Key": "geospatial-booking-001"},
        json={
            "pickup_address": "100 Biscayne Boulevard",
            "destination_address": "Miami International Airport",
            "pickup_latitude": 25.7617,
            "pickup_longitude": -80.1918,
            "destination_latitude": 25.7959,
            "destination_longitude": -80.287,
            "accepted_fare_cents": 2200,
            "payment_method": "CASH",
            "payment_responsibility": "BOOKER",
        },
    )
    assert booking.status_code == 201, booking.text

    offers = client.get("/api/v1/driver/offers", headers=driver_auth)
    assert offers.status_code == 200
    assert len(offers.json()) == 1
    assert offers.json()[0]["pickup_eta_seconds"] > 0
    assert offers.json()[0]["expected_earnings_cents"] == 1760


def test_offer_rejection_recovers_to_next_ranked_driver(
    client: TestClient, rider_auth: dict[str, str], driver_auth: dict[str, str]
):
    with SessionLocal() as session:
        first = session.scalar(
            select(DriverProfile).join(User).where(User.email == "driver@example.test")
        )
        assert first is not None
        second_user = create_user(
            session,
            "recovery-driver@example.test",
            "Recovery Driver",
            "demo-pass-123",
            approved_driver=True,
        )
        second = second_user.driver_profile
        assert second is not None
        first_id, second_id = first.id, second.id
    add_presence(first_id, 25.762, -80.1918)
    add_presence(second_id, 25.77, -80.1918)

    booking = client.post(
        "/api/v1/bookings",
        headers={**rider_auth, "Idempotency-Key": "dispatch-recovery-001"},
        json={
            "pickup_address": "Downtown Miami",
            "destination_address": "Miami Airport",
            "pickup_latitude": 25.7617,
            "pickup_longitude": -80.1918,
            "destination_latitude": 25.7959,
            "destination_longitude": -80.287,
            "accepted_fare_cents": 2200,
            "payment_method": "CASH",
            "payment_responsibility": "BOOKER",
        },
    )
    assert booking.status_code == 201
    first_offers = client.get("/api/v1/driver/offers", headers=driver_auth).json()
    assert len(first_offers) == 1

    rejected = client.post(
        f"/api/v1/driver/offers/{first_offers[0]['id']}/reject",
        headers=driver_auth,
    )
    assert rejected.status_code == 204

    second_login = client.post(
        "/api/v1/auth/login",
        json={"email": "recovery-driver@example.test", "password": "demo-pass-123"},
    )
    second_auth = {"Authorization": f"Bearer {second_login.json()['access_token']}"}
    second_offers = client.get("/api/v1/driver/offers", headers=second_auth)
    assert second_offers.status_code == 200
    assert len(second_offers.json()) == 1
    assert second_offers.json()[0]["trip_id"] == booking.json()["id"]


def test_concurrent_offer_acceptance_assigns_exactly_one_driver(
    client: TestClient, rider_auth: dict[str, str]
):
    with SessionLocal() as session:
        first_user = session.scalar(select(User).where(User.email == "driver@example.test"))
        assert first_user is not None and first_user.driver_profile is not None
        second_user = create_user(
            session,
            "concurrent-driver@example.test",
            "Concurrent Driver",
            "demo-pass-123",
            approved_driver=True,
        )
        assert second_user.driver_profile is not None

    booking = client.post(
        "/api/v1/bookings",
        headers={**rider_auth, "Idempotency-Key": "concurrent-accept-001"},
        json={
            "pickup_address": "100 Main Street",
            "destination_address": "200 Oak Avenue",
            "accepted_fare_cents": 1800,
            "payment_method": "CASH",
            "payment_responsibility": "BOOKER",
        },
    )
    assert booking.status_code == 201
    with SessionLocal() as session:
        offers = list(
            session.scalars(
                select(DispatchOffer).where(DispatchOffer.trip_id == booking.json()["id"])
            )
        )
        assert len(offers) == 2
        attempts: list[tuple[str, str]] = []
        for offer in offers:
            driver = session.get(DriverProfile, offer.driver_id)
            assert driver is not None
            attempts.append((driver.user_id, offer.id))

    barrier = Barrier(2)

    def attempt(user_id: str, offer_id: str) -> int:
        with SessionLocal() as session:
            user = session.get(User, user_id)
            assert user is not None
            barrier.wait()
            try:
                accept_offer(session, user, offer_id)
                return 200
            except HTTPException as exc:
                return exc.status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = list(
            pool.map(
                lambda args: attempt(*args),
                attempts,
            )
        )
    assert sorted(statuses) == [200, 409]
    with SessionLocal() as session:
        trip = session.get(Trip, booking.json()["id"])
        assert trip is not None
        assert trip.state == "ASSIGNED"
        assert trip.assigned_driver_id is not None
        competing_states = list(
            session.scalars(
                select(DriverProfile.availability).where(
                    DriverProfile.id != trip.assigned_driver_id
                )
            )
        )
        assert "OFFER_PENDING" not in competing_states
