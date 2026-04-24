---
name: observability
description: Use when setting up telemetry instrumentation, configuring OpenTelemetry, defining structured logging standards, adding trace spans, or establishing metrics collection in any service or pipeline
---

# Observability

## Overview

Establishes consistent telemetry instrumentation across all services and pipelines using **OpenTelemetry** as the unified, vendor-neutral standard. The three pillars — logs, traces, and metrics — are correlated via a shared `trace_id`. For data pipelines, **OpenLineage** (with **Marquez** as the open-source reference backend) provides data lineage metadata alongside OTel telemetry. Exporters route to Azure Monitor (Azure-hosted services) or GCP Cloud Monitoring (GCP-hosted ML workloads), following placement rules from `design-infrastructure`.

## Scope

**Owns:** OpenTelemetry SDK setup and configuration, structured logging standards and field conventions, trace and span instrumentation patterns, metrics collection and naming conventions, log-trace-metric correlation patterns, OpenLineage instrumentation pattern (how to emit lineage events — not the Marquez deployment).

**Does not own:** Log storage, routing, or alerting infrastructure (→ `design-infrastructure`), Marquez server deployment (→ `design-infrastructure`), business metric definitions — defined in domain skills, instrumented here, model performance monitoring thresholds and drift trigger logic (→ `mlops`), OpenLineage event emission from pipeline steps (→ `data-engineering`).

**Interfaces with:**
- `design-infrastructure` — observability defines what to emit; infrastructure defines where it goes (Azure Monitor, GCP Cloud Monitoring, Marquez)
- `mlops` — model metrics and pipeline step spans follow patterns defined here; thresholds and retraining trigger logic live in mlops
- `data-engineering` — OpenLineage events are emitted from pipeline steps per data-engineering patterns; instrumentation standard is defined here
- `design-system` — vendor neutrality constraint mandates OpenTelemetry over proprietary SDKs

## When to Use

- **Trigger:** Adding logging, tracing, or metrics to any service or pipeline
- **Trigger:** Setting up OpenTelemetry SDK in a new project
- **Trigger:** Standardising telemetry across services with inconsistent logging
- **Trigger:** Debugging via traces or correlating logs across services
- **Trigger:** Instrumenting ML pipeline steps (data validation, training, model validation, promotion)

**Do NOT use for:**
- Log storage backends, routing, or alerting rules (→ `design-infrastructure`)
- Model drift thresholds and retraining triggers (→ `mlops`)
- Marquez server setup (→ `design-infrastructure`)
- OpenLineage event emission logic in pipeline code (→ `data-engineering`)

## Core Pattern

### Three Pillars, One Trace ID

Every log record, span, and metric for a given request or pipeline run shares a `trace_id`. This is the correlation key — without it, debugging across services requires manual log hunting.

```
Request/Pipeline Run
├── Trace (trace_id: abc123)
│   ├── Span: data_validation   → attributes: step, model, pipeline_version
│   ├── Span: training          → attributes: model_name, n_samples, run_id
│   └── Span: model_validation  → attributes: rmse, baseline_rmse, passed
├── Logs (trace_id: abc123, span_id: ...)
│   └── Structured JSON with standard fields
└── Metrics (labels: model_name, pipeline_version)
    └── ml.model.rmse, ml.model.drift_score
```

### OpenTelemetry — Vendor-Neutral by Default

Never use a proprietary SDK (e.g., Azure Application Insights SDK, Google Cloud Logging client) directly. Instrument with OTel; route via an exporter. Swapping cloud targets means changing the exporter, not the instrumentation.

```python
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# Replace exporter without touching instrumentation code
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

provider = TracerProvider()
provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
trace.set_tracer_provider(provider)

tracer = trace.get_tracer(__name__)
meter  = metrics.get_meter(__name__)
```

### OpenLineage + Marquez — Data Lineage

**OpenLineage** is the open API spec for emitting and exchanging data lineage metadata — the standard defines the event format and REST API, not the storage backend. **Marquez** is the open-source reference implementation of the OpenLineage repository — it receives OpenLineage events, stores lineage metadata, and serves it via the OpenLineage API. Marquez is compatible with tools such as OpenMetadata and Apache Atlas.

The instrumentation pattern (how to emit lineage events) is owned here. The emission logic in pipeline steps is owned by `data-engineering`. The Marquez server deployment is owned by `design-infrastructure`.

```python
from openlineage.client import OpenLineageClient, RunEvent, RunState, Run, Job
from openlineage.client.models import Dataset

client = OpenLineageClient.from_environment()  # OPENLINEAGE_URL env var → Marquez

client.emit(RunEvent(
    eventType=RunState.COMPLETE,
    run=Run(runId=run_id),
    job=Job(namespace="sick_leave_pipeline", name="silver_transformation"),
    inputs=[Dataset(namespace="sqlite", name="bronze_sick_leave")],
    outputs=[Dataset(namespace="sqlite", name="silver_sick_leave")],
))
```

## Quick Reference

### Exporter Selection

| Target | Exporter | When |
|---|---|---|
| Azure Monitor | `azure-monitor-opentelemetry` | Azure-hosted services (default placement) |
| GCP Cloud Monitoring | `opentelemetry-exporter-gcp-monitoring` | GCP-hosted ML workloads |
| Local / dev | `ConsoleSpanExporter` | Development and testing only |
| Marquez | `openlineage-python` via `OPENLINEAGE_URL` | Data pipeline lineage |

### Span Naming Conventions

