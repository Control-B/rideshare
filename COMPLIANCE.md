# Compliance

Software configuration is not regulatory approval. Counsel and licensed insurance,
transportation, privacy, accessibility, tax, and payment specialists must approve each
market and operating mode before activation.

For an initial Florida review, the team must validate current Florida Statute 627.748
and all applicable local taxi/fleet rules, including definitions that may differ for
app, telephone, cash, prearranged, fleet, airport, and accessibility workflows.

Unresolved production gates:

- TNC versus taxi/fleet classification by booking channel
- operating authority and service-area permissions
- commercial auto insurance periods and proof
- driver screening, licensing, permits, inspections, and adverse-action process
- fare disclosure, receipts, cancellation, cash, taxes, and complaint handling
- airport and special-zone rules
- ADA/accessibility and service-animal handling
- minors and third-party/guest passenger consent
- telephone recording disclosure and retention
- SMS consent and opt-out requirements
- precise/background location retention and user rights
- PCI/marketplace payments, unclaimed funds, cash reconciliation, and payouts

The architecture keeps operating mode and market compliance as server-side policy.
A future compliance module must block activation until required reviews are explicitly
recorded, versioned, and auditable.
