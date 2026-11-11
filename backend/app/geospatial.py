import json
import math
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.models import (
    DriverLocationEvent,
    DriverPresence,
    DriverProfile,
    DriverState,
    FraudRiskEvent,
    ServiceZone,
    User,
)
from app.schemas import DriverLocationRequest

EARTH_RADIUS_MILES = 3958.7613


@dataclass(frozen=True)
class RouteEstimate:
    distance_miles: float
    duration_seconds: int
    provider: str
    synthetic: bool


@dataclass(frozen=True)
class RankedDriver:
    driver_id: str
    straight_line_miles: float
    road_distance_miles: float
    pickup_eta_seconds: int
    search_radius_miles: float
    score: float
    routing_provider: str


class RoutingProvider(Protocol):
    def estimate(
        self, origin_lat: float, origin_lon: float, destination_lat: float, destination_lon: float
    ) -> RouteEstimate: ...


class DeterministicRoutingProvider:
    """Free demo adapter. Live providers implement the same interface server-side."""

    def __init__(self, average_speed_mph: float = 24, road_factor: float = 1.22):
        self.average_speed_mph = average_speed_mph
        self.road_factor = road_factor

    def estimate(
        self, origin_lat: float, origin_lon: float, destination_lat: float, destination_lon: float
    ) -> RouteEstimate:
        straight_line = haversine_miles(origin_lat, origin_lon, destination_lat, destination_lon)
        road_distance = max(0.1, straight_line * self.road_factor)
        duration = max(60, round((road_distance / self.average_speed_mph) * 3600 + 45))
        return RouteEstimate(
            distance_miles=round(road_distance, 2),
            duration_seconds=duration,
            provider="DETERMINISTIC_DEMO",
            synthetic=True,
        )


def haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    lat1_rad, lat2_rad = math.radians(lat1), math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    value = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    )
    return 2 * EARTH_RADIUS_MILES * math.asin(math.sqrt(value))


def point_in_active_service_zone(session: Session, latitude: float, longitude: float) -> bool:
    zone = session.scalar(
        select(ServiceZone.id).where(
            ServiceZone.is_active.is_(True),
            ServiceZone.compliance_reviewed.is_(True),
            ServiceZone.min_latitude <= latitude,
            ServiceZone.max_latitude >= latitude,
            ServiceZone.min_longitude <= longitude,
            ServiceZone.max_longitude >= longitude,
        )
    )
    return zone is not None


def record_driver_location(
    session: Session,
    user: User,
    payload: DriverLocationRequest,
    settings: Settings | None = None,
) -> tuple[DriverLocationEvent, DriverPresence | None]:
    settings = settings or get_settings()
    driver = session.scalar(select(DriverProfile).where(DriverProfile.user_id == user.id))
    if not driver or not driver.approved:
        raise PermissionError("Approved driver profile required")

    now = datetime.now(UTC)
    observed_at = payload.observed_at
    if observed_at.tzinfo is None:
        observed_at = observed_at.replace(tzinfo=UTC)
    anomaly: str | None = None
    if observed_at > now + timedelta(seconds=30):
        anomaly = "FUTURE_TIMESTAMP"
    elif observed_at < now - timedelta(minutes=10):
        anomaly = "STALE_SUBMISSION"
    elif payload.accuracy_meters > settings.driver_max_accuracy_meters:
        anomaly = "LOW_ACCURACY"
    elif payload.speed_mps and payload.speed_mps > settings.driver_max_speed_mps:
        anomaly = "REPORTED_SPEED"

    presence = session.get(DriverPresence, driver.id)
    if not anomaly and presence:
        previous_at = presence.observed_at
        if previous_at.tzinfo is None:
            previous_at = previous_at.replace(tzinfo=UTC)
        elapsed = (observed_at - previous_at).total_seconds()
        if elapsed <= 0:
            anomaly = "OUT_OF_ORDER"
        inferred_speed = (
            haversine_miles(
                presence.latitude,
                presence.longitude,
                payload.latitude,
                payload.longitude,
            )
            * 1609.344
            / max(0.001, elapsed)
        )
        if not anomaly and inferred_speed > settings.driver_max_speed_mps:
            anomaly = "IMPOSSIBLE_TRAVEL"

    event = DriverLocationEvent(
        driver_id=driver.id,
        latitude=payload.latitude,
        longitude=payload.longitude,
        accuracy_meters=payload.accuracy_meters,
        speed_mps=payload.speed_mps,
        heading_degrees=payload.heading_degrees,
        observed_at=observed_at,
        anomaly_code=anomaly,
    )
    session.add(event)

    if anomaly:
        session.add(
            FraudRiskEvent(
                actor_user_id=user.id,
                event_type=f"GPS_{anomaly}",
                metadata_json=json.dumps(
                    {
                        "latitude": payload.latitude,
                        "longitude": payload.longitude,
                        "accuracy_meters": payload.accuracy_meters,
                    }
                ),
            )
        )
        session.commit()
        return event, None

    expires_at = observed_at + timedelta(seconds=settings.driver_presence_ttl_seconds)
    if presence:
        presence.latitude = payload.latitude
        presence.longitude = payload.longitude
        presence.accuracy_meters = payload.accuracy_meters
        presence.observed_at = observed_at
        presence.expires_at = expires_at
        presence.version += 1
    else:
        presence = DriverPresence(
            driver_id=driver.id,
            latitude=payload.latitude,
            longitude=payload.longitude,
            accuracy_meters=payload.accuracy_meters,
            observed_at=observed_at,
            expires_at=expires_at,
        )
        session.add(presence)
    session.commit()
    return event, presence


