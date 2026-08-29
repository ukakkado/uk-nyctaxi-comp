# Verify: Zone by Month Utilisation

## Reviewer verdicts

```json
{
  "verdict": "APPROVE_WITH_WARNINGS",
  "findings": [
    {
      "severity": "WARNING",
      "description": "The zone-filter rationale cited a non-existent column (is_unresolved_borough) and falsely claimed agg_zone_occupancy_hourly filters unresolved zones. Fixed: corrected to is_unresolved_zone and noted that the hourly model does NOT filter these.",
      "status": "RESOLVED"
    },
    {
      "severity": "WARNING",
      "description": "The design said status code handling 'matches agg_zone_occupancy_hourly convention exactly' but column names diverge. Fixed: qualified the claim to note that bucketing logic matches but column names differ per intent mandate.",
      "status": "RESOLVED"
    },
    {
      "severity": "INFO",
      "description": "Name the safe_divide macro for utilisation_rate to stay consistent with every other agg model.",
      "status": "RESOLVED"
    }
  ],
  "summary": "Design record is technically complete — all 9 acceptance units addressed, grain unambiguous, model buildable. Two warning-level rationale errors corrected. No redesign needed."
}
```
