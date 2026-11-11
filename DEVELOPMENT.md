# Development

## Prerequisites

- Node.js 22
- Python 3.12+
- Expo Go for device testing
- Docker only when using PostGIS/Redis locally

Copy `frontend/universal-app/.env.example` to `.env.local`. On a physical phone, use
the host computer's LAN address for the API URL.

## Local database options

The default `MOBILITY_DATABASE_URL=sqlite:///./mobility.db` supports the free demo.
For the production-like stack:

```bash
docker compose up --build
```

Then run migrations in the API container or with:

```bash
MOBILITY_DATABASE_URL=postgresql+psycopg://mobility:local_only_change_me@localhost:5432/mobility \
  alembic upgrade head
```

## Expo workflows

Expo Go:

```bash
cd frontend/universal-app
npm start
```

Development build (required for background driver location and production native
integrations):

```bash
npx expo install expo-dev-client
npx expo run:android
# macOS: npx expo run:ios
```

Native maps use Apple Maps on iOS and Google Maps on Android. Web retains a lightweight
preview until a browser map provider is configured. The route adapter is deterministic
and labeled synthetic; no provider-backed traffic or geocoding is represented as live.

Approved drivers send foreground location while online. Expo Go does not support the
production background-location workflow on iOS and has Android limitations. Use a
development build for background tracking. Expo SDK 57 also requires a compatible
Expo Go client; when the App Store client supports another SDK, use a development
build or matching simulator instead of treating the mismatch as an app crash.

## Configuration

Backend variables use the `MOBILITY_` prefix:

- `MOBILITY_DATABASE_URL`
- `MOBILITY_JWT_SECRET` (must be replaced outside local development)
- `MOBILITY_CORS_ORIGINS`
- `MOBILITY_ENVIRONMENT`
- `MOBILITY_DISPATCH_SEARCH_RADII_MILES` (default `2,5,10`)
- `MOBILITY_DRIVER_LOCATION_STALE_SECONDS`
- `MOBILITY_DRIVER_PRESENCE_TTL_SECONDS`
- `MOBILITY_DRIVER_MAX_ACCURACY_METERS`
- `MOBILITY_DRIVER_MAX_SPEED_MPS`
- `MOBILITY_DISPATCH_OFFER_SECONDS`
- `MOBILITY_DISPATCH_OFFER_GROUP_SIZE`

Never put server, payment, model, SMS, or telephony secrets in `EXPO_PUBLIC_*`
variables; those are bundled into the client.
