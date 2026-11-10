# Architecture

## Current shape

The MVP is a modular monolith with explicit domain boundaries. The Expo application
is a client; FastAPI is authoritative for identity, authorization, pricing, booking,
dispatch, trip state, and cash records. PostgreSQL/PostGIS and Redis are provisioned
for the target architecture, while SQLite keeps the no-cost local demo simple.

```text
Expo / React Native Web
        |
   HTTP + OpenAPI
        |
FastAPI modular API
  identity | pricing | booking | dispatch | trip | cash ledger
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

## Planned boundaries

Pricing, dispatch, notification, voice, payment, subscription, compliance, and fare
intelligence are internal modules first. Extract them only when scaling, isolation, or
operational ownership requires it. The transactional outbox and durable workers are
the next reliability boundary before any extraction.

## Expo compatibility

SDK 57 is intentionally used for current physical-device Expo Go availability.
Foreground location works in Expo Go. Background location, production push behavior,
and native payment SDKs move to development builds and platform-specific adapters.
