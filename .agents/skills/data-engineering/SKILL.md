---
name: data-engineering
description: Use when designing or implementing data pipelines, structuring Medallion architecture tiers, defining data quality gates, schema validation with Pydantic, writing SQLAlchemy Core or ORM transformations, or building feature pipelines for ML consumption
---

# Data Engineering

## Overview

ELT pipelines following a Mini-Medallion architecture (Raw → Bronze → Silver → Gold) using SQLite + SQLAlchemy + Pydantic. Data is loaded first, transformed in-place within the database, and validated at the boundary before it ever touches a session. The primary output is Gold tables that are ML-ready, null-free, and correctly shaped for downstream consumption.

## Scope

**Owns:** ELT pipeline design and implementation, Medallion tier definitions and boundaries, SQLAlchemy Core (Bronze bulk inserts) and ORM (Silver/Gold transformations), Pydantic boundary validation (the Sandwich), upsert logic, data quality gates, schema contracts, feature pipeline implementation (computing features at scale — not designing them).

**Does not own:** Feature design — which features to compute and why (→ `data-science`), feature serving at inference time (→ `mlops`), model training pipelines (→ `mlops`), statistical analysis or EDA (→ `data-science`), pipeline execution infrastructure (→ `design-infrastructure`).

**Interfaces with:**
- `data-science` — data-science specifies feature requirements; data-engineering implements the Gold pipeline
- `mlops` — Gold tables and feature tables are the contract; mlops triggers on them
- `design-system` — Medallion tiers map to domain trust tiers (Raw=untrusted, Gold=invariant-enforced)
- `design-infrastructure` — pipeline execution environments, scheduling, and container patterns

## When to Use

- **Trigger:** Designing or building any layer of the Medallion pipeline
- **Trigger:** Writing SQLAlchemy models, Core inserts, or ORM transformations
- **Trigger:** Adding or modifying data quality gates or schema validation
- **Trigger:** Implementing a feature pipeline (from a specification provided by data-science)
- **Trigger:** Deciding which SQLAlchemy API to use (Core vs ORM)

**Do NOT use for:**
- Deciding which features to engineer (→ `data-science`)
- Model training pipelines (→ `mlops`)
- EDA or statistical analysis (→ `data-science`)

## Core Pattern

### Medallion Architecture (ELT)

Load first, transform in-place. Never write intermediate files to disk — all state lives in the database.

**Raw** — Source Zone
- Local files (`.json`, `.csv`) exactly as received — source of truth for reprocessing
- Excluded from version control (`.gitignore`)
- No transformation — read-only input layer

**Bronze** — Landing Zone
- Technology: **SQLAlchemy Core** (bulk inserts, speed-optimised, minimal ORM overhead)
- Structure: Star Schema — Fact tables (main numerical data) + Dimension tables (lookup data)
- Upsert logic: process only new files in Raw; never reprocess the entire dataset
- No transformation — structural representation of raw data only

**Silver** — Clean Zone
- Technology: **SQLAlchemy ORM** (complex logic, joins, readability)
- Flatten nested structures, cast types (`DATETIME`, `NUMERIC`), standardise strings
- JOIN Fact + Dimension tables to replace codes with human-readable values
- Output: one meaningful flat table per domain

**Gold** — ML Zone
- Technology: **SQLAlchemy ORM**
- **Target datasets (Fact):** preserve composite key (e.g., `Quarter + Branch`) — **NEVER pivot**. The model iterates over discrete `(Quarter, Branch)` row objects; pivoting creates Cartesian explosions.
- **Feature datasets (Dimension):** pivot/flatten to exactly 1 row per `Quarter` for clean `LEFT JOIN` onto the target table
- Zero-Null policy: enforce via interpolation before the ML handoff gate
- Gold tables must pass all quality gates before `mlops` can trigger

### The Pydantic Sandwich

Validate at the boundary — before data touches a SQLAlchemy session. Do not use SQLAlchemy `@validates` or `TypeDecorator` for business validation; those fire on flush, not on input.

