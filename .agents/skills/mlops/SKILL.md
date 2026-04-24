---
name: mlops
description: Use when building production training pipelines, setting up MLflow infrastructure, managing model registries, deploying model serving endpoints, configuring feature stores, implementing drift detection, or managing model promotion gates
---

# MLOps

## Overview

Covers the operationalisation of ML models — taking validated model artifacts from data-science and running them reliably in production. Targets **Google MLOps Level 1**: automated continuous training (CT) pipelines with data/model validation gates, a governed model registry, and automated delivery of prediction services. The primary output is a production ML system that retrains automatically and delivers new model versions without manual intervention.

Current state in this project is **Level 0**: MLflow logs to a local SQLite database (`data/4_eval/eval_data.db`), training runs via `uv run main.py`, execution is manual. All new work should move toward Level 1.

## Scope

**Owns:** Production training pipeline design and automation, model registry and versioning, model promotion gates (experiment → staging → production), model serving and inference infrastructure, feature store serving (delivering features to models at inference time), model monitoring and drift detection, retraining triggers and automation, experiment tracking *infrastructure* (MLflow remote tracking server, model registry configuration), data/model validation *gates* (the automated decision to stop or continue the pipeline — not the validation implementation itself), ML metadata management (pipeline lineage, artifact pointers, reproducibility).

**Does not own:** Raw data pipeline management (→ `data-engineering`), model prototyping or experimentation (→ `data-science`), general container and cloud infrastructure primitives (→ `design-infrastructure`), component containerization patterns (→ `design-infrastructure`), CI/CD pipeline configuration (→ `design-infrastructure`), general telemetry instrumentation (→ `observability`), data validation *implementation* — Pydantic schema enforcement, Medallion quality gates (→ `data-engineering`).

**Interfaces with:**
- `data-engineering` — consumes Gold tables and feature tables; data validation implementation follows data-engineering's Pydantic Sandwich; mlops owns the pipeline gate *decision*
- `data-science` — operationalises model artifacts and evaluation results from data-science; experiment tracking usage patterns live in data-science
- `design-infrastructure` — component containerisation and ML CI/CD pipeline configuration follow design-infrastructure patterns; mlops defines *what* those pipelines must validate
- `observability` — model performance metrics and pipeline step telemetry are instrumented following observability patterns; drift thresholds are defined here

## When to Use

- **Trigger:** Building or modifying a production model training pipeline
- **Trigger:** Setting up or managing MLflow infrastructure (remote tracking server, model registry)
- **Trigger:** Defining or enforcing model promotion gates (staging → production)
- **Trigger:** Deploying a model serving endpoint
- **Trigger:** Configuring pipeline triggers (scheduled, on new data, on performance degradation, on drift)
- **Trigger:** Implementing data validation or model validation steps within a production pipeline
- **Trigger:** Setting up model monitoring, drift detection, or automated retraining

**Do NOT use for:**
- Raw data pipeline design or orchestration (→ `data-engineering`)
- Model prototyping or experimentation (→ `data-science`)
- General container or cloud infrastructure (→ `design-infrastructure`)
- Data validation implementation — schema enforcement, Pydantic models (→ `data-engineering`)

## Core Pattern

### Google MLOps Level 1 — Continuous Training Pipeline

The unit of deployment is the **training pipeline**, not the trained model. A new model is the output of a pipeline run, not a manually triggered script.

```
[Trigger] → [Data Validation] → [Training] → [Model Validation] → [Registry] → [Serving]
                   ↓ fail                           ↓ fail
              Stop pipeline                    Stop promotion
```

**Experimental-operational symmetry:** The same pipeline code runs in dev and production. Never maintain a "simplified dev version" — it defeats the point.

**Modularised components:** Each pipeline step is an isolated, versioned module with its own runtime. Containerisation of components follows `design-infrastructure` patterns. The mlops concern is that each step is independently testable and replaceable.

### Data Validation Gate

Runs before training. Decides automatically whether to proceed or stop and alert.

| Skew Type | Condition | Action |
|---|---|---|
| Schema skew | Unexpected features / missing features / wrong types | Stop pipeline — alert data science team |
| Distribution skew | Significant statistical drift in feature values | Trigger retraining (data patterns changed) |

Data validation *implementation* (schema contracts, Pydantic models) follows `data-engineering`. The *gate decision logic* lives here.

