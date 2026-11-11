import json
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.config import get_settings
from app.geospatial import point_in_active_service_zone, rank_available_drivers
from app.models import (
    CashCollection,
    DispatchCandidate,
    DispatchOffer,
    DriverProfile,
    DriverState,
    LedgerEntry,
    PaymentMethod,
    RideRequest,
    Trip,
    TripEvent,
    TripState,
    User,
    new_id,
)
from app.schemas import BookingRequest, QuoteRequest, TripView

ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    TripState.SEARCHING.value: {TripState.ASSIGNED.value, TripState.CANCELLED.value},
    TripState.ASSIGNED.value: {TripState.DRIVER_EN_ROUTE.value, TripState.CANCELLED.value},
    TripState.DRIVER_EN_ROUTE.value: {
        TripState.DRIVER_ARRIVED.value,
        TripState.CANCELLED.value,
    },
    TripState.DRIVER_ARRIVED.value: {
        TripState.IN_PROGRESS.value,
        TripState.CANCELLED.value,
    },
    TripState.IN_PROGRESS.value: {TripState.COMPLETED.value},
}


def calculate_quote(request: QuoteRequest) -> tuple[int, dict[str, int]]:
    base = 250
    distance = round(request.estimated_miles * 165)
    time = request.estimated_minutes * 35
    subtotal = base + distance + time
    service_fee = round(subtotal * 0.08)
    total = max(700, subtotal + service_fee)
    return total, {
        "base_fare": base,
        "distance": distance,
        "time": time,
        "service_fee": service_fee,
    }


def to_trip_view(trip: Trip) -> TripView:
    request = trip.ride_request
    return TripView(
        id=trip.id,
        state=trip.state,
        version=trip.version,
        assigned_driver_id=trip.assigned_driver_id,
        pickup_address=request.pickup_address,
        destination_address=request.destination_address,
        fare_cents=request.accepted_fare_cents,
        payment_method=request.payment_method,
        guest_passenger_name=request.guest_passenger_name,
        events=trip.events,
    )


def trip_query():
    return select(Trip).options(selectinload(Trip.ride_request), selectinload(Trip.events))


def create_booking(
    session: Session, user: User, payload: BookingRequest, idempotency_key: str
) -> Trip:
    existing = session.scalar(
        trip_query()
        .join(Trip.ride_request)
        .where(
            RideRequest.booker_user_id == user.id,
            RideRequest.idempotency_key == idempotency_key,
        )
    )
    if existing:
        return existing

    ride_request = RideRequest(
        booker_user_id=user.id,
        passenger_user_id=None if payload.for_someone_else else user.id,
        guest_passenger_name=payload.guest_passenger_name if payload.for_someone_else else None,
        guest_passenger_phone=payload.guest_passenger_phone if payload.for_someone_else else None,
        payer_user_id=user.id if payload.payment_responsibility == "BOOKER" else None,
        payment_responsibility=payload.payment_responsibility,
        pickup_address=payload.pickup_address,
        destination_address=payload.destination_address,
        pickup_latitude=payload.pickup_latitude,
        pickup_longitude=payload.pickup_longitude,
        destination_latitude=payload.destination_latitude,
        destination_longitude=payload.destination_longitude,
        payment_method=payload.payment_method.value,
        accepted_fare_cents=payload.accepted_fare_cents,
        idempotency_key=idempotency_key,
    )
    trip = Trip(ride_request=ride_request, state=TripState.SEARCHING.value)
    session.add_all([ride_request, trip])
    session.flush()
    event = TripEvent(
        trip_id=trip.id,
        previous_state=None,
        new_state=TripState.SEARCHING.value,
        actor_user_id=user.id,
        correlation_id=idempotency_key,
        version=1,
    )
    session.add(event)

    settings = get_settings()
    offered_driver_ids: list[str] = []
    if payload.pickup_latitude is not None and payload.pickup_longitude is not None:
        if not point_in_active_service_zone(
            session, payload.pickup_latitude, payload.pickup_longitude
        ):
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                "Pickup is outside an active, compliance-reviewed service zone",
            )
        ranked = rank_available_drivers(
            session,
            payload.pickup_latitude,
            payload.pickup_longitude,
            excluded_user_id=user.id,
            settings=settings,
        )
        for rank, candidate in enumerate(ranked, start=1):
            session.add(
                DispatchCandidate(
                    trip_id=trip.id,
                    driver_id=candidate.driver_id,
                    search_radius_miles=candidate.search_radius_miles,
                    straight_line_miles=candidate.straight_line_miles,
                    road_distance_miles=candidate.road_distance_miles,
                    pickup_eta_seconds=candidate.pickup_eta_seconds,
                    score=candidate.score,
                    rank=rank,
                    routing_provider=candidate.routing_provider,
                )
            )
        offered_driver_ids = [
            candidate.driver_id for candidate in ranked[: settings.dispatch_offer_group_size]
        ]
    else:
        eligible_drivers = session.scalars(
            select(DriverProfile).where(
                DriverProfile.approved.is_(True),
                DriverProfile.availability == DriverState.AVAILABLE.value,
                DriverProfile.user_id != user.id,
            )
        ).all()
        offered_driver_ids = [driver.id for driver in eligible_drivers]

    expires_at = datetime.now(UTC) + timedelta(seconds=settings.dispatch_offer_seconds)
    for driver_id in offered_driver_ids:
        session.add(DispatchOffer(trip_id=trip.id, driver_id=driver_id, expires_at=expires_at))
        driver = session.get(DriverProfile, driver_id)
        if driver:
            driver.availability = DriverState.OFFER_PENDING.value
    session.commit()
    return session.scalar(trip_query().where(Trip.id == trip.id))  # type: ignore[return-value]