```python
# ❌ SQLAlchemy-only validation — fires too late, clunky for regex/business rules
class BronzeRecord(Base):
    @validates('period')
    def validate_period(self, key, value):
        ...  # Runs at session flush, not at data entry

# ✅ Pydantic Sandwich — fail fast at the boundary
from pydantic import BaseModel, Field

class RawRecord(BaseModel):                          # Boundary validator
    period: str = Field(pattern=r'^\d{4}Q[1-4]$')
    value: float

class BronzeRecord(Base):                            # Storage only — no validation logic
    __tablename__ = "bronze_records"
    period: Mapped[str]
    value: Mapped[float]

# Usage: validate → store
record = RawRecord(**raw_data)                       # Raises ValidationError immediately if invalid
session.add(BronzeRecord(**record.model_dump()))
```

**Why not SQLModel?** SQLModel unifies Pydantic and SQLAlchemy into one class — elegant for simple schemas, but restrictive with complex Medallion transformations where Bronze storage models and Silver domain models must diverge. The Sandwich trades boilerplate for explicit control.

## Quick Reference

### Tooling Standards

| Task | Tool | Never use |
|---|---|---|
| Dependency management | `uv` | `pip`, `poetry`, `conda` |
| Run scripts | `uv run` | `python` directly |
| Sync environment | `uv sync` | `pip install -r` |
| Install editable | `uv pip install -e .` | `pip install -e .` |

### SQLAlchemy API Selection

| Tier | API | Reason |
|---|---|---|
| Bronze | Core | Bulk inserts, speed-critical, no ORM overhead needed |
| Silver | ORM | Complex joins and transformations benefit from ORM clarity |
| Gold | ORM | Feature engineering logic is complex; ORM readability wins |

### Medallion Tier Responsibilities

| Tier | Transformation | Quality Gate |
|---|---|---|
| Raw | None | None — source of truth |
| Bronze | None — load only (Star Schema) | Upsert deduplication |
| Silver | Flatten, cast types, JOIN, standardise | Type contract compliance |
| Gold | Feature engineering, pivot rules, interpolation | Zero-Null policy, ML shape contract |

### Pipeline Entrypoint Pattern

```bash
uv run main.py                 # ML pipeline only — runs on existing Gold tables
uv run main.py --refresh-data  # Full pipeline — Raw → Gold → ML
```

The `--refresh-data` flag is the clean separation between data engineering and ML engineering at the orchestration level. Never couple them implicitly.

## Implementation

### Project Structure

```
src/
  data_engineering/     # Medallion pipeline (Raw, Bronze, Silver, Gold)
  utils/                # Shared SQLAlchemy session handlers, DB utilities
  config.py             # Pipeline configuration (metrics enabled, paths)
data/
  0_Raw/                # Source files — excluded from Git
  *.db                  # SQLite databases per tier — excluded from Git
notebooks/
  data_exploration/     # Non-production EDA only — never import from src/
```

### Upsert Pattern (Bronze)

Never reprocess the entire Raw directory. Check whether the source file has already been loaded.

```python
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

stmt = sqlite_insert(BronzeTable).values(records)
stmt = stmt.on_conflict_do_nothing(index_elements=["source_file", "record_id"])
session.execute(stmt)
session.commit()
```

### Gold Layer Shape Rules

1. **Target tables:** rows indexed on composite key `(Quarter, Branch)` — one row per prediction unit
2. **Feature tables:** rows indexed on `(Quarter,)` only — exactly one row per time period
3. **Structural join:** `LEFT JOIN feature ON target.quarter = feature.quarter`
4. **Zero-Null gate:** run interpolation before exposing Gold to `mlops` — no nulls may pass

## Common Mistakes

**Using SQLAlchemy ORM at Bronze for bulk inserts.**
ORM overhead is unnecessary at the loading stage. Use SQLAlchemy Core for Bronze; reserve ORM for Silver and Gold transformations.

**Validating data inside SQLAlchemy models.**
`@validates` fires at flush time, not at input — garbage data reaches the session. Use the Pydantic Sandwich: validate at the boundary, store with SQLAlchemy.

**Pivoting target (Fact) tables in Gold.**
Target datasets must preserve the composite key as discrete row objects. Pivoting flattens the key and creates Cartesian explosions when joined with feature tables.

**Writing intermediate files to disk.**
The Zero-Artifact policy is absolute. All pipeline state lives in the SQLite database. No temporary CSVs, JSONs, or `.pkl` files between tiers.

**Running `python` directly instead of `uv run`.**
Always use `uv run` — it ensures the correct environment and interpreter. Running `python` directly risks environment mismatch.

**Reprocessing all Raw files on every pipeline run.**
Upsert logic exists to prevent this. Processing only new files is a core efficiency constraint, not a future optimisation.
