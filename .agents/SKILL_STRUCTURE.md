# Skill Structure

Master reference for the MECE skill system. Check this before writing or updating any skill to verify scope placement and avoid overlap.

---

## Structure

```
Layer 1 – Foundation        code-quality · git-workflow
Layer 2 – Design            design-system · design-infrastructure · observability
Layer 3 – Domain Build      data-engineering · data-science · mlops · application-development · agentic-development
Meta                        write-skills
```

---

## Layer 1 — Foundation

### `code-quality`
**Primary artifact:** Reviewed, compliant Python code

**Owns:** Python syntax standards (PEP-8, type hints, naming), function and module structure (indentation limits, size limits, guard clauses), TDD enforcement (pytest/unittest, mocking, failing test first), testing strategy taxonomy (UI / Contract / Integration / Unit), code review feedback format, standard library vs third-party dependency decisions.

**Does not own:** System or domain model design (→ `design-system`), domain-specific implementation patterns (→ domain skills), git operations or PR creation (→ `git-workflow`).

**Interfaces with:** `design-system` — architectural constraints propagate to code-level enforcement. Domain skills — code-quality applies universally.

---

### `git-workflow`
**Primary artifact:** Linked branch → commit → PR tied to a GitHub Issue

**Owns:** Branch naming (`feature/issue-N`), commit message format (`feat(#N): Title`), PR creation with issue auto-close (`Closes #N`), error handling for git/gh commands, agent-driven automation of the full branch → PR flow.

**Does not own:** CI/CD pipeline configuration (→ `design-infrastructure`), code review standards (→ `code-quality`).

**Interfaces with:** `design-infrastructure` — CI/CD runs on the branches and PRs this skill creates.

---

## Layer 2 — Design

### `design-system`
**Primary artifact:** Domain model with defined boundaries and dependency rules

**Owns:** Domain model design (entities, value objects, aggregates), bounded context definition and anti-corruption layers, dependency direction rules (hexagonal / clean architecture), port and adapter interface definitions, architectural drift detection, foundational data & AI system patterns (Pipes & Filters, Layers, Hub-and-Spoke).

**Does not own:** Container or cloud resource configuration (→ `design-infrastructure`), telemetry instrumentation (→ `observability`), code-level quality rules (→ `code-quality`), domain-specific implementation patterns (→ domain skills).

**Interfaces with:** `design-infrastructure`, `code-quality`, domain skills.

---

### `design-infrastructure`
**Primary artifact:** Deployable, secure execution environment (containers, IaC, CI/CD)

**Owns:** Dockerfile construction (multi-stage, rootless, health checks), Terraform module structure and remote state management, CI/CD pipeline configuration (including ML pipeline CI/CD), Azure and GCP identity/networking/secrets standards, multi-cloud placement decisions (Azure default, GCP for ML/BigQuery), Traefik reverse proxy for self-managed container environments, Marquez server deployment, IAM server deployment (Keycloak, Zitadel).

**Does not own:** Application domain modelling (→ `design-system`), telemetry SDK instrumentation (→ `observability`), model serving infrastructure (→ `mlops`).

**Interfaces with:** `design-system`, `observability`, `mlops`.

---

### `observability`
**Primary artifact:** Instrumented system emitting correlated logs, traces, and metrics

**Owns:** OpenTelemetry SDK setup and configuration, structured logging standards and field conventions, trace and span instrumentation patterns, metrics collection and naming conventions, log-trace-metric correlation, OpenLineage instrumentation pattern (how to emit lineage events — not the Marquez deployment or pipeline emission logic).

**Does not own:** Log storage, routing, or alerting infrastructure (→ `design-infrastructure`), business metric definitions (defined in domain skills, instrumented here), model performance thresholds and drift trigger logic (→ `mlops`), OpenLineage event emission from pipeline steps (→ `data-engineering`), Marquez server deployment (→ `design-infrastructure`).

**Interfaces with:** `design-infrastructure`, `mlops`, `data-engineering`.

---

## Layer 3 — Domain Build

### `data-engineering`
**Primary artifact:** Validated, ML-ready datasets and feature tables