def accept_offer(session: Session, user: User, offer_id: str) -> Trip:
    driver = session.scalar(select(DriverProfile).where(DriverProfile.user_id == user.id))
    if not driver or not driver.approved:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Approved driver profile required")

    offer = session.scalar(
        select(DispatchOffer).where(
            DispatchOffer.id == offer_id, DispatchOffer.driver_id == driver.id
        )
    )
    if not offer or offer.status != "PENDING":
        raise HTTPException(status.HTTP_409_CONFLICT, "Offer is no longer available")
    expires_at = offer.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at < datetime.now(UTC):
        offer.status = "EXPIRED"
        driver.availability = DriverState.AVAILABLE.value
        issue_next_candidate_offer(session, offer.trip_id)
        session.commit()
        raise HTTPException(status.HTTP_409_CONFLICT, "Offer expired")
    if driver.availability not in {
        DriverState.AVAILABLE.value,
        DriverState.OFFER_PENDING.value,
    }:
        raise HTTPException(status.HTTP_409_CONFLICT, "Driver is not available")

    result = session.execute(
        update(Trip)
        .where(
            Trip.id == offer.trip_id,
            Trip.state == TripState.SEARCHING.value,
            Trip.assigned_driver_id.is_(None),
        )
        .values(
            state=TripState.ASSIGNED.value,
            assigned_driver_id=driver.id,
            version=Trip.version + 1,
        )
    )
    if result.rowcount != 1:
        session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Trip was assigned to another driver")

    trip = session.get(Trip, offer.trip_id)
    assert trip is not None
    offer.status = "ACCEPTED"
    driver.availability = DriverState.ASSIGNED.value
    competing_driver_ids = list(
        session.scalars(
            select(DispatchOffer.driver_id).where(
                DispatchOffer.trip_id == trip.id,
                DispatchOffer.id != offer.id,
                DispatchOffer.status == "PENDING",
            )
        )
    )
    session.execute(
        update(DispatchOffer)
        .where(
            DispatchOffer.trip_id == trip.id,
            DispatchOffer.id != offer.id,
            DispatchOffer.status == "PENDING",
        )
        .values(status="REJECTED")
    )
    if competing_driver_ids:
        session.execute(
            update(DriverProfile)
            .where(
                DriverProfile.id.in_(competing_driver_ids),
                DriverProfile.availability == DriverState.OFFER_PENDING.value,
            )
            .values(availability=DriverState.AVAILABLE.value)
        )
    session.add(
        TripEvent(
            trip_id=trip.id,
            previous_state=TripState.SEARCHING.value,
            new_state=TripState.ASSIGNED.value,
            actor_user_id=user.id,
            correlation_id=new_id(),
            version=trip.version,
        )
    )
    session.commit()
    return session.scalar(trip_query().where(Trip.id == trip.id))  # type: ignore[return-value]


def issue_next_candidate_offer(session: Session, trip_id: str) -> DispatchOffer | None:
    trip = session.get(Trip, trip_id)
    if not trip or trip.state != TripState.SEARCHING.value or trip.assigned_driver_id:
        return None
    previously_offered = set(
        session.scalars(select(DispatchOffer.driver_id).where(DispatchOffer.trip_id == trip_id))
    )
    candidate = session.scalar(
        select(DispatchCandidate)
        .join(DriverProfile, DispatchCandidate.driver_id == DriverProfile.id)
        .where(
            DispatchCandidate.trip_id == trip_id,
            DispatchCandidate.driver_id.not_in(previously_offered),
            DriverProfile.approved.is_(True),
            DriverProfile.availability == DriverState.AVAILABLE.value,
        )
        .order_by(DispatchCandidate.rank)
    )
    if not candidate:
        return None
    driver = session.get(DriverProfile, candidate.driver_id)
    assert driver is not None
    driver.availability = DriverState.OFFER_PENDING.value
    offer = DispatchOffer(
        trip_id=trip_id,
        driver_id=driver.id,
        expires_at=datetime.now(UTC) + timedelta(seconds=get_settings().dispatch_offer_seconds),
    )
    session.add(offer)
    return offer


