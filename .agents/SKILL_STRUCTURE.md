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

**Owns:**
- Python syntax standards (PEP-8, type hints, naming)
- Function and module structure (indentation limits, size limits, guard clauses)
- TDD enforcement (pytest, mocking, failing test first)
- Code review feedback format (Observation / Principle / Instruction / Reference)
- Standard library vs third-party dependency decisions

**Does not own:**
- System or domain model design (→ `design-system`)
- Domain-specific implementation patterns (→ domain skills)
- Git operations or PR creation (→ `git-workflow`)

**Interfaces with:**
- `design-system` — architectural constraints define what code-quality enforces at the micro level
- Domain skills — code-quality applies universally; domain skills define what is being built

---

### `git-workflow`
**Primary artifact:** Linked branch → commit → PR tied to a GitHub Issue

**Owns:**
- Branch naming convention (`feature/issue-N`)
- Commit message format (`feat(#N): Title`)
- PR creation with issue auto-close (`Closes #N`)
- Error handling for git/gh commands
- Agent-driven automation of the full branch → PR flow

**Does not own:**
- CI/CD pipeline configuration (→ `design-infrastructure`)
- Code review standards (→ `code-quality`)
- Repository or branching strategy design

**Interfaces with:**
- `design-infrastructure` — CI/CD runs on the branches and PRs this skill creates

---

## Layer 2 — Design

### `design-system`
**Primary artifact:** Domain model with defined boundaries and dependency rules

**Owns:**
- Domain model design (entities, value objects, aggregates)
- Bounded context definition and anti-corruption layers
- Dependency direction rules (hexagonal / clean architecture)
- Port and adapter interface definitions
- Architectural drift detection

**Does not own:**
- Container or cloud resource configuration (→ `design-infrastructure`)
- Telemetry instrumentation (→ `observability`)
- Code-level quality rules (→ `code-quality`)
- Domain-specific implementation patterns (→ domain skills)

**Interfaces with:**
- `design-infrastructure` — system boundaries define what infrastructure must isolate
- `code-quality` — architectural constraints propagate down to code-level enforcement
- Domain skills — domain models defined here are implemented in domain skills

---

### `design-infrastructure`
**Primary artifact:** Deployable, secure execution environment (containers, IaC, CI/CD)

**Owns:**
- Dockerfile construction and optimization (multi-stage, rootless, health checks)
- Terraform module structure and remote state management
- CI/CD pipeline configuration
- Azure and GCP identity, networking, and secrets management standards
- Multi-cloud placement decisions (Azure default, GCP for ML/BigQuery environments)

**Does not own:**
- Application domain modeling (→ `design-system`)
- Telemetry SDK instrumentation (→ `observability`)
- Domain-specific deployment patterns (→ domain skills where relevant)

**Interfaces with:**
- `design-system` — system boundary design informs network isolation and identity scope
- `observability` — infrastructure routes and stores telemetry; SDK instrumentation lives in observability
- `mlops` — model serving infrastructure is owned by mlops, general container patterns live here

---

### `observability`
**Primary artifact:** Instrumented system emitting correlated logs, traces, and metrics

**Owns:**
- OpenTelemetry SDK setup and configuration
- Structured logging standards and field conventions
- Trace and span instrumentation patterns
- Metrics collection and naming conventions
- Log-trace-metric correlation patterns

**Does not own:**
- Log storage, routing, or alerting infrastructure (→ `design-infrastructure`)
- Business metric definitions — these are defined in domain skills, instrumented here
- Model performance monitoring and drift metrics (→ `mlops`)

**Interfaces with:**
- `design-infrastructure` — observability defines what to emit; infrastructure defines where it goes
- `mlops` — model metrics and drift monitoring are owned by mlops; general trace instrumentation lives here

---

## Layer 3 — Domain Build

### `data-engineering`
**Primary artifact:** Validated, reliable datasets and feature tables

**Owns:**
- ETL/ELT pipeline design and implementation
- Orchestration tooling (scheduling, DAGs, dependencies, retries)
- Storage layer management (data warehouse, data lake, lakehouse)
- Data quality gates and schema validation
- Medallion architecture (Bronze / Silver / Gold)
- Feature pipeline *implementation* (computing features reliably at scale)

**Does not own:**
- Feature *design* — which features to compute (→ `data-science`)
- Feature *serving* at inference time (→ `mlops`)
- Model training pipelines (→ `mlops`)
- Statistical analysis or EDA (→ `data-science`)

**Interfaces with:**
- `data-science` — data-science designs features; data-engineering implements the pipeline
- `mlops` — data-engineering produces training datasets; mlops consumes them for training pipelines
- `design-system` — Medallion layers map to domain trust tiers defined in design-system
- `design-infrastructure` — pipeline execution environments are owned by design-infrastructure

---

### `data-science`
**Primary artifact:** Model prototypes, evaluation results, and analytical insights

