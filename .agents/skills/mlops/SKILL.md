---
name: mlops
description: Use when building production training pipelines, setting up MLflow infrastructure, managing model registries, deploying model serving endpoints, configuring feature stores, implementing drift detection, or managing model promotion gates
---

# MLOps

## Overview

Covers the operationalisation of ML models — taking validated model artifacts from data-science and running them reliably in production. The primary output is a production ML system: an automated training pipeline, a governed model registry, and a monitoring setup.

## Scope

**Owns:** Production training pipeline design and automation, model registry and versioning, model promotion gates (experiment → staging → production), model serving and inference infrastructure, feature store serving (delivering features to models at inference time), model monitoring and drift detection, retraining triggers and automation, experiment tracking infrastructure (MLflow setup, registry configuration).

**Does not own:** Raw data pipeline management (→ `data-engineering`), model prototyping or experimentation (→ `data-science`), general container and cloud infrastructure primitives (→ `design-infrastructure`), general telemetry instrumentation (→ `observability`).

**Interfaces with:**
- `data-engineering` — mlops consumes Gold tables and feature tables produced by data-engineering
- `data-science` — mlops operationalises model artifacts and evaluation results from data-science
- `design-infrastructure` — serving infrastructure follows general container/cloud patterns from design-infrastructure
- `observability` — model metrics are defined here; trace instrumentation patterns come from observability

## When to Use

- **Trigger:** Building or modifying a production model training pipeline
- **Trigger:** Setting up or managing MLflow infrastructure (tracking server, model registry)
- **Trigger:** Defining model promotion gates (staging, production)
- **Trigger:** Deploying a model serving endpoint
- **Trigger:** Configuring model monitoring, drift detection, or retraining triggers

**Do NOT use for:**
- Raw data pipeline design or orchestration (→ `data-engineering`)
- Model prototyping or experimentation (→ `data-science`)
- General container or cloud infrastructure (→ `design-infrastructure`)

## Core Pattern

[TODO: Add model lifecycle pattern — training pipeline → registry → promotion gate → serving → monitoring loop, with MLflow as the backbone]

## Quick Reference

[TODO: Add MLflow setup patterns, promotion gate criteria, drift detection thresholds, model versioning conventions, uv integration for pipeline execution]

## Implementation

[TODO: Add MLflow infrastructure setup, training pipeline orchestration, model registry workflow, serving patterns using scikit-learn / PyTorch, monitoring and retraining trigger setup]

## Common Mistakes

[TODO: Document common operationalisation mistakes — no promotion gates, missing drift monitoring, feature skew between training and serving, MLflow artifacts not reproducible]