def recover_expired_offers(session: Session) -> list[Trip]:
    now = datetime.now(UTC)
    expired = list(
        session.scalars(
            select(DispatchOffer).where(
                DispatchOffer.status == "PENDING",
                DispatchOffer.expires_at < now,
            )
        )
    )
    trip_ids: set[str] = set()
    for offer in expired:
        offer.status = "EXPIRED"
        driver = session.get(DriverProfile, offer.driver_id)
        if driver and driver.availability == DriverState.OFFER_PENDING.value:
            driver.availability = DriverState.AVAILABLE.value
        trip_ids.add(offer.trip_id)
    session.flush()
    for trip_id in trip_ids:
        issue_next_candidate_offer(session, trip_id)
    if trip_ids:
        session.commit()
    return [
        trip
        for trip_id in trip_ids
        if (trip := session.scalar(trip_query().where(Trip.id == trip_id)))
    ]


def reject_offer(session: Session, user: User, offer_id: str) -> Trip:
    driver = session.scalar(select(DriverProfile).where(DriverProfile.user_id == user.id))
    if not driver or not driver.approved:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Approved driver profile required")
    offer = session.scalar(
        select(DispatchOffer).where(
            DispatchOffer.id == offer_id, DispatchOffer.driver_id == driver.id
        )
    )
    if not offer or offer.status != "PENDING":
        raise HTTPException(status.HTTP_409_CONFLICT, "Offer is no longer available")
    offer.status = "REJECTED"
    driver.availability = DriverState.AVAILABLE.value
    issue_next_candidate_offer(session, offer.trip_id)
    session.commit()
    trip = session.scalar(trip_query().where(Trip.id == offer.trip_id))
    if not trip:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Trip not found")
    return trip


def transition_trip(
    session: Session, user: User, trip_id: str, new_state: TripState, cash_collected: bool
) -> Trip:
    trip = session.scalar(trip_query().where(Trip.id == trip_id))
    if not trip:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Trip not found")
    driver = session.scalar(select(DriverProfile).where(DriverProfile.user_id == user.id))
    is_assigned_driver = driver is not None and trip.assigned_driver_id == driver.id
    is_booker = trip.ride_request.booker_user_id == user.id
    if not is_assigned_driver and not (is_booker and new_state == TripState.CANCELLED):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not allowed to transition this trip")
    if new_state.value not in ALLOWED_TRANSITIONS.get(trip.state, set()):
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"Invalid transition {trip.state} -> {new_state.value}"
        )
    if new_state == TripState.COMPLETED:
        is_cash = trip.ride_request.payment_method == PaymentMethod.CASH.value
        if is_cash and not cash_collected:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Cash confirmation required")

    previous_state = trip.state
    trip.state = new_state.value
    trip.version += 1
    session.add(
        TripEvent(
            trip_id=trip.id,
            previous_state=previous_state,
            new_state=new_state.value,
            actor_user_id=user.id,
            correlation_id=new_id(),
            version=trip.version,
            metadata_json=json.dumps({"cash_collected": cash_collected}),
        )
    )

    if driver:
        availability_by_trip_state = {
            TripState.DRIVER_EN_ROUTE: DriverState.EN_ROUTE_TO_PICKUP,
            TripState.DRIVER_ARRIVED: DriverState.ARRIVED,
            TripState.IN_PROGRESS: DriverState.ON_TRIP,
            TripState.COMPLETED: DriverState.AVAILABLE,
            TripState.CANCELLED: DriverState.AVAILABLE,
        }
        next_availability = availability_by_trip_state.get(new_state)
        if next_availability:
            driver.availability = next_availability.value

    if new_state == TripState.COMPLETED and cash_collected and driver:
        amount = trip.ride_request.accepted_fare_cents
        collection = CashCollection(trip_id=trip.id, driver_id=driver.id, amount_cents=amount)
        session.add(collection)
        session.add_all(
            [
                LedgerEntry(
                    account_code=f"DRIVER_CASH_HELD:{driver.id}",
                    reference_type="TRIP",
                    reference_id=trip.id,
                    debit_cents=amount,
                ),
                LedgerEntry(
                    account_code="RIDE_REVENUE_RECEIVABLE",
                    reference_type="TRIP",
                    reference_id=trip.id,
                    credit_cents=amount,
                ),
            ]
        )
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Transition already recorded") from exc
    return session.scalar(trip_query().where(Trip.id == trip.id))  # type: ignore[return-value]
