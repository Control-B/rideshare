from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import (
    CurrentUser,
    create_access_token,
    hash_password,
    verify_password,
)
from app.config import get_settings
from app.database import Base, SessionLocal, engine, get_session
from app.models import (
    CashCollection,
    DispatchOffer,
    DriverProfile,
    DriverState,
    RideRequest,
    RiderProfile,
    Trip,
    User,
    UserRole,
)
from app.schemas import (
    AvailabilityRequest,
    BookingRequest,
    CashView,
    LoginRequest,
    OfferView,
    QuoteRequest,
    QuoteResponse,
    RegisterRequest,
    TokenResponse,
    TransitionRequest,
    TripView,
    UserView,
)
from app.services import (
    accept_offer,
    calculate_quote,
    create_booking,
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
        if session.scalar(select(User.id).limit(1)):
            return
        create_user(session, "rider@example.test", "Riley Rider", "demo-pass-123")
        create_user(
            session,
            "driver@example.test",
            "Devon Driver",
            "demo-pass-123",
            approved_driver=True,
        )


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(engine)
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
def book(
    payload: BookingRequest,
    user: CurrentUser,
    session: SessionDep,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=8)],
) -> TripView:
    return to_trip_view(create_booking(session, user, payload, idempotency_key))


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
        DriverState.ASSIGNED.value,
        DriverState.EN_ROUTE_TO_PICKUP.value,
        DriverState.ARRIVED.value,
        DriverState.ON_TRIP.value,
    }:
        raise HTTPException(status.HTTP_409_CONFLICT, "Active trip controls availability")
    driver.availability = payload.availability.value
    session.commit()
    session.refresh(user)
    return user_view(user)


@app.get("/api/v1/driver/offers", response_model=list[OfferView])
def list_offers(user: CurrentUser, session: SessionDep) -> list[OfferView]:
    driver = user.driver_profile
    if not driver or not driver.approved:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Approved driver profile required")
    rows = session.execute(
        select(DispatchOffer, RideRequest)
        .join(Trip, DispatchOffer.trip_id == Trip.id)
        .join(RideRequest, Trip.ride_request_id == RideRequest.id)
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
        )
        for offer, request in rows
    ]


@app.post("/api/v1/driver/offers/{offer_id}/accept", response_model=TripView)
def accept(offer_id: str, user: CurrentUser, session: SessionDep) -> TripView:
    return to_trip_view(accept_offer(session, user, offer_id))


@app.post("/api/v1/trips/{trip_id}/transition", response_model=TripView)
def transition(
    trip_id: str,
    payload: TransitionRequest,
    user: CurrentUser,
    session: SessionDep,
) -> TripView:
    return to_trip_view(
        transition_trip(session, user, trip_id, payload.new_state, payload.cash_collected)
    )


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
