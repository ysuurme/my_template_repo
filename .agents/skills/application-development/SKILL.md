---
name: application-development
description: Use when designing or building APIs, implementing REST endpoints, defining request/response contracts, setting up authentication, handling background tasks, or structuring service-to-service communication
---

# Application Development

## Overview

Covers the design and implementation of production APIs and services. Enforces clean request/response contracts, consistent auth patterns, and service boundaries that respect the domain model defined in `design-system`. **FastAPI** is the standard framework for all new Python API development — it is Pydantic-native (the same Pydantic used across data-engineering and mlops), generates OpenAPI documentation automatically, and is the current industry standard for Python services.

## Scope

**Owns:** API design patterns (REST, request/response contracts, versioning), input validation and serialisation (Pydantic), authentication and authorisation patterns, background task patterns, service-to-service communication, API documentation standards, contract testing for REST APIs.

**Does not own:** Domain modelling (→ `design-system`), infrastructure and deployment (→ `design-infrastructure`), agent-specific API patterns (→ `agentic-development`), model serving infrastructure (→ `mlops`).

**Interfaces with:**
- `design-system` — application layer implements ports defined in design-system; no business logic in routers
- `design-infrastructure` — APIs deploy as Docker containers; container standards and Kubernetes/cloud deployment live there
- `agentic-development` — agents may call application APIs; agent-specific patterns live in agentic-development
- `mlops` — model serving endpoints (MLflow-deployed prediction services) follow mlops patterns; custom prediction APIs built on top follow application-development patterns

## When to Use

- **Trigger:** Designing or implementing a REST API endpoint
- **Trigger:** Defining request/response models and validation
- **Trigger:** Setting up authentication or authorisation
- **Trigger:** Implementing background tasks or async processing
- **Trigger:** Structuring communication between services
- **Trigger:** Building a prediction API wrapper around a deployed ML model

**Do NOT use for:**
- Domain modelling or bounded context design (→ `design-system`)
- Infrastructure or deployment configuration (→ `design-infrastructure`)
- Agent-specific API patterns (→ `agentic-development`)
- MLflow model registry or training pipeline (→ `mlops`)

## Core Pattern

### FastAPI — Pydantic-Native, OpenAPI by Default

FastAPI is chosen because it uses the same Pydantic models already in use across the stack (data-engineering, mlops). No additional validation library, no separate schema definition step. Request and response models are the same Pydantic `BaseModel` classes used everywhere else.

```python
from fastapi import FastAPI, Depends
from pydantic import BaseModel

app = FastAPI(title="Absenteeism Prediction API", version="1.0.0")

class PredictionRequest(BaseModel):
    quarter: str                        # e.g. "2024Q1"
    branch_id: int
    features: dict[str, float]

class PredictionResponse(BaseModel):
    prediction: float
    model_version: str
    confidence: float | None = None

@app.post("/v1/predict", response_model=PredictionResponse)
async def predict(
    request: PredictionRequest,
    service: PredictionService = Depends(get_prediction_service),
) -> PredictionResponse:
    return await service.predict(request)
```

OpenAPI docs are generated automatically at `/docs` (Swagger UI) and `/redoc`. No manual documentation updates required.

### Router → Service → Port (Hexagonal)

Business logic never lives in the router. Routers are thin — they validate input, call a service, and return a response.

```
routers/        # FastAPI routes — input validation + response shaping only
services/       # Business logic — calls ports, orchestrates domain logic
ports/          # Abstract interfaces (abc.ABC or typing.Protocol)
adapters/       # Concrete implementations injected via Depends()
```

```python
# ✅ Thin router
@router.post("/predict", response_model=PredictionResponse)
async def predict(request: PredictionRequest, service: PredictionService = Depends(get_service)):
    return await service.predict(request)

# ❌ Business logic in router
@router.post("/predict")
async def predict(request: PredictionRequest):
    model = load_model("model.pkl")           # Domain logic in controller
    features = engineer_features(request)     # Transformation in controller
    return model.predict(features)
```