```python
def validate_data_or_stop(df: pl.DataFrame, schema: DataSchema) -> None:
    violations = schema.check(df)
    if violations.has_schema_skew:
        raise PipelineHaltError(f"Schema skew detected: {violations.schema_errors}")
    if violations.has_distribution_skew:
        logger.warning("Distribution skew detected — retraining triggered")
```

### Model Validation Gate

Runs after training. Decides automatically whether to promote or discard the new model.

```python
def validate_model_or_discard(
    new_model: MlflowModel,
    baseline_model: MlflowModel,
    test_df: pl.DataFrame,
) -> bool:
    new_metrics = evaluate(new_model, test_df)
    baseline_metrics = evaluate(baseline_model, test_df)

    if new_metrics["rmse"] >= baseline_metrics["rmse"]:
        return False  # New model does not beat baseline

    segment_metrics = evaluate_by_segment(new_model, test_df)
    if segment_metrics.max_variance() > SEGMENT_VARIANCE_THRESHOLD:
        return False  # Inconsistent performance across segments

    return True
```

Offline validation must pass before any promotion. Online validation (canary or A/B) follows after staging promotion.

## Quick Reference

### Pipeline Triggers

| Trigger | When to use |
|---|---|
| On demand | Ad hoc retraining, debugging, initial pipeline run |
| Scheduled | Data refreshes on a known cadence (daily, weekly) |
| On new data availability | Data arrives ad hoc; trigger on ingestion event |
| On performance degradation | Monitored metric drops below threshold |
| On concept drift | Feature distribution changes significantly |

### Promotion Gates

| Stage | Gate |
|---|---|
| Experiment → Staging | Offline model validation passes (metrics beat baseline, segment variance within threshold) |
| Staging → Production | Online validation passes (canary / A/B test over defined traffic window) |
| Rollback trigger | Production metrics degrade below rollback threshold |

### MLflow Maturity Levels

| State | Setup | When |
|---|---|---|
| Level 0 (current) | Local SQLite `data/4_eval/eval_data.db` | Prototyping only — not production |
| Level 1 (target) | Remote MLflow tracking server + model registry | When CT pipeline is in production |

### Open Standards

| Standard | Role | Tool |
|---|---|---|
| ONNX | Model serialisation format — framework-agnostic, portable across runtimes | `mlflow.onnx.log_model()` |
| OpenTelemetry | Pipeline step telemetry — spans, metrics (→ `observability`) | OTEL SDK |
| OpenLineage | Data and model lineage metadata (→ `data-engineering`) | Emitted by orchestrator |

**ONNX as default model format:** Log models as ONNX where the framework supports it. ONNX decouples the training framework (scikit-learn, PyTorch) from the serving runtime and enables cross-platform deployment without framework dependencies.

```python
import mlflow.onnx
import onnxmltools
from skl2onnx import convert_sklearn

onnx_model = convert_sklearn(trained_model, initial_types=[("input", FloatTensorType([None, n_features]))])
mlflow.onnx.log_model(onnx_model, artifact_path="model", registered_model_name="sick_leave_xgboost")
```

### Production Deployment Targets

| Platform | When to use |
|---|---|
| Kubernetes (self-managed) | Full control over serving infrastructure; follows `design-infrastructure` container standards |
| Databricks Model Serving | When training already runs on Databricks; lowest friction for Spark-native models |
| Google Cloud Vertex AI | GCP-native serving; aligns with GCP-for-ML placement from `design-infrastructure` |
| Azure ML Online Endpoints | Azure-native serving; aligns with Azure-default placement from `design-infrastructure` |

**MLflow → Docker → deployment:** MLflow can build a serving container directly from a logged model. This container is the deployment unit regardless of the target platform.

```bash
mlflow models build-docker -m "models:/sick_leave_xgboost/Production" -n sick-leave-serving
# → Docker image → Kubernetes / Vertex AI / Azure ML endpoint
```

### Naming Conventions

| Artifact | Convention |
|---|---|
| Experiment | Domain name: `sick_leave_prediction` |
| Run | `{model_name}_{feature_set}` |
| Registered model | `{domain}_{algorithm}` e.g. `sick_leave_xgboost` |
| Model version tags | `staging`, `production`, `archived` |

## Implementation

### MLflow Infrastructure (Level 1 Target)

MLflow remote tracking server replaces the local SQLite setup. Model registry enables governed promotion.

