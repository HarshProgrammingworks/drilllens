# DrillLens risk rules

The active engine is `RuleBasedRiskEngine` version 1.0.0. It is decision support. A score is an indicator, not a prediction that an event will occur, and not an instruction to change a drilling parameter.

Confidence increases when recent samples, nearby wells, formation, and stored evidence are present. It is analytical confidence in the indicator. It is not a probability and it is not model accuracy. No accuracy percentage is published because no supervised model has been trained or validated.

## Levels

| Score | Level |
| --- | --- |
| 0–29 | LOW |
| 30–59 | MODERATE |
| 60–79 | HIGH |
| 80–100 | CRITICAL |

Administrators can change the bounds. The stored rule is `low < moderate < high < 100`. Alerts are created when a score reaches `alert_min_score` (default 60). The same well and category will not create another alert until the cooldown expires, unless severity increases.

## Rules

Baselines are the median of recent stored samples for that well. Percent changes are `(current - baseline) / baseline`.

### Stuck pipe

If torque rises by at least the configured torque-rise percent (default 15%) and ROP is not increasing, add 40. Historical stuck-pipe evidence from the well or wells within 25 km adds up to 30. A smaller torque rise without the ROP condition adds 18.

### Kick / overpressure

If standpipe pressure rises by at least the configured pressure-rise percent (default 10%), add 28. A similar pump-pressure rise adds 18. Kick or overpressure evidence adds more when a pressure rule has already fired.

### Lost circulation

If mud flow falls by at least the configured flow-change percent (default 12%), add 34. A pump-pressure drop with stable mud weight adds 16. Lost-circulation evidence adds more when a flow rule has fired.

### Torque anomaly

If absolute torque change exceeds the torque-rise percent, add 36. This is recorded separately from the stuck-pipe combination so a torque change is visible even when ROP has not dropped.

### Mud problems

If mud weight changes by 4% or more versus baseline, add 30. Historical mud evidence adds up to 25.

### Cementing

If the current operation text contains cementing, add 20. A hook-load change of 15% or more during that operation adds 20. Historical cementing evidence adds up to 30.

## Evidence

Evidence rows are created only from report extraction or from explicit DEMO seed records. The engine never writes an excerpt that was not stored.

## Future model

`MLRiskEngine` raises an error until a trained model, dataset version, and evaluation record exist. Feature vectors may be stored beside rule results for a later training set. scikit-learn `StandardScaler` is used only to describe recent deviation. It is not a classifier.
