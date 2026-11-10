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

CI runs lint, types, tests, migration, and web export. PostgreSQL concurrency tests
with simultaneous driver transactions, Playwright web journeys, Maestro device
journeys, provider contract tests, accessibility automation, and load/chaos tests are
required in later milestones. SQLite tests are not evidence of PostGIS performance or
full production concurrency behavior.
