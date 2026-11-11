from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import (
    Depends,
    FastAPI,
    Header,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import (
    CurrentUser,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.config import get_settings
from app.database import SessionLocal, get_session
from app.geospatial import (
    DeterministicRoutingProvider,
    rank_available_drivers,
    record_driver_location,
)
from app.models import (
    CashCollection,
    DispatchCandidate,
    DispatchOffer,
    DriverPresence,
    DriverProfile,
    DriverState,
    RideRequest,
    RiderProfile,
    ServiceZone,
    Trip,
    User,
    UserRole,
)
from app.realtime import realtime_manager
from app.schemas import (
    AvailabilityRequest,
    BookingRequest,
    CashView,
    DispatchCandidateView,
    DispatchPreviewRequest,
    DriverLocationRequest,
    DriverLocationView,
    LoginRequest,
    NearbyVehicleView,
    OfferView,
    QuoteRequest,
    QuoteResponse,
    RegisterRequest,
    RouteEstimateRequest,
    RouteEstimateView,
    TokenResponse,
    TransitionRequest,
    TripView,
    UserView,
)
from app.services import (
    accept_offer,
    calculate_quote,
    create_booking,
    recover_expired_offers,
    reject_offer,
    to_trip_view,
    transition_trip,
    trip_query,
)


def user_view(user: User) -> UserView:
    return UserView(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        roles=[role.role for role in user.roles],
        driver_approved=bool(user.driver_profile and user.driver_profile.approved),
        driver_availability=(user.driver_profile.availability if user.driver_profile else None),
    )


async def notify_trip_participants(session: Session, trip: Trip, event_type: str) -> None:
    user_ids = {
        trip.ride_request.booker_user_id,
        *session.scalars(
            select(DriverProfile.user_id)
            .join(DispatchOffer, DispatchOffer.driver_id == DriverProfile.id)
            .where(DispatchOffer.trip_id == trip.id)
        ),
    }
    if trip.assigned_driver_id:
        assigned_user_id = session.scalar(
            select(DriverProfile.user_id).where(DriverProfile.id == trip.assigned_driver_id)
        )
        if assigned_user_id:
            user_ids.add(assigned_user_id)
    await realtime_manager.send_many(
        user_ids,
        {"type": event_type, "trip_id": trip.id, "state": trip.state},
    )


def create_user(
    session: Session,
    email: str,
    full_name: str,
    password: str,
    *,
    approved_driver: bool = False,
) -> User:
    user = User(email=email.lower(), full_name=full_name, password_hash=hash_password(password))
    user.roles.append(UserRole(role="RIDER"))
    session.add(user)
    session.flush()
    session.add(RiderProfile(user_id=user.id))
    if approved_driver:
        user.roles.append(UserRole(role="DRIVER"))
        session.add(
            DriverProfile(
                user=user,
                approved=True,
                availability=DriverState.AVAILABLE.value,
                vehicle_label="Blue demo sedan · DEMO-101",
            )
        )
    session.commit()
    session.refresh(user)
    return user


def seed_demo_data() -> None:
    with SessionLocal() as session:
        rider = session.scalar(select(User).where(User.email == "rider@example.test"))
        if rider:
            rider.full_name = "Banjah"
            session.commit()
        else:
            create_user(session, "rider@example.test", "Banjah", "demo-pass-123")

        driver = session.scalar(select(User).where(User.email == "driver@example.test"))
        if not driver:
            create_user(
                session,
                "driver@example.test",
                "Devon Driver",
                "demo-pass-123",
                approved_driver=True,
            )

        zone = session.scalar(select(ServiceZone).where(ServiceZone.market_code == "DEMO-MIA"))
        if not zone:
            session.add(
                ServiceZone(
                    market_code="DEMO-MIA",
                    name="Synthetic Miami demonstration zone",
                    operating_mode="HYBRID",
                    is_active=True,
                    compliance_reviewed=True,
                    min_latitude=25.55,
                    max_latitude=26.05,
                    min_longitude=-80.45,
                    max_longitude=-80.05,
                )
            )
            session.commit()


@asynccontextmanager
async def lifespan(_: FastAPI):
    seed_demo_data()
    yield


settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
    openapi_url="/api/openapi.json",
    docs_url="/api/docs",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SessionDep = Annotated[Session, Depends(get_session)]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "api"}


@app.post("/api/v1/auth/register", response_model=TokenResponse, status_code=201)
def register(payload: RegisterRequest, session: SessionDep) -> TokenResponse:
    try:
        user = create_user(session, payload.email, payload.full_name, payload.password)
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered") from exc
    return TokenResponse(access_token=create_access_token(user.id), user=user_view(user))


@app.post("/api/v1/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest, session: SessionDep) -> TokenResponse:
    user = session.scalar(select(User).where(User.email == payload.email.lower()))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    return TokenResponse(access_token=create_access_token(user.id), user=user_view(user))


@app.get("/api/v1/me", response_model=UserView)
def me(user: CurrentUser) -> UserView:
    return user_view(user)


@app.post("/api/v1/quotes", response_model=QuoteResponse)
def quote(payload: QuoteRequest, _: CurrentUser) -> QuoteResponse:
    fare, breakdown = calculate_quote(payload)
    return QuoteResponse(fare_cents=fare, breakdown=breakdown)


@app.post("/api/v1/bookings", response_model=TripView, status_code=201)
async def book(
    payload: BookingRequest,
    user: CurrentUser,
    session: SessionDep,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=8)],
) -> TripView:
    trip = create_booking(session, user, payload, idempotency_key)
    await notify_trip_participants(session, trip, "TRIP_SEARCH_UPDATED")
    return to_trip_view(trip)