**Owns:** ELT pipeline design and implementation (Raw → Bronze → Silver → Gold Medallion), SQLAlchemy Core (Bronze bulk inserts) and ORM (Silver/Gold), SQLModel for unified Pydantic + SQLAlchemy models, Pydantic boundary validation (Sandwich pattern), Polars for pipeline data transformations (single-machine), PySpark for distributed pipeline transformations, DuckDB query engine, DuckLake storage backend (PostgreSQL catalog + Parquet), data quality gates and schema validation, feature pipeline *implementation* (computing features at scale), OpenLineage event emission from pipeline steps, Dagster Software-Defined Assets (optional, mature setup), integration testing for ETL outputs (row counts, unique IDs, date ranges).

**Does not own:** Feature *design* — which features to compute (→ `data-science`), feature *serving* at inference time (→ `mlops`), model training pipelines (→ `mlops`), statistical analysis or EDA (→ `data-science`), Marquez server deployment (→ `design-infrastructure`).

**Interfaces with:** `data-science`, `mlops`, `design-system`, `design-infrastructure`, `observability`.

---

### `data-science`
**Primary artifact:** Model prototypes, evaluation results, and analytical insights

**Owns:** Exploratory data analysis (EDA), feature selection and design (deciding what to compute, not how to compute it at scale), model prototyping and evaluation, statistical analysis and hypothesis testing, Marimo notebooks (default format — `.py`, reactive, agent-readable), Pandas for EDA/prototyping (single-machine default), notebook-to-module refactoring patterns, experiment tracking *usage* (running experiments, logging metrics, comparing runs).

**Does not own:** Feature pipeline *implementation* at scale (→ `data-engineering`), production model deployment or serving (→ `mlops`), experiment tracking *infrastructure* (→ `mlops`), data pipeline orchestration (→ `data-engineering`).

**Interfaces with:** `data-engineering`, `mlops`, `code-quality`.

---

### `mlops`
**Primary artifact:** Production ML system (training pipeline, serving endpoint, monitoring)

**Owns:** Production training pipeline design and automation (Google MLOps Level 1 target), model registry, versioning, and promotion gates (experiment → staging → production), model serving and inference infrastructure, ONNX as standard model serialisation format, MLflow infrastructure (remote tracking server, model registry), feature store serving, model monitoring, drift detection, and retraining triggers, data/model validation *gates* (automated pipeline stop/continue decisions), ML metadata management (lineage, artifact pointers, reproducibility), pipeline triggers (scheduled, on new data, on degradation, on drift).

**Does not own:** Raw data pipeline management (→ `data-engineering`), model prototyping (→ `data-science`), general container and cloud infrastructure primitives (→ `design-infrastructure`), data validation *implementation* — schema enforcement, Pydantic models (→ `data-engineering`), general telemetry instrumentation (→ `observability`).

**Interfaces with:** `data-engineering`, `data-science`, `design-infrastructure`, `observability`.

---

### `application-development`
**Primary artifact:** Production API or service

**Owns:** REST API design (FastAPI, Pydantic-native, auto OpenAPI), GraphQL Query API (Strawberry + FastAPI), input validation and serialisation (Pydantic / SQLModel), authentication and authorisation patterns, IAM backend selection (Keycloak for internal employees, Zitadel for B2B SaaS tenants), background task patterns, service-to-service communication, contract testing for REST and GraphQL APIs.

**Does not own:** Domain modelling (→ `design-system`), infrastructure and deployment (→ `design-infrastructure`), agent-specific API patterns (→ `agentic-development`), model serving infrastructure (→ `mlops`), IAM server deployment (→ `design-infrastructure`).

**Interfaces with:** `design-system`, `design-infrastructure`, `agentic-development`.

---

### `agentic-development`  ⚠️ PENDING USER INPUTS
**Primary artifact:** Functioning agent (tool use, multi-agent coordination, structured outputs)

**Owns:** Claude API usage patterns (tool use, structured outputs, streaming), agent loop design and state management, multi-agent coordination patterns, tool definition, validation, and error handling, context window and prompt management, agent testing patterns.

