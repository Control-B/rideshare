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
| POST | `/api/v1/driver/location` | Validate and record foreground driver location |
| GET | `/api/v1/vehicles/nearby` | Read privacy-rounded available vehicles |
| POST | `/api/v1/routes/estimate` | Estimate a deterministic demo route |
| POST | `/api/v1/dispatch/preview` | Preview eligible ETA-ranked candidates |
| GET | `/api/v1/driver/offers` | List offers for an approved driver |
| POST | `/api/v1/driver/offers/{id}/accept` | Atomically claim an offer |
| POST | `/api/v1/driver/offers/{id}/reject` | Decline and start dispatch recovery |
| POST | `/api/v1/trips/{id}/transition` | Apply an authorized transition |
| GET | `/api/v1/trips/{id}/cash` | Read reported cash status |
| WS | `/api/v1/realtime?token=...` | Receive authenticated trip/offer updates |

`POST /bookings` requires an `Idempotency-Key` header. Reusing the same key for the
same account returns the original trip and cannot create a duplicate.

Coordinate bookings require complete pickup and destination coordinate pairs. Pickup
must be inside an active, compliance-reviewed service zone. Address-only bookings
remain supported as a legacy demo path and do not claim geospatial matching.

Going available requires recent accepted presence. Location submissions outside the
accuracy, timestamp, or plausible-speed thresholds are retained as review signals but
do not update matchable presence.

## Trip path

```text
SEARCHING → ASSIGNED → DRIVER_EN_ROUTE → DRIVER_ARRIVED
           → IN_PROGRESS → COMPLETED
```

Cancellation is allowed only at defined pre-trip points. Invalid, stale, unauthorized,
and duplicate operations return 409, 403, or 422 rather than mutating state.
