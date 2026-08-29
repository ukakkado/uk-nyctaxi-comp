---
status: decided
date: 2026-08-29
---

# Utilisation rate denominator is total presence time, including break

The utilisation rate for zone-level (and by extension, any location-level) time analysis uses total interval time as the denominator — including BREAK status. The numerator is ON_TRIP time. This measures "what fraction of time present in the zone was earning," not "what fraction of active working time was earning."

## Considered Options

- **Total presence (chosen).** Denominator = all interval time in the zone (ON_TRIP + AVAILABLE + DISPATCHED + BREAK). Numerator = ON_TRIP. This answers "how much of the time cars were in this zone did they earn?" Break time is real zone presence — a car on break in a zone is a car not earning there.

- **Net utilisation excluding break.** Denominator = total minus BREAK. This answers "when the car was available to work, how often was it earning?" Useful for driver-level productivity analysis, but misleading at the zone level: a zone where drivers take long breaks would appear more utilised than a zone where they stay available, even if the earning time is the same.

## Consequences

- Zone utilisation rates are structurally lower than driver-level occupancy rates, because break time inflates the denominator. This is intentional — the metric measures zone productivity, not driver productivity.
- Consumers who want a net measure can compute it from the exposed `break_hours` and `on_trip_hours` columns.
- Any future location-level utilisation metric (garage, borough, etc.) should use the same denominator convention unless an ADR explicitly overrides it for that context.