## Quick Reference

### API Style Selection

| Style | When | Framework |
|---|---|---|
| **REST** | Transactional operations (CRUD, prediction endpoints, webhooks) | FastAPI |
| **GraphQL** | Query-heavy clients (dashboards, analytics frontends, multiple clients with different data needs) | Strawberry + FastAPI |

**GraphQL is the preferred Query API** when clients need flexible access to nested or related data and different clients query different subsets of the same data. REST is preferred for simple, well-defined request/response contracts such as prediction endpoints.

### GraphQL with Strawberry

Strawberry is the preferred Python GraphQL library — it is type-annotated, Pydantic-compatible, and integrates directly with FastAPI. Schema is generated from Python types, not from a separate SDL file.

```python
import strawberry
from strawberry.fastapi import GraphQLRouter

@strawberry.type
class Prediction:
    quarter: str
    branch_id: int
    predicted_sick_days: float
    model_version: str

@strawberry.type
class Query:
    @strawberry.field
    def prediction(self, quarter: str, branch_id: int) -> Prediction:
        return service.get_prediction(quarter, branch_id)

schema = strawberry.Schema(query=Query)
graphql_router = GraphQLRouter(schema)
app.include_router(graphql_router, prefix="/graphql")
```

GraphQL Playground (interactive query UI) is available at `/graphql` — equivalent to Swagger for REST.

### Framework Decisions

| Concern | Choice | Reason |
|---|---|---|
| REST framework | FastAPI | Pydantic-native, auto OpenAPI, async-first, industry standard |
| GraphQL framework | Strawberry + FastAPI | Type-annotated, Pydantic-compatible, single app for both REST and GraphQL |
| Validation | Pydantic `BaseModel` | Same library as data-engineering and mlops — no new dependency |
| REST docs | Auto-generated `/docs` | OpenAPI Swagger from Pydantic models — no manual updates |
| GraphQL docs | Auto-generated `/graphql` | GraphQL Playground from Strawberry schema |
| Auth | OAuth2 + JWT or API key | Choose based on client type (user vs service) |
| Testing | Contract tests (consumer-driven) | Primary test type for both REST and GraphQL — see `code-quality` for taxonomy |
| Deployment | Docker container | Follows `design-infrastructure` standards |

### API Versioning

Always version the API from day one. Prefix all routes with `/v1/`.

```python
from fastapi import APIRouter
router = APIRouter(prefix="/v1", tags=["prediction"])
```

### Auth Patterns

| Use case | Pattern |
|---|---|
| User-facing API | OAuth2 with JWT (`fastapi.security.OAuth2PasswordBearer`) |
| Service-to-service | API key header (`X-API-Key`) validated via dependency |
| Internal only | Managed Identity (Azure) / Service Account (GCP) — no key in code |

**Self-hosted IAM — Keycloak vs Zitadel (Optional):** When a managed SaaS provider (Azure AD, Auth0) is ruled out by data residency, cost, or open-source requirements, choose between these two based on deployment context:

| Criterion | Keycloak | Zitadel |
|---|---|---|
| **Default for** | Enterprise / on-premise / LDAP + AD integration | Cloud-native / B2B SaaS / multi-tenant organisations |
| **Runtime** | Java — higher memory footprint, slower start | Go — low memory, instant startup, Kubernetes-friendly |
| **Multi-tenancy** | Realms — management overhead at scale | Native organisations — designed for thousands of tenants |
| **Protocol support** | OAuth2, OIDC, SAML, LDAP, Kerberos, legacy AD | OAuth2, OIDC, SAML |
| **Customisation** | Java SPIs — powerful, complex | JavaScript Actions + API-first — faster to iterate |
| **Audit / compliance** | Standard logs | Event sourcing — immutable history of every change |
| **Community** | 10+ years, vast ecosystem, most problems solved | Smaller but growing fast |
| **Database** | PostgreSQL / MySQL | PostgreSQL (optimal); CockroachDB for global scale |