| Context | Span name | Key attributes |
|---|---|---|
| API request | `{method} {route}` e.g. `POST /v1/predict` | `http.status_code`, `user_id` |
| ML pipeline step | `{step_name}` e.g. `data_validation` | `pipeline_version`, `run_id`, `model_name` |
| DB query | `{db.operation} {db.table}` | `db.system`, `db.statement` |
| External call | `{http.method} {host}` | `http.url`, `http.status_code` |

### Metric Naming Conventions

| Domain | Pattern | Example |
|---|---|---|
| ML model | `ml.<model_name>.<metric>` | `ml.model.rmse`, `ml.model.drift_score` |
| Pipeline | `pipeline.<name>.<metric>` | `pipeline.training.duration_seconds` |
| API | `http.server.request.duration` | OTel semantic convention |
| Data quality | `data.<tier>.<check>` | `data.gold.null_count` |

### Standard Structured Log Fields

Every log record must include these fields. Additional domain-specific fields are added on top.

| Field | Type | Required |
|---|---|---|
| `trace_id` | string | Always — correlation key |
| `span_id` | string | Always |
| `service.name` | string | Always — OTel resource attribute |
| `severity` | string | Always (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `message` | string | Always |
| `pipeline_version` | string | Pipeline runs |
| `run_id` | string | Pipeline runs |
| `step_name` | string | Pipeline steps |
| `model_name` | string | ML steps |

## Implementation

### SDK Initialisation

Configure once at application startup. Use environment variables for exporter targets — never hardcode endpoints.

```python
import os
from opentelemetry import trace, metrics
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

resource = Resource.create({"service.name": os.environ["SERVICE_NAME"]})

tracer_provider = TracerProvider(resource=resource)
tracer_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
trace.set_tracer_provider(tracer_provider)

meter_provider = MeterProvider(resource=resource)
metrics.set_meter_provider(meter_provider)

tracer = trace.get_tracer(__name__)
meter  = metrics.get_meter(__name__)
```

### Structured Logging with Trace Correlation

```python
import logging
import json
from opentelemetry import trace

class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        span = trace.get_current_span()
        ctx  = span.get_span_context()
        return json.dumps({
            "severity":  record.levelname,
            "message":   record.getMessage(),
            "trace_id":  format(ctx.trace_id, "032x") if ctx.is_valid else None,
            "span_id":   format(ctx.span_id,  "016x") if ctx.is_valid else None,
            "service":   record.name,
        })

handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
logging.basicConfig(handlers=[handler], level=logging.INFO)
```

### ML Pipeline Step Instrumentation

```python
with tracer.start_as_current_span("data_validation") as span:
    span.set_attribute("pipeline_version", PIPELINE_VERSION)
    span.set_attribute("run_id", run_id)
    span.set_attribute("model_name", model_name)
    span.set_attribute("input_record_count", len(df))
    result = validate_data(df)
    span.set_attribute("validation_passed", result.passed)
    if not result.passed:
        span.set_status(trace.StatusCode.ERROR, result.error_message)
```

### Model Performance Metrics

```python
rmse_gauge  = meter.create_gauge("ml.model.rmse")
drift_gauge = meter.create_gauge("ml.model.drift_score")

labels = {"model_name": model_name, "pipeline_version": PIPELINE_VERSION, "run_id": run_id}
rmse_gauge.set(rmse_value, labels)
drift_gauge.set(drift_score, labels)
```

Threshold values that determine whether these metrics are acceptable live in `mlops`.

### Azure Monitor Exporter

```bash
uv add azure-monitor-opentelemetry
```

```python
from azure.monitor.opentelemetry import configure_azure_monitor
configure_azure_monitor(connection_string=os.environ["APPLICATIONINSIGHTS_CONNECTION_STRING"])
# Replaces manual TracerProvider setup — configures traces, metrics, logs together
```

### GCP Cloud Monitoring Exporter

```bash
uv add opentelemetry-exporter-gcp-monitoring opentelemetry-exporter-gcp-trace
```

```python
from opentelemetry.exporter.cloud_monitoring import CloudMonitoringMetricsExporter
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter

tracer_provider.add_span_processor(BatchSpanProcessor(CloudTraceSpanExporter()))
meter_provider  = MeterProvider(metric_readers=[PeriodicExportingMetricReader(CloudMonitoringMetricsExporter())])
```

## Common Mistakes

**Using print() or a proprietary logging SDK instead of structured logging.**
`print()` is unsearchable. A proprietary SDK (e.g., direct Azure App Insights calls) creates vendor lock-in — changing cloud targets requires re-instrumentation. Use the OTel SDK; swap exporters.

**Missing `trace_id` on log records.**
Without the correlation key, debugging a failed pipeline run means manually matching timestamps across log streams. Every log record must carry `trace_id` and `span_id`.

**Defining metric threshold values in observability code.**
Thresholds (e.g., "RMSE > 0.15 triggers retraining") belong in `mlops`. Observability only emits the value.

**One giant root span instead of per-step spans.**
A single span covering an entire pipeline run tells you the pipeline succeeded or failed, nothing more. Emit one span per logical step so you can pinpoint which step failed and how long each took.

**Missing span attributes.**
A span named `training` with no attributes is unsearchable. Always set `pipeline_version`, `run_id`, `model_name`, and the key outcome attribute (e.g., `validation_passed`, `rmse`) on every span.

**Using `ConsoleSpanExporter` in production.**
Console exporter is for local development only. Production must route to Azure Monitor or GCP Cloud Monitoring via the appropriate exporter.
