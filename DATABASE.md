# Database

SQLAlchemy 2 models and Alembic migrations are under `backend/app` and
`backend/migrations`.

The implemented slice includes users, roles, rider profiles, driver profiles, ride
requests, trips, trip events, dispatch offers, cash collections, and ledger entries.
UUID strings are portable between SQLite demo mode and PostgreSQL. Production
migrations will use native UUID and PostGIS geography where appropriate.

Key constraints:

- unique normalized user email
- unique user/role and one rider/driver profile per user
- unique booking idempotency key per booker
- one trip per ride request
- one offer per trip/driver
- one event version per trip
- one cash collection per trip
- unique ledger account/reference tuple

Money is stored in integer cents. Timestamps are UTC. Trip versions support optimistic
concurrency and event ordering. Ledger entries are append-only in application code.

Run:

```bash
cd backend
alembic upgrade head
alembic revision --autogenerate -m "describe change"
```

The complete roadmap adds PostGIS service areas/locations, vehicles, documents,
payment transactions, full double-entry batches, outbox events, notifications,
subscriptions, fare observations, calls, and compliance records.
