# Testing

Backend tests exercise the implemented vertical slice:

- unified rider and approved-driver login
- deterministic quote
- consent-validated guest booking
- booking idempotency
- driver offer and atomic assignment guard
- stale acceptance rejection
- every valid trip transition
- required cash confirmation
- cash collection record
- rider denial on driver APIs
- onboarding without implicit approval
- road-ETA ranking instead of straight-line ordering
- configurable search-radius expansion
- stale and inaccurate location rejection
- fraud-review event creation
- coordinate booking and ranked offer creation
- rejection recovery to the next candidate
- simultaneous offer acceptance with exactly one winner
- authenticated WebSocket connection and heartbeat

Run:

```bash
cd backend
../.venv/bin/ruff check .
../.venv/bin/pytest --cov=app

cd ../frontend/universal-app
npm run lint
npx tsc --noEmit
npx expo export --platform web
```

CI runs lint, types, tests, migration, and web export. The included simultaneous
acceptance test verifies the conditional assignment guard on SQLite. PostgreSQL
transaction-isolation tests, PostGIS query-plan checks, Playwright web journeys,
Maestro device journeys, provider contract tests, accessibility automation, and
load/chaos tests remain required. SQLite is not evidence of PostGIS performance or
full production concurrency behavior.
