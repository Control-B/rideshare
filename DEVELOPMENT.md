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

The current map area is a synthetic route visualization. A provider-backed native/web
map adapter and geocoding service are intentionally deferred; no fake geocoding or
route result is represented as live.

## Configuration

Backend variables use the `MOBILITY_` prefix:

- `MOBILITY_DATABASE_URL`
- `MOBILITY_JWT_SECRET` (must be replaced outside local development)
- `MOBILITY_CORS_ORIGINS`
- `MOBILITY_ENVIRONMENT`

Never put server, payment, model, SMS, or telephony secrets in `EXPO_PUBLIC_*`
variables; those are bundled into the client.