def _portable_presence_rows(
    session: Session,
    pickup_latitude: float,
    pickup_longitude: float,
    radius_miles: float,
    excluded_user_id: str | None,
    settings: Settings,
) -> list[tuple[str, float, float]]:
    now = datetime.now(UTC)
    freshness_cutoff = now - timedelta(seconds=settings.driver_location_stale_seconds)
    rows = session.execute(
        select(DriverPresence, DriverProfile)
        .join(DriverProfile, DriverPresence.driver_id == DriverProfile.id)
        .where(
            DriverProfile.approved.is_(True),
            DriverProfile.availability == DriverState.AVAILABLE.value,
            DriverPresence.expires_at >= now,
            DriverPresence.observed_at >= freshness_cutoff,
            DriverPresence.accuracy_meters <= settings.driver_max_accuracy_meters,
        )
    )
    result: list[tuple[str, float, float]] = []
    for presence, driver in rows:
        if excluded_user_id and driver.user_id == excluded_user_id:
            continue
        distance = haversine_miles(
            pickup_latitude,
            pickup_longitude,
            presence.latitude,
            presence.longitude,
        )
        if distance <= radius_miles:
            result.append((driver.id, presence.latitude, presence.longitude))
    return result


def _postgis_presence_rows(
    session: Session,
    pickup_latitude: float,
    pickup_longitude: float,
    radius_miles: float,
    excluded_user_id: str | None,
    settings: Settings,
) -> list[tuple[str, float, float]]:
    rows = session.execute(
        text(
            """
            SELECT p.driver_id, p.latitude, p.longitude
            FROM driver_presence p
            JOIN driver_profiles d ON d.id = p.driver_id
            WHERE d.approved = true
              AND d.availability = 'AVAILABLE'
              AND p.expires_at >= NOW()
              AND p.observed_at >= NOW() - (:stale_seconds * INTERVAL '1 second')
              AND p.accuracy_meters <= :accuracy
              AND (:excluded_user_id IS NULL OR d.user_id <> :excluded_user_id)
              AND ST_DWithin(
                p.location,
                ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326)::geography,
                :radius_meters
              )
            """
        ),
        {
            "stale_seconds": settings.driver_location_stale_seconds,
            "accuracy": settings.driver_max_accuracy_meters,
            "excluded_user_id": excluded_user_id,
            "longitude": pickup_longitude,
            "latitude": pickup_latitude,
            "radius_meters": radius_miles * 1609.344,
        },
    )
    return [(row.driver_id, row.latitude, row.longitude) for row in rows]


def rank_available_drivers(
    session: Session,
    pickup_latitude: float,
    pickup_longitude: float,
    *,
    excluded_user_id: str | None = None,
    settings: Settings | None = None,
    routing_provider: RoutingProvider | None = None,
) -> list[RankedDriver]:
    settings = settings or get_settings()
    routing_provider = routing_provider or DeterministicRoutingProvider()
    rows: list[tuple[str, float, float]] = []
    selected_radius = settings.dispatch_radii[-1]

    for radius in settings.dispatch_radii:
        selected_radius = radius
        if session.bind and session.bind.dialect.name == "postgresql":
            rows = _postgis_presence_rows(
                session,
                pickup_latitude,
                pickup_longitude,
                radius,
                excluded_user_id,
                settings,
            )
        else:
            rows = _portable_presence_rows(
                session,
                pickup_latitude,
                pickup_longitude,
                radius,
                excluded_user_id,
                settings,
            )
        if rows:
            break

    ranked: list[RankedDriver] = []
    for driver_id, latitude, longitude in rows:
        straight_line = haversine_miles(pickup_latitude, pickup_longitude, latitude, longitude)
        route = routing_provider.estimate(latitude, longitude, pickup_latitude, pickup_longitude)
        ranked.append(
            RankedDriver(
                driver_id=driver_id,
                straight_line_miles=round(straight_line, 2),
                road_distance_miles=route.distance_miles,
                pickup_eta_seconds=route.duration_seconds,
                search_radius_miles=selected_radius,
                score=float(route.duration_seconds),
                routing_provider=route.provider,
            )
        )
    return sorted(ranked, key=lambda candidate: (candidate.score, candidate.driver_id))
