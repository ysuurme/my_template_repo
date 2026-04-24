---
name: data-science
description: Use when performing exploratory data analysis, designing features, prototyping models, evaluating model quality, conducting statistical analysis, or refactoring notebooks into production modules
---

# Data Science

## Overview

Covers the exploratory and experimental work that produces model prototypes, feature designs, and analytical insights. The primary output is a validated model artifact and the feature specification that data-engineering will implement at scale.

## Scope

**Owns:** Exploratory data analysis (EDA), feature selection and design (deciding what to compute, not how to compute it at scale), model prototyping and evaluation, statistical analysis and hypothesis testing, notebook-to-module refactoring patterns, experiment tracking usage — running experiments, logging metrics, comparing runs.

**Does not own:** Feature pipeline implementation at scale (→ `data-engineering`), production model deployment or serving (→ `mlops`), experiment tracking infrastructure — registry setup and model promotion gates (→ `mlops`), data pipeline orchestration (→ `data-engineering`).

**Interfaces with:**
- `data-engineering` — data-science designs features; data-engineering builds the production pipeline
- `mlops` — data-science produces model artifacts and evaluation results; mlops operationalises them
- `code-quality` — notebook-to-module refactoring is enforced by code-quality standards

## When to Use

- **Trigger:** Performing EDA on a new dataset
- **Trigger:** Designing or selecting features for a model
- **Trigger:** Prototyping, training, or evaluating a model in a notebook or script
- **Trigger:** Running experiments and comparing results with MLflow
- **Trigger:** Refactoring a notebook into a production-ready module

**Do NOT use for:**
- Building the production feature pipeline (→ `data-engineering`)
- Deploying or serving a model (→ `mlops`)
- Setting up MLflow infrastructure or model registry (→ `mlops`)

## Core Pattern

[TODO: Add EDA pattern, feature design handoff format to data-engineering, model evaluation standard]

## Quick Reference

[TODO: Add experiment tracking usage patterns, notebook-to-module refactoring checklist, evaluation metric standards, MLflow logging patterns]

## Implementation

[TODO: Add stack-specific patterns: notebook conventions with uv, MLflow experiment tracking usage, scikit-learn / PyTorch prototyping patterns, model evaluation framework]

## Common Mistakes

[TODO: Document common mistakes — EDA not reproducible, feature design not documented for handoff to data-engineering, experiment results not logged to MLflow]
