---
name: design-infrastructure
description: Use when creating Dockerfiles, building Terraform modules, configuring CI/CD pipelines, defining cloud identity and networking standards, or making multi-cloud placement decisions
---

# Infrastructure Design

## Overview

Governs the execution environment, delivery mechanism, and cloud orchestration of systems. Prioritises least privilege, blast radius minimisation, and cloud fluidity across Azure and GCP.

## Scope

**Owns:** Dockerfile construction and optimisation (multi-stage, rootless, health checks), Terraform module structure and remote state management, CI/CD pipeline configuration, Azure and GCP identity and networking standards, secrets management, multi-cloud placement decisions.

**Does not own:** Application domain modelling (→ `design-system`), telemetry SDK instrumentation (→ `observability`), domain-specific deployment patterns (→ domain skills where relevant).

**Interfaces with:**
- `design-system` — system boundary design informs network isolation and identity scope
- `observability` — infrastructure routes and stores telemetry; SDK instrumentation lives in observability
- `mlops` — model serving infrastructure is owned by mlops; general container patterns live here

## When to Use

- **Trigger:** Constructing a Dockerfile for any workload
- **Trigger:** Setting up or modifying Terraform modules or state backends
- **Trigger:** Building or updating CI/CD pipelines
- **Trigger:** Deciding which cloud provider to use for a given workload
- **Trigger:** Defining identity, networking, or secrets management standards

**Do NOT use for:**
- Application domain modelling (→ `design-system`)
- Telemetry SDK setup and instrumentation (→ `observability`)

## Core Pattern

### Maker/Checker Loop

1. **Maker:** Draft the Terraform configuration, Dockerfile layers, or CI/CD pipeline
2. **Checker:** Critique specifically for least-privilege networking, container blast radius, and cost anomalies
3. **TDD Edge:** Define how infrastructure state will be validated before deployment (drift detection, image scanning)

### Hard Constraints

**1. Azure Identity & Networking**
- **Compute Identity:** System-Assigned Managed Identities for all app compute nodes — eliminates credential rotation. Service Principals only for external headless automation (CI/CD Terraform pipelines)
- **Secrets:** Never in `ENV` variables or Dockerfile — fetch dynamically from Azure Key Vault using Managed Identity
- **Network Isolation:** Compute inside VNet. No public IPs directly on VMs or App Services unless brokered via Front Door / App Gateway. Azure Private Link (Private Endpoints) for PaaS services

**2. Terraform Integrity**
- Modular, single-purpose DRY modules
- Local state is banned — state must be encrypted, remote, and locked via Azure Storage
- Mandate `terraform plan -detailed-exitcode` in pipelines — exit code 2 signals drift requiring immediate attention

**3. Docker Blast Radius Minimisation**
- Multi-stage builds — "Builder" installs compilers; final runtime layer must never contain `gcc`, `git`, or shells
- Rootless — dedicated non-root user via `USER` directive; executing as `root` is an immediate failure
- Base images: `python:3.12-slim` for standard workloads; Distroless Python for maximum security environments
- `HEALTHCHECK` required — ping `/health` using standard library only

## Quick Reference

### Multi-Cloud Placement

| Workload | Default | Rationale |
|---|---|---|
| State backend | Azure Blob Storage | Conditional lease locking, Enterprise Compliance |
| ML / BigQuery workloads | GCP | Data gravity, Vertex AI, native BigQuery integration |
| Hybrid / Enterprise compliance | Azure | Entra ID, Hybrid Benefit |

**Storage latency difference:** GCP Archive is instant (milliseconds). Azure Blob Archive requires async rehydration (hours) — Python host must handle the Request/Wait cycle.

### Infrastructure Mapping

| Requirement | Pattern | Azure | GCP |
|---|---|---|---|
| Auth & Identity | OIDC | Managed Identity | Workload Identity |
| Orchestration | K8s Deployment | AKS | GKE |
| IaC State | Remote Locked Backend | Blob Container | GCS Bucket |
| CI/CD Drift | Scheduled Plan Runs | Exit Code 2 → Alert | Exit Code 2 → Alert |
| Reverse Proxy (self-managed) | Traefik | AKS Ingress | GKE Ingress |
| Reverse Proxy (cloud-native) | Cloud Load Balancer | Azure Front Door / App Gateway | Cloud Load Balancing |

### Traefik — Cloud-Native Reverse Proxy (Optional)

Traefik is the preferred reverse proxy for self-managed container environments (Kubernetes, Docker Compose). It auto-discovers services via Docker/Kubernetes labels, eliminating manual routing configuration. Built-in Let's Encrypt integration handles TLS certificate lifecycle automatically.

Use Traefik when: running self-managed containers (AKS, GKE, Docker Compose) and service routing complexity justifies a dedicated proxy. Use cloud-native load balancers (Azure Front Door, GCP Cloud Load Balancing) when using managed PaaS services where cloud routing is provided.

```yaml
# docker-compose.yml — Traefik auto-discovery via labels
services:
  api:
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.api.rule=Host(`api.example.com`)"
      - "traefik.http.routers.api.tls.certresolver=letsencrypt"
```

### ML Pipeline CI/CD

ML training pipeline CI/CD is a first-class concern alongside application CI/CD. A pipeline CI stage must: (1) build and test each containerised pipeline component using the same multi-stage, rootless, `HEALTHCHECK` Docker standards as any other container; (2) run an end-to-end smoke test of the assembled pipeline on a small sample dataset; (3) deploy the validated pipeline definition to the target orchestrator (e.g. Vertex AI Pipelines on GCP). Model validation logic, promotion gates, and retraining triggers are owned by `mlops`; only the build, test, and deploy infrastructure lives here.

## Implementation

### Output Format

1. **Strategic Cloud Mapping** — justifying resource positioning and auth bounds
2. **Maker Proposal** — Terraform blocks, Dockerfile, or YAML pipeline
3. **Checker Critique** — least privilege and blast radius self-audit
4. **TDD Invariants** — Terraform drift exit-code bounds; Trivy scan gate applicability

### Trivy Scanning

Vulnerability scans prior to deployment are strongly recommended. Mandatory for production workloads; optional for short-lived non-sensitive pilots.

## Common Mistakes

**Secrets in environment variables or Dockerfile.**
Immediate failure. Fetch from Key Vault using Managed Identity at runtime.

**Local Terraform state.**
Banned. All state must be remote, encrypted, and locked.

**Compiler or shell in final Docker layer.**
Multi-stage build required. Final image must not inherit build tools.

**Running container as root.**
Add a dedicated user and switch via `USER` directive before the entrypoint.

**No HEALTHCHECK defined.**
Every image must define a `HEALTHCHECK` — use standard library, not a third-party dependency.
