from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models import DriverState, PaymentMethod, TripState


class RegisterRequest(BaseModel):
    email: str = Field(min_length=5, max_length=320)
    full_name: str = Field(min_length=2, max_length=120)
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: str
    password: str


class UserView(BaseModel):
    id: str
    email: str
    full_name: str
    roles: list[str]
    driver_approved: bool
    driver_availability: str | None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserView


class QuoteRequest(BaseModel):
    pickup_address: str = Field(min_length=3, max_length=500)
    destination_address: str = Field(min_length=3, max_length=500)
    estimated_miles: float = Field(default=5, gt=0, le=500)
    estimated_minutes: int = Field(default=15, gt=0, le=1440)
    pickup_latitude: float | None = Field(default=None, ge=-90, le=90)
    pickup_longitude: float | None = Field(default=None, ge=-180, le=180)
    destination_latitude: float | None = Field(default=None, ge=-90, le=90)
    destination_longitude: float | None = Field(default=None, ge=-180, le=180)


class QuoteResponse(BaseModel):
    fare_cents: int
    currency: str = "USD"
    breakdown: dict[str, int]
    synthetic: bool = True


class BookingRequest(BaseModel):
    pickup_address: str = Field(min_length=3, max_length=500)
    destination_address: str = Field(min_length=3, max_length=500)
    accepted_fare_cents: int = Field(ge=500, le=500_000)
    payment_method: PaymentMethod
    for_someone_else: bool = False
    guest_passenger_name: str | None = Field(default=None, max_length=120)
    guest_passenger_phone: str | None = Field(default=None, max_length=32)
    guest_communication_consent: bool = False
    payment_responsibility: str = "BOOKER"
    pickup_latitude: float | None = Field(default=None, ge=-90, le=90)
    pickup_longitude: float | None = Field(default=None, ge=-180, le=180)
    destination_latitude: float | None = Field(default=None, ge=-90, le=90)
    destination_longitude: float | None = Field(default=None, ge=-180, le=180)

    @model_validator(mode="after")
    def validate_guest(self) -> "BookingRequest":
        if self.for_someone_else:
            if not self.guest_passenger_name or not self.guest_passenger_phone:
                raise ValueError("Guest name and phone are required")
            if not self.guest_communication_consent:
                raise ValueError("Guest communication consent is required")
        coordinate_values = (
            self.pickup_latitude,
            self.pickup_longitude,
            self.destination_latitude,
            self.destination_longitude,
        )
        if any(value is not None for value in coordinate_values) and any(
            value is None for value in coordinate_values
        ):
            raise ValueError("All pickup and destination coordinates are required together")
        return self


class TripEventView(BaseModel):
    previous_state: str | None
    new_state: str
    version: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TripView(BaseModel):
    id: str
    state: str
    version: int
    assigned_driver_id: str | None
    pickup_address: str
    destination_address: str
    fare_cents: int
    payment_method: str
    guest_passenger_name: str | None
    events: list[TripEventView]


class AvailabilityRequest(BaseModel):
    availability: DriverState


class OfferView(BaseModel):
    id: str
    trip_id: str
    status: str
    expires_at: datetime
    pickup_address: str
    destination_address: str
    fare_cents: int
    pickup_eta_seconds: int | None = None
    estimated_trip_miles: float | None = None
    expected_earnings_cents: int | None = None


class DriverLocationRequest(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    accuracy_meters: float = Field(ge=0, le=10_000)
    speed_mps: float | None = Field(default=None, ge=0, le=500)
    heading_degrees: float | None = Field(default=None, ge=0, lt=360)
    observed_at: datetime


class DriverLocationView(BaseModel):
    driver_id: str
    accepted: bool
    anomaly_code: str | None
    observed_at: datetime
    expires_at: datetime | None


class NearbyVehicleView(BaseModel):
    vehicle_id: str
    latitude: float
    longitude: float
    category: str = "STANDARD"
    approximate: bool = True
    updated_at: datetime


class RouteEstimateRequest(BaseModel):
    origin_latitude: float = Field(ge=-90, le=90)
    origin_longitude: float = Field(ge=-180, le=180)
    destination_latitude: float = Field(ge=-90, le=90)
    destination_longitude: float = Field(ge=-180, le=180)


class RouteEstimateView(BaseModel):
    distance_miles: float
    duration_seconds: int
    provider: str
    synthetic: bool


class DispatchCandidateView(BaseModel):
    driver_id: str
    pickup_eta_seconds: int
    road_distance_miles: float
    search_radius_miles: float
    rank: int


class DispatchPreviewRequest(BaseModel):
    pickup_latitude: float = Field(ge=-90, le=90)
    pickup_longitude: float = Field(ge=-180, le=180)


class TransitionRequest(BaseModel):
    new_state: TripState
    cash_collected: bool = False


class CashView(BaseModel):
    trip_id: str
    amount_cents: int
    status: str
