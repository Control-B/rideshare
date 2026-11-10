# Deployment

The target is a portable container deployment. `docker-compose.yml` provides PostGIS,
Redis, and the API for local development. DigitalOcean can initially host the API as
a container, managed PostgreSQL, managed Redis, object storage, and a private worker.

Production sequence:

1. Build immutable images and generate an SBOM.
2. Run tests, scans, and migration validation.
3. Back up the database and run Alembic as a one-shot release job.
4. Deploy API and durable worker with health/readiness checks.
5. Deploy web output behind TLS/CDN.
6. Publish signed mobile builds through EAS after store review.
7. Verify metrics, traces, logs, error reporting, and synthetic booking checks.

Required additions include a transactional outbox worker, managed secrets, private
networking, least-privilege service identities, WAF/rate limiting, OpenTelemetry,
error reporting, alerts, point-in-time recovery, restore drills, and zero-downtime
migration practices.

Do not expose the SQLite demo, seeded accounts, permissive local secrets, or synthetic
provider adapters publicly.
