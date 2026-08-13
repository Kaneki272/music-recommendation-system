# Model Versioning Strategy

## Rules
1. Model versions use semantic versioning: `v{major}.{minor}.{patch}`
2. A new version is created for every retrain — old versions are NEVER deleted.
3. Only one version per model type is marked `is_production=True`.
4. All artifacts (weights, config, metadata, evaluation results) are stored together.

## Artifact Directory
```
models/
  {model_type}/
    v1/
      model/          ← serialized weights
      config.yaml     ← exact hyperparameters
      metadata.json   ← ModelMetadata (training_timestamp, dataset_version, metrics)
      evaluation.json ← EvaluationResult
    v2/
      ...
```

## Dataset → Model Traceability
```
DatasetMetadata(dataset_version="2026-08-01")
          ↓
ModelMetadata(dataset_version="2026-08-01", code_version="85dc3e2")
          ↓
EvaluationResult(dataset_version="2026-08-01", model_version="v1.0.0")
```

This chain ensures every model can be traced to its exact training data and code.