**Owns:**
- Exploratory data analysis (EDA)
- Feature selection and design (deciding what to compute, not how to compute it at scale)
- Model prototyping and evaluation
- Statistical analysis and hypothesis testing
- Notebook-to-module refactoring patterns
- Experiment tracking *usage* — running experiments, logging metrics, comparing runs

**Does not own:**
- Feature pipeline *implementation* at scale (→ `data-engineering`)
- Production model deployment or serving (→ `mlops`)
- Experiment tracking *infrastructure* — registry setup, model promotion gates (→ `mlops`)
- Data pipeline orchestration (→ `data-engineering`)

**Interfaces with:**
- `data-engineering` — data-science defines features; data-engineering builds the production pipeline
- `mlops` — data-science produces model artifacts and evaluation results; mlops operationalizes them
- `code-quality` — notebook-to-module refactoring is enforced by code-quality standards

---

### `mlops`
**Primary artifact:** Production ML system (training pipeline, serving endpoint, monitoring)

**Owns:**
- Production training pipeline design and automation
- Model registry, versioning, and promotion gates (experiment → staging → production)
- Model serving and inference infrastructure
- Feature store serving (delivering features to models at inference time)
- Model monitoring, drift detection, and retraining triggers
- Experiment tracking *infrastructure* — MLflow setup, registry configuration

**Does not own:**
- Raw data pipeline management (→ `data-engineering`)
- Model prototyping or experimentation (→ `data-science`)
- General container and cloud infrastructure primitives (→ `design-infrastructure`)
- General telemetry instrumentation (→ `observability`)

**Interfaces with:**
- `data-engineering` — mlops consumes datasets and feature tables produced by data-engineering
- `data-science` — mlops operationalizes model artifacts and evaluation results from data-science
- `design-infrastructure` — serving infrastructure follows general container/cloud patterns from design-infrastructure
- `observability` — model metrics are defined here; trace instrumentation patterns come from observability

---

### `application-development`
**Primary artifact:** Production API or service

**Owns:**
- API design patterns (REST, request/response contracts, versioning)
- Input validation and serialization
- Authentication and authorization patterns
- Background task patterns
- Service-to-service communication
- API documentation standards

**Does not own:**
- Domain modeling (→ `design-system`)
- Infrastructure and deployment (→ `design-infrastructure`)
- Agent-specific API patterns (→ `agentic-development`)

**Interfaces with:**
- `design-system` — application layer implements ports defined in design-system
- `design-infrastructure` — application deployment environment is owned by design-infrastructure
- `agentic-development` — agents may call application APIs; agent-specific patterns live in agentic-development

---

### `agentic-development`
**Primary artifact:** Functioning agent (tool use, multi-agent coordination, structured outputs)

**Owns:**
- Claude API usage patterns (tool use, structured outputs, streaming)
- Agent loop design and state management
- Multi-agent coordination patterns
- Tool definition, validation, and error handling
- Context window and prompt management
- Agent testing patterns

**Does not own:**
- General API development patterns (→ `application-development`)
- Agent deployment infrastructure (→ `design-infrastructure`)
- Data pipeline patterns used by agents (→ `data-engineering`)
- Model serving infrastructure (→ `mlops`)

**Interfaces with:**
- `application-development` — agents often expose or consume APIs; general API patterns live there
- `design-infrastructure` — agent runtime deployment follows general container/cloud patterns
- `git-workflow` — agent-driven git automation uses the patterns defined in git-workflow

---

## Meta

### `write-skills`
**Primary artifact:** Valid, MECE-compliant SKILL.md

**Owns:**
- Skill creation standards and SKILL.md template
- Validation process (baseline → draft → verify)
- MECE enforcement and split detection
- Routing signal format
- ASO (Agent Search Optimization) rules

**Does not own:**
- Project-specific agent instructions (→ `CLAUDE.md` / `AGENT.md`)
- Individual skill content

**Interfaces with:** All other skills — defines the contract every skill must follow.

---

## Explicit Boundary Rules

These shared concerns appear in multiple domains. Ownership is fixed here.

| Concern | Owner | Notes |
|---|---|---|
| Feature design (what to compute) | `data-science` | |
| Feature pipeline (computing it at scale) | `data-engineering` | |
| Feature serving (at inference time) | `mlops` | |
| Experiment tracking usage (running experiments) | `data-science` | |
| Experiment tracking infrastructure (MLflow setup, registry) | `mlops` | |
| Model evaluation during prototyping | `data-science` | |
| Model promotion gates (staging → production) | `mlops` | |
| Training data pipeline | `data-engineering` | It's a pipeline; model training itself is mlops |
| Batch inference pipeline | `mlops` | It executes a model; data movement patterns from data-engineering apply |
| Container and cloud primitives | `design-infrastructure` | |
| Model serving infrastructure | `mlops` | Specialised enough to own it; general container patterns from design-infrastructure |
| Business metric definitions | Domain skill that owns the domain | Instrumentation pattern comes from observability |
| Telemetry SDK instrumentation | `observability` | Routing/storage infrastructure from design-infrastructure |