```python
import mlflow

# Set remote tracking URI — configured via env var in production
mlflow.set_tracking_uri(os.environ["MLFLOW_TRACKING_URI"])
mlflow.set_experiment("sick_leave_prediction")

with mlflow.start_run(run_name=f"{model_name}_{feature_set}"):
    mlflow.log_params({
        "model": model_name,
        "features": feature_set,
        "target": TARGET_COLUMN,
        "n_train": len(X_train),
        "random_seed": RANDOM_SEED,
        "data_version": data_version,        # Dataset record count or hash
    })
    model.fit(X_train, y_train)
    mlflow.log_metrics({"rmse": rmse, "mae": mae, "r2": r2})
    mlflow.sklearn.log_model(model, artifact_path="model",
                             registered_model_name=f"sick_leave_{model_name}")
```

### Model Registry — Promotion Flow

```python
from mlflow.tracking import MlflowClient

client = MlflowClient()

def promote_to_staging(run_id: str, model_name: str, version: str) -> None:
    client.transition_model_version_stage(
        name=model_name, version=version, stage="Staging"
    )

def promote_to_production(model_name: str, version: str) -> None:
    # Archive current production version first
    prod_versions = client.get_latest_versions(model_name, stages=["Production"])
    for v in prod_versions:
        client.transition_model_version_stage(
            name=model_name, version=v.version, stage="Archived"
        )
    client.transition_model_version_stage(
        name=model_name, version=version, stage="Production"
    )
```

### ML Metadata Management

Every pipeline run must record the following via MLflow params and tags. This enables reproducibility, rollback, and lineage tracing.

```python
mlflow.set_tags({
    "pipeline_version": PIPELINE_VERSION,
    "data_source": "gold_sick_leave",
    "data_record_count": str(len(df)),
    "training_start": datetime.utcnow().isoformat(),
    "previous_model_version": current_production_version,
})
```

Artifacts logged per run:
- Trained model (`model/`)
- Validation anomaly report (`data_validation_report.json`)
- Evaluation metrics per segment (`segment_metrics.json`)
- Feature importance (`feature_importance.csv`)

### Pipeline Entrypoint

```bash
uv run main.py                     # Manual trigger — existing Gold tables
uv run main.py --refresh-data      # Full pipeline — rebuild Gold then train
uv run main.py --validate-only     # Data validation gate only — no training
```

At Level 1, these entrypoints are called by an orchestrator (e.g., Vertex AI Pipelines for GCP-hosted training), not manually.

### Feature Store (Optional Level 1 Component)

A feature store centralises feature definitions and prevents training-serving skew. It is optional at Level 1 but critical if online prediction is in scope.

| Use case | Source |
|---|---|
| Experimentation (offline extract) | Feature store batch read |
| Continuous training | Feature store batch read (fresh values) |
| Online prediction | Feature store low-latency real-time read |

The feature store API serves the same feature values for training and serving — this is the primary mechanism for eliminating training-serving skew. Feature *definitions* live in `data-science`; feature *pipeline implementation* lives in `data-engineering`; feature *serving at inference time* is owned here.

## Common Mistakes

**Deploying a model instead of a pipeline.**
At Level 1 the unit of deployment is the training pipeline. Deploying only the trained artifact means retraining requires manual intervention — that is Level 0.

**No data validation gate before training.**
Without schema skew detection, silent data quality failures produce silently degraded models. The pipeline must halt on schema violations.

**Promoting a model that beats overall metrics but has high segment variance.**
A model that improves average RMSE but degrades performance on a specific segment is not ready for production. Segment-level evaluation is mandatory in the model validation gate.

**Training-serving skew from separate feature computation.**
If features are computed differently during training (offline batch) and serving (online inference), the model performance will degrade in production. The feature store or identical feature pipeline code in both paths is the fix.

**MLflow run names left as auto-generated UUIDs.**
Always set `run_name = f"{model_name}_{feature_set}"`. Unnamed runs are unscannable in the registry.

**Missing metadata on MLflow runs.**
Without `data_version`, `pipeline_version`, and `previous_model_version` logged as params/tags, you cannot reproduce a run or trace lineage after a rollback.

**Mixing Level 0 and Level 1 patterns.**
Do not log to the local SQLite MLflow store while building a CT pipeline. Once CT is in scope, the remote tracking server is required — local SQLite has no registry API.

**No promotion gate between staging and production.**
Offline model validation alone is not sufficient. A canary or A/B deployment with a defined traffic window and rollback criterion is required before full production promotion.
