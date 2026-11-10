# Configurable Mobility Platform

An original, production-oriented foundation for a unified rider/driver product. This
repository currently implements the first end-to-end vertical slice: unified login,
interface switching, deterministic fare quotes, guest bookings, driver offers, atomic
acceptance, authoritative trip transitions, and cash collection recording.

This is an incremental MVP, not the completed multi-phase platform. Synthetic/demo
features are visibly labeled and no paid provider is activated.

## Repository layout

- `frontend/universal-app` — Expo SDK 57 universal app for iOS, Android, and web
- `backend` — FastAPI, SQLAlchemy 2, Alembic, and authoritative domain operations
- `assets` — user-supplied product references and shared media
- `docs` — architecture, API, security, compliance, deployment, and roadmap notes
- `docker-compose.yml` — PostGIS, Redis, and API development stack

## Quick start (no Docker required)

Backend:

```bash
python3.12 -m venv .venv
. .venv/bin/activate
pip install -e "backend[dev]"
cd backend
alembic upgrade head
uvicorn app.main:app --reload
```

Universal app, in another terminal:

```bash
cd frontend/universal-app
npm install
cp .env.example .env.local
npm start
```

Press `w` for web or scan the QR code with Expo Go. For a physical device, set
`EXPO_PUBLIC_API_URL` to the development machine's LAN URL, such as
`http://192.168.1.20:8000`; `localhost` points to the phone itself.

Demo accounts:

- Rider: `rider@example.test` / `demo-pass-123`
- Approved driver: `driver@example.test` / `demo-pass-123`

To exercise the complete flow, sign in as the rider and request a cash ride. In a
second browser/device, sign in as the driver, accept the offer, and advance each trip
state through completion.

## Commands

```bash
# backend
cd backend
ruff check .
pytest
alembic upgrade head

# frontend
cd frontend/universal-app
npm run lint
npx tsc --noEmit
npx expo export --platform web
```

## Expo Go versus development builds

Expo Go supports this milestone's authentication, mode switch, booking, driver
onboarding state, foreground location, simulated route display, dispatch, trip state,
and cash flow. Background driver location, production push, native payment SDKs, and
always-on driving behavior require an Expo development build. See
[`DEVELOPMENT.md`](./DEVELOPMENT.md).

## Documentation

- [Architecture](./ARCHITECTURE.md)
- [Development](./DEVELOPMENT.md)
- [API](./API.md)
- [Database](./DATABASE.md)
- [Security](./SECURITY.md)
- [Compliance](./COMPLIANCE.md)
- [Deployment](./DEPLOYMENT.md)
- [Testing](./TESTING.md)
- [Roadmap](./ROADMAP.md)
