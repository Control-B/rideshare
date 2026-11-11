# Architecture

## Current shape

The MVP is a modular monolith with explicit domain boundaries. The Expo application
is a client; FastAPI is authoritative for identity, authorization, pricing, booking,
dispatch, trip state, and cash records. PostgreSQL/PostGIS and Redis are provisioned
for the target architecture, while SQLite keeps the no-cost local demo simple.

```text
Expo / React Native Web
        |
 HTTP + authenticated WebSocket
        |
FastAPI modular API
 identity | pricing | geospatial | dispatch | trip | cash ledger
        |
 PostgreSQL/PostGIS       Redis
```

The phone, web, dispatcher, and future voice channel must call the same application
services. A channel cannot create assignments or settle payments directly.

## Invariants

- Interface mode is presentation state, never authorization.
- Driver availability remains independent of the visible interface.
- A conditional database update assigns a trip only while it is `SEARCHING` and has
  no assigned driver.
- Trip transitions follow a server-side allow-list and append versioned events.
- Booker, actual passenger, assigned driver, and payer are separate fields.
- Cash reported by a driver is `REPORTED_COLLECTED`, not platform-settled cash.
- Accepted fare is stored in integer cents on the ride request.
- Idempotency is unique per booking account and key.
- Only fresh, accurate locations from approved drivers can enter presence.
- Legal/operational eligibility is filtered before ETA ranking.
- Vehicle markers shown before assignment use rounded, approximate coordinates.

## Geospatial and real-time boundary

`RoutingProvider` isolates road-network ETA providers. The current
`DeterministicRoutingProvider` is free, deterministic, and explicitly synthetic; it can
be replaced by an authorized Google Routes or Mapbox Matrix adapter. Configurable
2/5/10-mile defaults expand until eligible candidates are found, then candidates are
ranked by pickup ETA.

SQLite uses portable latitude/longitude filtering for tests. PostgreSQL migrations add
generated PostGIS geography values and GiST indexes; `ST_DWithin` performs the
production candidate search. Driver presence is short-lived while immutable location
events support narrowly retained integrity review.

The current WebSocket manager supports one API process. Production requires Redis
pub/sub fan-out, durable recovery jobs, and an outbox so events survive process failure.

## Planned boundaries

Pricing, dispatch, notification, voice, payment, subscription, compliance, and fare
intelligence are internal modules first. Extract them only when scaling, isolation, or
operational ownership requires it. The transactional outbox and durable workers are
the next reliability boundary before any extraction.

## Expo compatibility

The project currently uses SDK 57. Foreground location is the Expo Go-compatible path,
but the App Store Expo Go client may support an older SDK; use a matching simulator or
development build when versions differ. Background location, production push
behavior, and native payment SDKs require development builds and platform adapters.