**Choose Keycloak when:** managing internal employees — it is the gold standard for corporate identity, sitting in the middle of a private network with deep LDAP/Active Directory integration, employee SSO, and support for legacy enterprise protocols. This is the safe bet for internal IT.

**Choose Zitadel when:** managing external customers or B2B tenant organisations — cloud-native, lightweight, and built specifically for the multi-tenant SaaS problem where each customer needs their own SSO, branding, and user management.

Both integrate identically with FastAPI:

```python
from fastapi.security import OAuth2AuthorizationCodeBearer

oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl="https://<iam-host>/oauth/v2/authorize",
    tokenUrl="https://<iam-host>/oauth/v2/token",
)

@app.get("/protected")
async def protected_route(token: str = Depends(oauth2_scheme)) -> dict:
    user = await verify_token(token)
    return {"user": user}
```

IAM server deployment follows `design-infrastructure` patterns.

Never put secrets in code or environment variables — fetch from Key Vault via Managed Identity (→ `design-infrastructure`).

### Background Tasks

Use FastAPI `BackgroundTasks` for fire-and-forget operations (e.g., logging, notifications). For heavy processing that must complete before responding, use async service calls.

```python
from fastapi import BackgroundTasks

@app.post("/predict")
async def predict(request: PredictionRequest, background_tasks: BackgroundTasks):
    result = await service.predict(request)
    background_tasks.add_task(log_prediction, result)
    return result
```

## Implementation

### Project Structure

```
src/
  api/
    routers/          # Route handlers — thin, no business logic
    services/         # Business logic layer
    ports/            # Abstract interfaces
    adapters/         # Concrete implementations
    models/           # Pydantic request/response models
  main.py             # FastAPI app initialisation
```

### Dependency Injection

Services and adapters are injected via FastAPI's `Depends()`. This aligns with the Ports and Adapters pattern from `design-system` and keeps routers testable.

```python
from functools import lru_cache
from fastapi import Depends

@lru_cache
def get_prediction_service() -> PredictionService:
    return PredictionService(model_adapter=MlflowModelAdapter())

@router.post("/predict")
async def predict(
    request: PredictionRequest,
    service: PredictionService = Depends(get_prediction_service),
) -> PredictionResponse:
    return await service.predict(request)
```

### Contract Testing

For REST APIs, contract tests are the primary test type. They verify that the API honours the contract expected by its consumers — not that the internal implementation is correct.

```python
# Consumer-side contract: assert the response shape matches what the consumer expects
def test_predict_response_contract(client: TestClient) -> None:
    response = client.post("/v1/predict", json={
        "quarter": "2024Q1",
        "branch_id": 1,
        "features": {"avg_sick_days": 3.5},
    })
    assert response.status_code == 200
    body = response.json()
    assert "prediction" in body
    assert "model_version" in body
    assert isinstance(body["prediction"], float)
```

Consumer-driven contract tests define what the consumer expects. Producer contract tests verify the API still satisfies all registered consumers after a change.

### Running with uv

```bash
uv run uvicorn src.main:app --reload   # Dev server
uv run pytest tests/                   # Run contract and integration tests
```

## Common Mistakes

**Business logic in the router.**
Routers validate input and return responses. Domain logic belongs in services. A router with more than ~10 lines of non-routing code is a code smell.

**No versioning from day one.**
Always prefix with `/v1/`. Retrofitting versioning onto an unversioned API breaks existing clients.

**Using `dict` instead of Pydantic models.**
Untyped `dict` responses lose validation, auto-documentation, and type safety. Every request and response must be a typed Pydantic model.

**Secrets in environment variables.**
Environment variables are visible in process lists and container inspection. Fetch secrets from Key Vault at runtime via Managed Identity (→ `design-infrastructure`).

**Missing contract tests for service-to-service APIs.**
Internal APIs break silently without contract tests. A producer change that violates the consumer contract won't be caught by unit tests.

**No response model on endpoints.**
Always set `response_model=` on every endpoint. Without it, FastAPI cannot generate correct OpenAPI docs and will serialise everything, including internal fields that should be hidden.
