---
name: design-system
description: Use when designing a new feature, establishing domain models, defining bounded contexts, mapping data flows between services, or detecting architectural drift in existing code
---

# System Design

## Overview

Enforces Domain-Driven Design and Hexagonal Architecture to keep business logic isolated from infrastructure, frameworks, and vendor SDKs. The domain core must never import from external layers.

## Scope

**Owns:** Domain model design (entities, value objects, aggregates), bounded context definition and anti-corruption layers, dependency direction rules (hexagonal / clean architecture), port and adapter interface definitions, architectural drift detection.

**Does not own:** Container or cloud resource configuration (→ `design-infrastructure`), telemetry instrumentation (→ `observability`), code-level quality rules (→ `code-quality`), domain-specific implementation patterns (→ domain skills).

**Interfaces with:**
- `design-infrastructure` — system boundaries define what infrastructure must isolate
- `code-quality` — architectural constraints propagate down to code-level enforcement
- Domain skills — domain models defined here are implemented in domain skills

## When to Use

- **Trigger:** Planning a new sub-system, API endpoint, or feature set
- **Trigger:** Refactoring a codebase with no clear domain/infrastructure separation
- **Trigger:** Mapping data flows between services or bounded contexts
- **Trigger:** Detecting or preventing architectural drift (domain importing from infrastructure)

**Do NOT use for:**
- Container or cloud configuration (→ `design-infrastructure`)
- Code-level syntax or style rules (→ `code-quality`)
- Domain-specific implementation patterns (→ domain skills)

## Core Pattern

### Foundational Patterns for Data & AI Systems

Three structural patterns from Buschmann et al. (2013) underpin the architecture of data and AI systems. Select the pattern that matches the topology of the system being designed.

| Pattern | Use when | Implementation |
|---|---|---|
| **Pipes and Filters** | Batch data processing — data flows sequentially through independent transformation stages | Medallion architecture (Raw → Bronze → Silver → Gold); each tier is a filter, the pipeline is the pipe |
| **Layers** | Achieving interoperability across tiers with different trust levels and transformation concerns | Domain trust tiering (Raw = untrusted, Gold = invariant-enforced); Hexagonal Architecture (Domain / Application / Infrastructure) |
| **Hub-and-Spoke (Event Broker)** | Federated data systems — multiple producers and consumers decoupled via a central event broker | Azure Service Bus / GCP Pub/Sub as the hub; microservices, pipelines, and ML systems as spokes |

**Pipes and Filters** is the primary pattern for all batch data pipelines. Each Medallion tier is a filter (validates and transforms its input, produces clean output); the tier boundary is the pipe (contracts enforce what passes through).

**Layers** is the primary pattern for the application architecture within a service. Domain core, application layer, and infrastructure layer are strict layers — dependencies flow inward only.

**Hub-and-Spoke** applies when the system grows beyond a single pipeline into a federated architecture — multiple data sources, consumers, and ML systems communicating asynchronously. The event broker (Service Bus, Pub/Sub, Kafka) is the hub; each pipeline or service is a spoke.

### Maker/Checker Loop

Execute before finalising any structural proposal:

1. **Maker:** Draft the object layout and boundary map
2. **Checker:** Critique specifically for security vulnerabilities and operational cost
3. **TDD Edge:** Define testable domain boundaries before writing logic — what fails when the payload is malformed?

The Checker step is not optional. A design proposal without a security and cost critique is incomplete.

### Hard Constraints

**1. Dependency Direction**
- Dependencies point strictly inward toward the Domain Core
- Domain CANNOT import from databases, frameworks, or cloud SDKs
- Expose external requirements via `abc.ABC` or `typing.Protocol` (Ports); inject concrete implementations outward (Adapters)

**2. DDD Types**
- **Entities:** Business logic with identity — `pydantic` models or `dataclasses` with explicit ID fields
- **Value Objects:** Immutable attributes — `frozen=True` dataclasses
- **Application Layer:** Zero business logic — strictly orchestrates retrieval and execution

**3. Zero-Artifact Policy**
- No temporary CSVs, JSONs, or intermediate files written to disk
- Volatile state → memory; persistent state → centralized SQL or secure blob storage

**4. Data Trust Tiering**
- Isolate Raw IO from structurally validated domains (Bronze / Silver / Gold)
- System invariants act as hard gates before advancing tiers

**5. Vendor Neutrality**
- `SQLAlchemy` over raw vendor drivers
- `OpenTelemetry` over proprietary cloud logging (→ `observability`)
- Single unified telemetry facade — no fragmented `print` or `logging.basicConfig()`

## Quick Reference

| Constraint | Rule |
|---|---|
| Dependency direction | Inward only — domain never imports from infrastructure |
| External requirements | `abc.ABC` or `typing.Protocol` Ports |
| Entities | `pydantic` or `dataclasses` with explicit ID fields |
| Value Objects | `frozen=True` dataclasses |
| Application layer | Zero business logic — orchestration only |
| Intermediate artifacts | Banned — memory or centralized storage only |
| ORM | `SQLAlchemy` over raw vendor drivers |
| Telemetry | OpenTelemetry SDK, single facade (→ `observability`) |

### Multi-Cloud Persistence Mapping

| Requirement | Pattern | Azure | GCP |
|---|---|---|---|
| Persistence | Repository (DDD) | Azure SQL / Cosmos | Cloud SQL / BigQuery |
| Async Tasks | Domain Events | Service Bus | Pub/Sub |
| Observability | OpenTelemetry SDK | Azure Monitor | Cloud Monitoring |

## Implementation

### Output Format

Always produce a diagram before proposing changes:

1. **Diagram** — D2 graph (`d2` code block, `theme: sketch`) or Mermaid fallback
2. **Maker Proposal** — Entities, bounded contexts, and their interactions
3. **Checker Critique** — Security vulnerabilities and cost assessment
4. **Testable Invariants** — How the domain fails gracefully (error states, malformed inputs)

## Common Mistakes

**Domain imports from infrastructure.**
Extract the dependency into a Port and inject the Adapter. Immediate architectural drift if left uncorrected.

**Application layer contains business logic.**
Move it to the Domain. The application layer orchestrates; the domain decides.

**Bounded context models leaking across contexts.**
Define Anti-Corruption Layers at context boundaries. Never share internal domain models directly.

**Skipping the Checker step.**
A design proposal without a security and cost critique is not complete.
