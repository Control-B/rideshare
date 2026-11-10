import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def new_id() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(UTC)


class DriverState(enum.StrEnum):
    OFFLINE = "OFFLINE"
    AVAILABLE = "AVAILABLE"
    OFFER_PENDING = "OFFER_PENDING"
    ASSIGNED = "ASSIGNED"
    EN_ROUTE_TO_PICKUP = "EN_ROUTE_TO_PICKUP"
    ARRIVED = "ARRIVED"
    ON_TRIP = "ON_TRIP"
    UNAVAILABLE = "UNAVAILABLE"
    SUSPENDED = "SUSPENDED"


class TripState(enum.StrEnum):
    SEARCHING = "SEARCHING"
    ASSIGNED = "ASSIGNED"
    DRIVER_EN_ROUTE = "DRIVER_EN_ROUTE"
    DRIVER_ARRIVED = "DRIVER_ARRIVED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"


class PaymentMethod(enum.StrEnum):
    CASH = "CASH"
    SANDBOX_CARD = "SANDBOX_CARD"


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    roles: Mapped[list["UserRole"]] = relationship(cascade="all, delete-orphan")
    driver_profile: Mapped["DriverProfile | None"] = relationship(back_populates="user")


class UserRole(Base):
    __tablename__ = "user_roles"
    __table_args__ = (UniqueConstraint("user_id", "role", name="uq_user_role"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(32))


class RiderProfile(Base):
    __tablename__ = "rider_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True
    )


class DriverProfile(Base):
    __tablename__ = "driver_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True
    )
    approved: Mapped[bool] = mapped_column(Boolean, default=False)
    availability: Mapped[str] = mapped_column(String(32), default=DriverState.OFFLINE.value)
    vehicle_label: Mapped[str | None] = mapped_column(String(120))
    version: Mapped[int] = mapped_column(Integer, default=1)

    user: Mapped[User] = relationship(back_populates="driver_profile")


class RideRequest(Base):
    __tablename__ = "ride_requests"
    __table_args__ = (UniqueConstraint("booker_user_id", "idempotency_key", name="uq_booking_key"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    booker_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    passenger_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    guest_passenger_name: Mapped[str | None] = mapped_column(String(120))
    guest_passenger_phone: Mapped[str | None] = mapped_column(String(32))
    payer_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    payment_responsibility: Mapped[str] = mapped_column(String(32))
    pickup_address: Mapped[str] = mapped_column(String(500))
    destination_address: Mapped[str] = mapped_column(String(500))
    payment_method: Mapped[str] = mapped_column(String(32))
    accepted_fare_cents: Mapped[int] = mapped_column(Integer)
    idempotency_key: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    trip: Mapped["Trip"] = relationship(back_populates="ride_request")


class Trip(Base):
    __tablename__ = "trips"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    ride_request_id: Mapped[str] = mapped_column(
        ForeignKey("ride_requests.id"), unique=True, index=True
    )
    assigned_driver_id: Mapped[str | None] = mapped_column(
        ForeignKey("driver_profiles.id"), index=True
    )
    state: Mapped[str] = mapped_column(String(32), default=TripState.SEARCHING.value, index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    ride_request: Mapped[RideRequest] = relationship(back_populates="trip")
    events: Mapped[list["TripEvent"]] = relationship(
        order_by="TripEvent.created_at", cascade="all, delete-orphan"
    )


class TripEvent(Base):
    __tablename__ = "trip_events"
    __table_args__ = (UniqueConstraint("trip_id", "version", name="uq_trip_event_version"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    trip_id: Mapped[str] = mapped_column(ForeignKey("trips.id", ondelete="CASCADE"), index=True)
    previous_state: Mapped[str | None] = mapped_column(String(32))
    new_state: Mapped[str] = mapped_column(String(32))
    actor_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    correlation_id: Mapped[str] = mapped_column(String(100), index=True)
    version: Mapped[int] = mapped_column(Integer)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class DispatchOffer(Base):
    __tablename__ = "dispatch_offers"
    __table_args__ = (
        UniqueConstraint("trip_id", "driver_id", name="uq_trip_driver_offer"),
        Index("ix_offer_driver_status", "driver_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    trip_id: Mapped[str] = mapped_column(ForeignKey("trips.id"), index=True)
    driver_id: Mapped[str] = mapped_column(ForeignKey("driver_profiles.id"), index=True)
    status: Mapped[str] = mapped_column(String(24), default="PENDING")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class CashCollection(Base):
    __tablename__ = "cash_collections"
    __table_args__ = (UniqueConstraint("trip_id", name="uq_cash_trip"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    trip_id: Mapped[str] = mapped_column(ForeignKey("trips.id"), index=True)
    driver_id: Mapped[str] = mapped_column(ForeignKey("driver_profiles.id"))
    amount_cents: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(24), default="REPORTED_COLLECTED")
    reported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    reconciled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class LedgerEntry(Base):
    __tablename__ = "ledger_entries"
    __table_args__ = (
        CheckConstraint("debit_cents >= 0 AND credit_cents >= 0", name="ck_ledger_nonnegative"),
        UniqueConstraint("reference_type", "reference_id", "account_code", name="uq_ledger_ref"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    account_code: Mapped[str] = mapped_column(String(64), index=True)
    reference_type: Mapped[str] = mapped_column(String(32))
    reference_id: Mapped[str] = mapped_column(String(36), index=True)
    debit_cents: Mapped[int] = mapped_column(Integer, default=0)
    credit_cents: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
