---
name: observability
description: Use when setting up telemetry instrumentation, configuring OpenTelemetry, defining structured logging standards, adding trace spans, or establishing metrics collection in any service or pipeline
---

# Observability

## Overview

Establishes consistent telemetry instrumentation across all services and pipelines using OpenTelemetry as the unified standard. Ensures logs, traces, and metrics are correlated and structured for effective querying and alerting.

## Scope

**Owns:** OpenTelemetry SDK setup and configuration, structured logging standards and field conventions, trace and span instrumentation patterns, metrics collection and naming conventions, log-trace-metric correlation patterns.

**Does not own:** Log storage, routing, or alerting infrastructure (→ `design-infrastructure`), business metric definitions — defined in domain skills, instrumented here, model performance monitoring and drift metrics (→ `mlops`).

**Interfaces with:**
- `design-infrastructure` — observability defines what to emit; infrastructure defines where it goes
- `mlops` — model metrics are defined in mlops; general trace instrumentation patterns come from here
- `design-system` — vendor neutrality constraint in design-system mandates OpenTelemetry over proprietary logging

## When to Use

- **Trigger:** Adding logging, tracing, or metrics to any service or pipeline
- **Trigger:** Setting up OpenTelemetry SDK in a new project
- **Trigger:** Standardising telemetry across services that use inconsistent logging approaches
- **Trigger:** Debugging via traces or correlating logs across services

**Do NOT use for:**
- Log storage backends, routing, or alerting rules (→ `design-infrastructure`)
- Model drift and performance monitoring (→ `mlops`)

## Core Pattern

[TODO: Add OpenTelemetry SDK setup pattern, structured log format, trace/span instrumentation example]

## Quick Reference

[TODO: Add fields table for structured logs, span naming conventions, metrics naming conventions]

## Implementation

[TODO: Add SDK initialisation code, exporter configuration for Azure Monitor and GCP Cloud Monitoring, correlation ID propagation pattern]

## Common Mistakes

[TODO: Document common instrumentation mistakes — fragmented logging, missing correlation IDs, proprietary SDK lock-in]
