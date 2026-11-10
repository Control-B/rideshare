# API

FastAPI publishes OpenAPI at `/api/openapi.json` and interactive local documentation
at `/api/docs`. All protected routes use a bearer access token.

## Vertical-slice endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/api/v1/auth/register` | Create one rider identity |
| POST | `/api/v1/auth/login` | Obtain an access token |
| GET | `/api/v1/me` | Read roles and driver state |
| POST | `/api/v1/quotes` | Calculate a deterministic fare |
| POST | `/api/v1/bookings` | Create/idempotently replay a booking |
| GET | `/api/v1/trips` | Read authorized rider/driver trips |
| POST | `/api/v1/driver/onboarding` | Create an unapproved applicant |
| PUT | `/api/v1/driver/availability` | Explicit online/offline change |
| GET | `/api/v1/driver/offers` | List offers for an approved driver |
| POST | `/api/v1/driver/offers/{id}/accept` | Atomically claim an offer |
| POST | `/api/v1/trips/{id}/transition` | Apply an authorized transition |
| GET | `/api/v1/trips/{id}/cash` | Read reported cash status |

`POST /bookings` requires an `Idempotency-Key` header. Reusing the same key for the
same account returns the original trip and cannot create a duplicate.

## Trip path

```text
SEARCHING → ASSIGNED → DRIVER_EN_ROUTE → DRIVER_ARRIVED
           → IN_PROGRESS → COMPLETED
```

Cancellation is allowed only at defined pre-trip points. Invalid, stale, unauthorized,
and duplicate operations return 409, 403, or 422 rather than mutating state.
