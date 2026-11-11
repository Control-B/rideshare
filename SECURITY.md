# Security

The current slice uses Argon2 password hashing, short-scope JWT bearer authentication,
server-side role/object authorization, Pydantic validation, CORS allow-lists,
idempotency constraints, and immutable trip event history.

Before production:

- replace the development JWT secret with managed secret storage and rotate keys
- add refresh-token rotation, revocation, email verification, MFA, and recovery
- enforce TLS, trusted hosts, rate limits, abuse controls, and device/session review
- encrypt sensitive profile/document fields and define deletion/retention workflows
- add signed webhook verification and replay protection for every provider
- tokenize payments only through a compliant marketplace processor
- use signed, short-lived, scoped guest tracking links
- redact phone numbers, tokens, addresses, and provider payloads from logs
- add SAST, dependency, container, IaC, and secret scanning
- complete threat modeling and independent penetration/accessibility reviews

The demo endpoint and seeded credentials must be disabled in production. The frontend
contains no server secrets. Client role checks improve UX only; backend checks are
authoritative.

Driver location is accepted only for approved drivers and is checked for timestamp,
accuracy, and impossible-speed anomalies. An anomaly creates a review event; it does
not automatically suspend a driver. Pre-assignment nearby-vehicle responses round
coordinates to reduce unnecessary precision. Production must additionally enforce
location retention/deletion policy, encrypt sensitive history, rate-limit ingestion,
and restrict fraud-review access.

WebSocket authentication currently uses the bearer token as a query parameter because
browser WebSocket APIs cannot set authorization headers. Production should issue a
short-lived, single-purpose socket ticket and ensure URLs are redacted from logs.

The current cash ledger is a minimal balanced trip record, not a complete accounting
subledger. Refund, reconciliation, chargeback, subscription, payout, and immutable
batch controls remain production blockers.