@app.get("/api/v1/trips", response_model=list[TripView])
def list_trips(user: CurrentUser, session: SessionDep) -> list[TripView]:
    rows = session.scalars(
        trip_query()
        .join(Trip.ride_request)
        .outerjoin(DriverProfile, Trip.assigned_driver_id == DriverProfile.id)
        .where(or_(RideRequest.booker_user_id == user.id, DriverProfile.user_id == user.id))
        .order_by(Trip.created_at.desc())
    ).unique()
    return [to_trip_view(trip) for trip in rows]


@app.post("/api/v1/driver/onboarding", response_model=UserView)
def start_driver_onboarding(user: CurrentUser, session: SessionDep) -> UserView:
    if not user.driver_profile:
        session.add(DriverProfile(user_id=user.id, approved=False))
        if "DRIVER_APPLICANT" not in {role.role for role in user.roles}:
            user.roles.append(UserRole(role="DRIVER_APPLICANT"))
        session.commit()
        session.refresh(user)
    return user_view(user)


@app.put("/api/v1/driver/availability", response_model=UserView)
def set_availability(
    payload: AvailabilityRequest, user: CurrentUser, session: SessionDep
) -> UserView:
    driver = user.driver_profile
    if not driver or not driver.approved:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Approved driver profile required")
    if payload.availability not in {DriverState.OFFLINE, DriverState.AVAILABLE}:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Unsupported manual state")
    if driver.availability in {
        DriverState.OFFER_PENDING.value,
        DriverState.ASSIGNED.value,
        DriverState.EN_ROUTE_TO_PICKUP.value,
        DriverState.ARRIVED.value,
        DriverState.ON_TRIP.value,
    }:
        raise HTTPException(status.HTTP_409_CONFLICT, "Active trip controls availability")
    if payload.availability == DriverState.AVAILABLE:
        presence = session.get(DriverPresence, driver.id)
        now = datetime.now(UTC)
        if (
            not presence
            or presence.expires_at.replace(tzinfo=presence.expires_at.tzinfo or UTC) < now
            or presence.observed_at.replace(tzinfo=presence.observed_at.tzinfo or UTC)
            < now - timedelta(seconds=settings.driver_location_stale_seconds)
            or presence.accuracy_meters > settings.driver_max_accuracy_meters
        ):
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "A fresh, accurate driver location is required before going online",
            )
    driver.availability = payload.availability.value
    session.commit()
    session.refresh(user)
    return user_view(user)


