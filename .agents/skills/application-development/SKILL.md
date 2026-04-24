---
name: application-development
description: Use when designing or building APIs, implementing REST endpoints, defining request/response contracts, setting up authentication, handling background tasks, or structuring service-to-service communication
---

# Application Development

## Overview

Covers the design and implementation of production APIs and services. Enforces clean request/response contracts, consistent auth patterns, and service boundaries that respect the domain model defined in design-system.

## Scope

**Owns:** API design patterns (REST, request/response contracts, versioning), input validation and serialisation, authentication and authorisation patterns, background task patterns, service-to-service communication, API documentation standards.

**Does not own:** Domain modelling (→ `design-system`), infrastructure and deployment (→ `design-infrastructure`), agent-specific API patterns (→ `agentic-development`).

**Interfaces with:**
- `design-system` — application layer implements ports defined in design-system
- `design-infrastructure` — application deployment environment is owned by design-infrastructure
- `agentic-development` — agents may call application APIs; agent-specific patterns live in agentic-development

## When to Use

- **Trigger:** Designing or implementing an API endpoint
- **Trigger:** Defining request/response models and validation
- **Trigger:** Setting up authentication or authorisation
- **Trigger:** Implementing background tasks or async processing
- **Trigger:** Structuring communication between services

**Do NOT use for:**
- Domain modelling or bounded context design (→ `design-system`)
- Infrastructure or deployment configuration (→ `design-infrastructure`)
- Agent-specific API patterns (→ `agentic-development`)

## Core Pattern

[TODO: Add REST API design pattern, request/response contract standard, validation approach using Pydantic]

## Quick Reference

[TODO: Add endpoint structure table, auth pattern options, background task patterns, versioning conventions, uv tooling for FastAPI projects]

## Implementation

[TODO: Add stack-specific patterns: FastAPI conventions, Pydantic validation, auth implementation, async task setup, dependency injection aligned with design-system ports/adapters]

## Common Mistakes

[TODO: Document common API mistakes — missing input validation, business logic in controllers, no versioning strategy, secrets in code]
