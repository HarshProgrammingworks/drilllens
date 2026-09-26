"""Feature vectors for the rule engine and for a future trained model.

These features are calculated from stored parameter samples. They are inputs
to documented rules. They are not a supervised prediction and have no accuracy claim.
"""

from __future__ import annotations

import numpy as np
from sklearn.preprocessing import StandardScaler

FIELDS = [
    "depth",
    "rop",
    "wob",
    "rpm",
    "torque",
    "standpipe_pressure",
    "mud_flow",
    "mud_weight",
    "pump_pressure",
    "hook_load",
]


def latest_and_baseline(rows: list[dict]) -> tuple[dict, dict, dict]:
    if not rows:
        empty = {name: None for name in FIELDS}
        return empty, empty, {"sample_count": 0}
    current = {name: rows[-1].get(name) for name in FIELDS}
    history = rows[:-1] if len(rows) > 1 else rows
    matrix = []
    for row in history:
        matrix.append([row.get(name) if row.get(name) is not None else np.nan for name in FIELDS])
    arr = np.array(matrix, dtype=float)
    baseline = {}
    scaled = {}
    with np.errstate(all="ignore"):
        medians = np.nanmedian(arr, axis=0)
    for idx, name in enumerate(FIELDS):
        value = medians[idx]
        baseline[name] = None if np.isnan(value) else float(value)
    usable = np.where(np.isnan(arr), np.nanmedian(arr, axis=0), arr)
    if usable.shape[0] >= 2 and not np.isnan(usable).all():
        filled = np.where(np.isnan(usable), 0.0, usable)
        try:
            transformed = StandardScaler().fit_transform(filled)
            last = transformed[-1]
            for idx, name in enumerate(FIELDS):
                scaled[name] = float(last[idx])
        except ValueError:
            scaled = {}
    features = {
        "sample_count": len(rows),
        "baseline": baseline,
        "scaled_deviation": scaled,
        "provenance": "CALCULATED",
    }
    return current, baseline, features


def percent_change(current: float | None, baseline: float | None) -> float | None:
    if current is None or baseline is None or baseline == 0:
        return None
    return (current - baseline) / abs(baseline) * 100.0