@app.post("/api/v1/driver/location", response_model=DriverLocationView)
async def update_driver_location(
    payload: DriverLocationRequest, user: CurrentUser, session: SessionDep
) -> DriverLocationView:
    try:
        event, presence = record_driver_location(session, user, payload)
    except PermissionError as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(exc)) from exc
    await realtime_manager.send(
        user.id,
        {
            "type": "DRIVER_LOCATION_ACCEPTED" if presence else "DRIVER_LOCATION_FLAGGED",
            "observed_at": event.observed_at.isoformat(),
            "anomaly_code": event.anomaly_code,
        },
    )
    return DriverLocationView(
        driver_id=event.driver_id,
        accepted=presence is not None,
        anomaly_code=event.anomaly_code,
        observed_at=event.observed_at,
        expires_at=presence.expires_at if presence else None,
    )


@app.get("/api/v1/vehicles/nearby", response_model=list[NearbyVehicleView])
def nearby_vehicles(
    user: CurrentUser,
    session: SessionDep,
    latitude: Annotated[float, Query(ge=-90, le=90)],
    longitude: Annotated[float, Query(ge=-180, le=180)],
    radius_miles: Annotated[float, Query(gt=0, le=10)] = 2,
) -> list[NearbyVehicleView]:
    del user
    now = datetime.now(UTC)
    rows = session.execute(
        select(DriverPresence, DriverProfile)
        .join(DriverProfile, DriverPresence.driver_id == DriverProfile.id)
        .where(
            DriverProfile.approved.is_(True),
            DriverProfile.availability.in_(
                [DriverState.AVAILABLE.value, DriverState.OFFER_PENDING.value]
            ),
            DriverPresence.expires_at >= now,
            DriverPresence.observed_at
            >= now - timedelta(seconds=settings.driver_location_stale_seconds),
        )
    )
    from app.geospatial import haversine_miles

    vehicles: list[NearbyVehicleView] = []
    for presence, driver in rows:
        if (
            haversine_miles(latitude, longitude, presence.latitude, presence.longitude)
            <= radius_miles
        ):
            vehicles.append(
                NearbyVehicleView(
                    vehicle_id=f"vehicle-{driver.id[-8:]}",
                    latitude=round(presence.latitude, 3),
                    longitude=round(presence.longitude, 3),
                    updated_at=presence.observed_at,
                )
            )
    return vehicles


@app.post("/api/v1/routes/estimate", response_model=RouteEstimateView)
def estimate_route(payload: RouteEstimateRequest, _: CurrentUser) -> RouteEstimateView:
    route = DeterministicRoutingProvider().estimate(
        payload.origin_latitude,
        payload.origin_longitude,
        payload.destination_latitude,
        payload.destination_longitude,
    )
    return RouteEstimateView(
        distance_miles=route.distance_miles,
        duration_seconds=route.duration_seconds,
        provider=route.provider,
        synthetic=route.synthetic,
    )


@app.post("/api/v1/dispatch/preview", response_model=list[DispatchCandidateView])
def preview_dispatch(
    payload: DispatchPreviewRequest, user: CurrentUser, session: SessionDep
) -> list[DispatchCandidateView]:
    candidates = rank_available_drivers(
        session,
        payload.pickup_latitude,
        payload.pickup_longitude,
        excluded_user_id=user.id,
    )
    return [
        DispatchCandidateView(
            driver_id=candidate.driver_id,
            pickup_eta_seconds=candidate.pickup_eta_seconds,
            road_distance_miles=candidate.road_distance_miles,
            search_radius_miles=candidate.search_radius_miles,
            rank=rank,
        )
        for rank, candidate in enumerate(candidates, start=1)
    ]


