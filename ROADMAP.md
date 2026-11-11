# Roadmap

## Delivered foundation

- Expo universal app with persisted secure session and prominent Rider/Driver switch
- approved-driver and applicant experiences under one identity
- deterministic fare quote and guest/cash booking
- server-authoritative dispatch acceptance and trip state machine
- reported cash collection with balanced ledger entries
- SQLite demo plus PostgreSQL/PostGIS/Redis container foundation
- migrations, CI, API contract, tests, and operating documentation
- foreground driver location with freshness, accuracy, and anomaly validation
- PostGIS service zones, spatial indexes, configurable radius expansion, and
  deterministic road-ETA ranking
- ranked offers, atomic assignment, rejection/expiration recovery, and WebSocket
  client updates
- privacy-rounded nearby vehicles and Apple Maps/Google Maps native rendering

## Next milestone

- authorized geocoding and live routing/traffic provider adapters
- transactional outbox, Redis WebSocket fan-out, durable recovery worker, and
  push/SMS adapters
- PostgreSQL simultaneous-acceptance, PostGIS query-plan, and failure-recovery tests
- sandbox marketplace card payment and complete ledger batches
- dispatcher web view for pending/active/failed trips

## Subsequent milestones

- vehicle/document onboarding and human approval controls
- scheduled/multi-stop/airport/accessibility trips
- subscriptions, fleet operations, admin, cash reconciliation, and reports
- authorized competitive fare ingestion, provenance, confidence, and Beat My Fare
- Retell/LangGraph voice adapter using the same idempotent booking tools
- production observability, backup/restore, fraud, security, privacy, and accessibility
- market-by-market compliance gates and legal review

No live competitor fare, payment, telephony, identity verification, background
screening, or insurance capability is implied by the current demo.
