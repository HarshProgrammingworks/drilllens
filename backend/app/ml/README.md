# Machine learning boundary

No supervised drilling model is trained or shipped.

- `features/feature_builder.py` builds numeric features from stored samples.
- `inference/engine.py` defines `RiskEngine`, the active `RuleBasedRiskEngine`, and `MLRiskEngine`.
- `models/` and `training/` are reserved for a future validated model.

When a model is added, persist `model_version`, `dataset_version`, `prediction_timestamp`, features, prediction, and confidence from a real evaluation. Do not display an accuracy figure without that evaluation.