@app.get("/api/v1/driver/offers", response_model=list[OfferView])
async def list_offers(user: CurrentUser, session: SessionDep) -> list[OfferView]:
    driver = user.driver_profile
    if not driver or not driver.approved:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Approved driver profile required")
    for recovered_trip in recover_expired_offers(session):
        await notify_trip_participants(session, recovered_trip, "DISPATCH_RECOVERY_UPDATED")
    rows = session.execute(
        select(DispatchOffer, RideRequest, DispatchCandidate)
        .join(Trip, DispatchOffer.trip_id == Trip.id)
        .join(RideRequest, Trip.ride_request_id == RideRequest.id)
        .outerjoin(
            DispatchCandidate,
            (DispatchCandidate.trip_id == DispatchOffer.trip_id)
            & (DispatchCandidate.driver_id == DispatchOffer.driver_id),
        )
        .where(DispatchOffer.driver_id == driver.id, DispatchOffer.status == "PENDING")
        .order_by(DispatchOffer.created_at.desc())
    )
    return [
        OfferView(
            id=offer.id,
            trip_id=offer.trip_id,
            status=offer.status,
            expires_at=offer.expires_at,
            pickup_address=request.pickup_address,
            destination_address=request.destination_address,
            fare_cents=request.accepted_fare_cents,
            pickup_eta_seconds=candidate.pickup_eta_seconds if candidate else None,
            estimated_trip_miles=None,
            expected_earnings_cents=round(request.accepted_fare_cents * 0.8),
        )
        for offer, request, candidate in rows
    ]


@app.post("/api/v1/driver/offers/{offer_id}/accept", response_model=TripView)
async def accept(offer_id: str, user: CurrentUser, session: SessionDep) -> TripView:
    trip = accept_offer(session, user, offer_id)
    await notify_trip_participants(session, trip, "TRIP_ASSIGNED")
    return to_trip_view(trip)


@app.post("/api/v1/driver/offers/{offer_id}/reject", status_code=204)
async def reject(offer_id: str, user: CurrentUser, session: SessionDep) -> None:
    trip = reject_offer(session, user, offer_id)
    await notify_trip_participants(session, trip, "DISPATCH_RECOVERY_UPDATED")


@app.websocket("/api/v1/realtime")
async def realtime(websocket: WebSocket, token: str = Query()) -> None:
    try:
        user_id = decode_access_token(token)
    except ValueError:
        await websocket.close(code=1008, reason="Invalid token")
        return
    with SessionLocal() as session:
        socket_user = session.get(User, user_id)
        if not socket_user or not socket_user.is_active:
            await websocket.close(code=1008, reason="Inactive or unknown user")
            return
    await realtime_manager.connect(user_id, websocket)
    try:
        await websocket.send_json({"type": "CONNECTED"})
        while True:
            message = await websocket.receive_text()
            if message == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        realtime_manager.disconnect(user_id, websocket)


@app.post("/api/v1/trips/{trip_id}/transition", response_model=TripView)
async def transition(
    trip_id: str,
    payload: TransitionRequest,
    user: CurrentUser,
    session: SessionDep,
) -> TripView:
    trip = transition_trip(session, user, trip_id, payload.new_state, payload.cash_collected)
    await notify_trip_participants(session, trip, "TRIP_STATE_UPDATED")
    return to_trip_view(trip)


@app.get("/api/v1/trips/{trip_id}/cash", response_model=CashView)
def cash_status(trip_id: str, user: CurrentUser, session: SessionDep) -> CashView:
    trip = session.scalar(trip_query().where(Trip.id == trip_id))
    if not trip or trip.ride_request.booker_user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cash record not found")
    cash = session.scalar(select(CashCollection).where(CashCollection.trip_id == trip_id))
    if not cash:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cash record not found")
    return CashView(trip_id=trip_id, amount_cents=cash.amount_cents, status=cash.status)


@app.get("/api/v1/demo/accounts")
def demo_accounts(
    enabled: Annotated[bool, Query()] = True,
) -> list[dict[str, str]]:
    if settings.environment == "production" or not enabled:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    return [
        {"email": "rider@example.test", "password": "demo-pass-123", "role": "rider"},
        {"email": "driver@example.test", "password": "demo-pass-123", "role": "driver"},
    ]