**Does not own:** General API development patterns (→ `application-development`), agent deployment infrastructure (→ `design-infrastructure`), data pipeline patterns used by agents (→ `data-engineering`), model serving infrastructure (→ `mlops`).

**Interfaces with:** `application-development`, `design-infrastructure`, `git-workflow`.

**Status:** Scope defined. Core Pattern, Quick Reference, Implementation, and Common Mistakes are [TODO] — awaiting user inputs on Claude API usage, tool use patterns, agent loop design, and multi-agent coordination preferences.

---

## Meta

### `write-skills`
**Primary artifact:** Valid, MECE-compliant SKILL.md

**Owns:** Skill creation standards and SKILL.md template, validation process (baseline → draft → verify), MECE enforcement and split detection, routing signal format, ASO (Agent Search Optimization) rules.

**Does not own:** Project-specific agent instructions (→ `CLAUDE.md` / `AGENT.md`), individual skill content.

**Interfaces with:** All other skills — defines the contract every skill must follow.

---

## Explicit Boundary Rules

Shared concerns that appear across multiple domains. Ownership is fixed here to prevent duplication.

| Concern | Owner | Notes |
|---|---|---|
| Feature design (what to compute) | `data-science` | |
| Feature pipeline (computing at scale) | `data-engineering` | |
| Feature serving (at inference time) | `mlops` | |
| Experiment tracking usage (running experiments) | `data-science` | |
| Experiment tracking infrastructure (MLflow setup, registry) | `mlops` | |
| Model evaluation during prototyping | `data-science` | |
| Model promotion gates (staging → production) | `mlops` | |
| Training data pipeline | `data-engineering` | It's a pipeline; model training is mlops |
| Batch inference pipeline | `mlops` | Executes a model; data movement patterns from data-engineering apply |
| Container and cloud primitives | `design-infrastructure` | |
| Model serving infrastructure | `mlops` | General container patterns from design-infrastructure |
| Business metric definitions | Domain skill that owns the domain | Instrumentation pattern from observability |
| Telemetry SDK instrumentation | `observability` | Routing/storage infrastructure from design-infrastructure |
| Pipeline data transformation (single-machine) | `data-engineering` | Polars — must-have; never Pandas in pipelines |
| Pipeline data transformation (distributed) | `data-engineering` | PySpark — optional; adopt when data exceeds single-machine capacity |
| EDA / notebook data processing | `data-science` | Pandas default; switch to Polars only when Pandas is a memory/speed bottleneck |
| Polars ↔ Pandas bridge | Boundary only | `df.to_pandas()` acceptable solely when a downstream library strictly requires `pd.DataFrame` |
| Storage backend selection | `data-engineering` | SQLite for local/prototype; DuckLake (PostgreSQL catalog + Parquet + DuckDB) for production scale |
| DuckLake query access from notebooks | `data-science` | Reading Gold via DuckDB in Marimo; setup and config live in data-engineering |
| OpenLineage event emission | `data-engineering` | Emit per Medallion tier; instrumentation pattern defined in observability |
| OpenLineage instrumentation pattern | `observability` | How to emit events; emission logic in data-engineering; Marquez deployment in design-infrastructure |
| Pipeline orchestration (mature, SDA) | `data-engineering` | Dagster — optional; for multi-pipeline production with built-in lineage and scheduling |
| Pipeline orchestration (multi-system) | `data-engineering` + `design-infrastructure` | Airflow — optional; DAG logic in data-engineering, server deployment in design-infrastructure |
| IAM backend — internal employees | `application-development` | Keycloak — LDAP/AD, corporate network, legacy protocol support |
| IAM backend — B2B SaaS tenants | `application-development` | Zitadel — cloud-native, multi-tenant organisations, event-sourced audit trail |
| IAM server deployment | `design-infrastructure` | Keycloak and Zitadel server setup follows design-infrastructure container/IaC patterns |
| GraphQL vs REST selection | `application-development` | GraphQL for query-heavy clients; REST for transactional APIs and prediction endpoints |
| Foundational architectural patterns | `design-system` | Pipes & Filters (batch), Layers (service), Hub-and-Spoke (federated systems) |
