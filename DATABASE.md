# Database

SQLAlchemy 2 models and Alembic migrations are under `backend/app` and
`backend/migrations`.

The implemented slice includes users, roles, rider/driver profiles, location events,
short-lived driver presence, service zones, ranked dispatch candidates, offers, trips,
trip events, fraud-review signals, cash collections, and ledger entries. UUID strings
remain portable between SQLite demo mode and PostgreSQL.

On PostgreSQL, generated `geography` columns and GiST indexes are created for driver
presence, location events, and service-zone boundaries. Candidate search uses
`ST_DWithin` in meters. SQLite retains a deterministic Haversine path for local tests;
it is not a PostGIS performance substitute.

Key constraints:

- unique normalized user email
- unique user/role and one rider/driver profile per user
- unique booking idempotency key per booker
- one trip per ride request
- one offer per trip/driver
- one event version per trip
- one cash collection per trip
- unique ledger account/reference tuple
- one current presence row per driver
- one ranked candidate and one offer per trip/driver
- latitude, longitude, accuracy, and service-zone bounds checks

Money is stored in integer cents. Timestamps are UTC. Trip versions support optimistic
concurrency and event ordering. Ledger entries are append-only in application code.

Run:

```bash
cd backend
alembic upgrade head
alembic revision --autogenerate -m "describe change"
```

Production still needs partition/retention jobs for location history, a transactional
outbox, durable dispatch workers, vehicles/documents, full payment batches,
notifications, subscriptions, fare observations, calls, and compliance records.
