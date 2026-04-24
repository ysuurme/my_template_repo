---
name: data-engineering
description: Use when designing or implementing data pipelines, structuring Medallion architecture tiers, defining data quality gates, schema validation with Pydantic, writing SQLAlchemy or Polars transformations, configuring DuckLake storage, or building feature pipelines for ML consumption
---

# Data Engineering

## Overview

ELT pipelines following a Mini-Medallion architecture (Raw → Bronze → Silver → Gold). Two storage backends are supported: **SQLite + SQLAlchemy** for local, single-machine prototyping; **DuckLake (PostgreSQL catalog + Parquet files + DuckDB)** for production-scale data lakes. **Polars** is the default data processing library for all pipeline transformations. The primary output is Gold tables or Parquet datasets that are ML-ready, null-free, and correctly shaped for downstream consumption.

## Scope

**Owns:** ELT pipeline design and implementation, Medallion tier definitions and boundaries, SQLAlchemy Core (Bronze bulk inserts) and ORM (Silver/Gold transformations), Polars for pipeline data transformations, DuckLake storage backend configuration (PostgreSQL catalog, Parquet files, DuckDB query engine), storage backend selection (SQLite vs DuckLake), Pydantic boundary validation (the Sandwich), upsert logic, data quality gates, schema contracts, feature pipeline implementation (computing features at scale — not designing them).

**Does not own:** Feature design — which features to compute and why (→ `data-science`), feature serving at inference time (→ `mlops`), model training pipelines (→ `mlops`), statistical analysis or EDA (→ `data-science`), pipeline execution infrastructure (→ `design-infrastructure`), Pandas for EDA/prototyping (→ `data-science`).

**Interfaces with:**
- `data-science` — data-science specifies feature requirements; data-engineering implements the Gold pipeline
- `mlops` — Gold tables / Parquet datasets are the contract; mlops triggers on them
- `design-system` — Medallion tiers map to domain trust tiers (Raw=untrusted, Gold=invariant-enforced)
- `design-infrastructure` — pipeline execution environments, scheduling, and container patterns

## When to Use

- **Trigger:** Designing or building any layer of the Medallion pipeline
- **Trigger:** Writing SQLAlchemy models, Core inserts, or ORM transformations
- **Trigger:** Writing Polars transformation logic for pipeline stages
- **Trigger:** Configuring or querying a DuckLake storage backend
- **Trigger:** Deciding storage backend — SQLite (local prototype) vs DuckLake (production scale)
- **Trigger:** Adding or modifying data quality gates or schema validation
- **Trigger:** Implementing a feature pipeline from a data-science specification

**Do NOT use for:**
- Deciding which features to engineer (→ `data-science`)
- Model training pipelines (→ `mlops`)
- EDA or statistical analysis (→ `data-science`)

## Core Pattern

### Medallion Architecture (ELT)

Load first, transform in-place. Never write intermediate files to disk — all state lives in the database or object storage.

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
- Technology: **SQLAlchemy ORM** (complex logic, joins) or **Polars** (large-scale transformation)
- Flatten nested structures, cast types, standardise strings
- JOIN Fact + Dimension tables to replace codes with human-readable values
- Output: one meaningful flat table per domain

**Gold** — ML Zone
- Technology: **SQLAlchemy ORM** (SQLite backend) or **Polars → Parquet** (DuckLake backend)
- **Target datasets (Fact):** preserve composite key (e.g., `Quarter + Branch`) — **NEVER pivot**
- **Feature datasets (Dimension):** pivot/flatten to exactly 1 row per `Quarter` for clean `LEFT JOIN`
- Zero-Null policy: enforce via interpolation before the ML handoff gate
- Gold must pass all quality gates before `mlops` can trigger

### Polars as Default Processing Library

Polars is the default for all pipeline data transformations. It is lazy, multi-threaded, Arrow-native, and memory-efficient. Pandas is not used in pipelines — its eager, single-threaded execution is a bottleneck at pipeline scale.

```python
import polars as pl

# ✅ Polars pipeline transformation
df = pl.read_database("SELECT * FROM silver_sick_leave", connection)
df_gold = (
    df
    .filter(pl.col("value").is_not_null())
    .with_columns(pl.col("period").str.to_date())
    .group_by("quarter", "branch")
    .agg(pl.col("value").mean().alias("avg_value"))
)
df_gold.write_parquet("data/gold/sick_leave/2024Q1.parquet")

# ❌ Pandas in pipelines — single-threaded, eager, memory-heavy
import pandas as pd
df = pd.read_sql("SELECT * FROM silver_sick_leave", connection)
```

Exception: Pandas is acceptable as a bridge when a downstream library strictly requires a `pd.DataFrame` (e.g., a scikit-learn pipeline that hasn't been updated to accept Polars). Convert at the boundary: `df.to_pandas()`.

### The Pydantic Sandwich

Validate at the boundary — before data touches a SQLAlchemy session or Polars write. Do not use SQLAlchemy `@validates` for business validation; those fire on flush, not on input.

The preferred ORM stack is **SQLAlchemy + Pydantic + SQLModel**. SQLModel (from the creator of FastAPI) unifies SQLAlchemy and Pydantic into a single model definition, eliminating the boilerplate of maintaining two separate classes for the same data shape.

```python
from sqlmodel import SQLModel, Field, Session, create_engine
from pydantic import field_validator

class SickLeaveRecord(SQLModel, table=True):         # One class = Pydantic model + SQLAlchemy table
    id: int | None = Field(default=None, primary_key=True)
    period: str = Field(pattern=r'^\d{4}Q[1-4]$')
    value: float

# Boundary validation still happens before hitting the session
record = SickLeaveRecord.model_validate(raw_data)    # Raises ValidationError if invalid
with Session(engine) as session:
    session.add(record)
    session.commit()
```

**When to use SQLModel vs separate SQLAlchemy + Pydantic models:**

| Case | Approach |
|---|---|
| Models are identical between validation and storage | SQLModel — single class, no duplication |
| Bronze and Silver models must diverge significantly (different field sets, transformations) | Pydantic Sandwich — separate `RawRecord(BaseModel)` + `BronzeRecord(Base)` for explicit control |

For most Medallion tiers where the shape is stable, SQLModel eliminates boilerplate. Use the explicit Pydantic Sandwich only when the validation model and the storage model genuinely need to differ.

## Quick Reference

### Technology Tiers

Technologies are classified as **must-have** (required in every project) or **optional** (adopted when project maturity, scale, or team context justifies the added complexity).

#### Must-Have (Every Project)

| Task | Tool |
|---|---|
| Dependency management | `uv` |
| Single-machine pipeline transformation | `polars` |
| ORM / SQL abstraction | SQLAlchemy Core (Bronze) + ORM (Silver/Gold) |
| Boundary validation | Pydantic (Sandwich pattern) |
| Data lake query engine | `duckdb` |
| Storage backend | SQLite (local/prototype) |
| Architecture | Medallion (Raw → Bronze → Silver → Gold) |

#### Optional (Mature / Production Setup)

| Tool | Adopt when |
|---|---|
| **PySpark** | Data exceeds single-machine capacity; Databricks environment |
| **DuckLake** | Production data lake with multi-consumer access (PostgreSQL catalog + Parquet) |
| **PySpark** | Data exceeds single-machine capacity; Databricks environment |
| **DuckLake** | Production data lake with multi-consumer access (PostgreSQL catalog + Parquet) |
| **Dagster** | Mature orchestration with Software-Defined Assets, built-in lineage, and scheduling |
| **OpenLineage + Marquez** | Data lineage tracking at scale across pipeline stages |
| **dbt** | Team is strongly SQL-heavy and Python transformations are not preferred |
| **Airflow** | Complex multi-system orchestration where Spark DAGs are insufficient |

### Processing Framework Selection

| Scale | Framework | When |
|---|---|---|
| Single-machine (prototype, local dev) | **Polars** | Data fits in memory; default for Medallion pipeline development |
| Distributed (production, cluster) | **PySpark** | Data exceeds single-machine capacity; Databricks environment |
| Mature orchestration with SDA | **Dagster** | Declarative assets, built-in lineage, partitioning, backfills |
| SQL-centric team (good reason required) | dbt | Team strongly prefers SQL over Python; transformations are pure SQL; integrates with Dagster |
| Multi-system orchestration (good reason required) | Airflow | Orchestrating across heterogeneous systems where Spark/Dagster are insufficient |

**Default rule:** Polars for single-machine work, PySpark for distributed work. dbt and Airflow require an explicit reason — they are not the default.

**Why Spark over dbt:** PySpark is Python-native — the same language used across the entire stack. dbt is SQL-only, limiting expressiveness for complex transformations. Spark pipelines also run natively on Databricks.

**Why Spark over Airflow:** Spark handles pipeline execution via its own DAG model. Airflow adds orchestration infrastructure only justified when Spark alone cannot coordinate the full system.

### Dagster Software-Defined Assets (Optional — Mature Setup)

Dagster shifts orchestration from *task execution* (run this job) to *asset production* (produce this dataset). Each Medallion tier becomes a declared asset; Dagster handles execution, scheduling, and lineage automatically.

**When to adopt:** Multiple Medallion pipelines in production, need for built-in partitioning/backfills, or when observability into asset state (which assets are stale, which are fresh) becomes a primary concern.

```python
from dagster import asset, AssetIn

@asset                              # Bronze — loads from Raw
def bronze_sick_leave(context) -> pl.DataFrame:
    return load_raw_files(RAW_PATH)

@asset(ins={"bronze": AssetIn("bronze_sick_leave")})   # Silver
def silver_sick_leave(bronze: pl.DataFrame) -> pl.DataFrame:
    return transform_to_silver(bronze)

@asset(ins={"silver": AssetIn("silver_sick_leave")})   # Gold
def gold_sick_leave(silver: pl.DataFrame) -> pl.DataFrame:
    return build_gold(silver)
```

Key properties of Dagster SDAs relevant to this stack:
- **Environment agnosticism** — same asset definitions run in dev and production without code changes (mirrors experimental-operational symmetry in `mlops`)
- **Built-in data lineage** — asset dependency graph is the lineage graph; no separate OpenLineage emission needed when Dagster is the orchestrator
- **Partitioning and backfills** — time-partitioned assets (per Quarter) and historical backfills are first-class, not workarounds
- **dbt integration** — dbt models can be declared as Dagster assets, unifying SQL and Python transformations in one lineage graph

### Storage Backend Selection

| Backend | When to use | Catalog | Storage | Query |
|---|---|---|---|---|
| SQLite + SQLAlchemy | Local dev, single-machine prototype, portable | Embedded `.db` file | `.db` file | SQLAlchemy / DuckDB |
| DuckLake | Production scale, cloud, multi-consumer access | PostgreSQL | Parquet on object storage | DuckDB |

### SQLAlchemy API Selection

| Tier | API | Reason |
|---|---|---|
| Bronze | Core | Bulk inserts, speed-critical |
| Silver | ORM or Polars | ORM for joins; Polars for large-scale transformation |
| Gold | ORM or Polars → Parquet | ORM for SQLite backend; Polars for DuckLake backend |

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

## Implementation

### Project Structure

```
src/
  data_engineering/     # Medallion pipeline (Raw, Bronze, Silver, Gold)
  utils/                # Shared SQLAlchemy session handlers, DB utilities
  config.py             # Pipeline configuration (metrics enabled, paths, storage backend)
data/
  0_Raw/                # Source files — excluded from Git
  *.db                  # SQLite databases per tier — excluded from Git
  gold/                 # Parquet files (DuckLake backend) — excluded from Git
```

### DuckLake Setup and Usage

```python
import duckdb
import polars as pl

# Attach DuckLake (PostgreSQL catalog + Parquet on object storage)
conn = duckdb.connect()
conn.execute("INSTALL ducklake; LOAD ducklake;")
conn.execute("""
    ATTACH 'ducklake:postgresql://user:pass@host/catalog_db'
    AS lake (DATA_PATH 's3://bucket/data/')
""")

# Write Gold tier as Parquet (via Polars)
df_gold.write_parquet("s3://bucket/data/gold/sick_leave/2024Q1.parquet")

# Query via DuckDB — returns Polars DataFrame
result = conn.execute("SELECT * FROM lake.gold.sick_leave").pl()
```

### Upsert Pattern (Bronze / SQLite)

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

### Open Standards

| Standard | Role |
|---|---|
| OpenLineage | Data lineage metadata — records what data flows through which pipeline steps, with input/output dataset pointers |
| Pydantic | Boundary validation (Pydantic Sandwich) |
| SQLAlchemy | Storage abstraction — Core for Bronze, ORM for Silver/Gold |

**OpenLineage for data lineage:** Emit OpenLineage events from each Medallion tier so that pipeline lineage (what data came from where, which pipeline version produced it) is machine-readable. OpenLineage is the open standard — compatible with OpenMetadata, Apache Atlas, and Marquez.

```python
from openlineage.client import OpenLineageClient, RunEvent, RunState
from openlineage.client.facet import DataSourceDatasetFacet

client = OpenLineageClient.from_environment()
client.emit(RunEvent(
    eventType=RunState.COMPLETE,
    job=Job(namespace="sick_leave_pipeline", name="silver_transformation"),
    inputs=[Dataset(namespace="sqlite", name="bronze_sick_leave")],
    outputs=[Dataset(namespace="sqlite", name="silver_sick_leave")],
))
```

### Integration Testing for ETL Pipelines

Integration tests — not unit tests — are the primary test type for ETL pipelines. Test the output of each pipeline stage, not the transformation logic.

```python
def test_silver_row_count(session: Session) -> None:
    count = session.execute(select(func.count()).select_from(SilverSickLeave)).scalar()
    assert count > 0, "Silver table must not be empty after pipeline run"

def test_gold_no_nulls(session: Session) -> None:
    nulls = session.execute(
        select(func.count()).select_from(GoldSickLeave).where(GoldSickLeave.avg_value.is_(None))
    ).scalar()
    assert nulls == 0, "Gold Zero-Null policy violated"

def test_gold_date_range(session: Session) -> None:
    min_q, max_q = session.execute(
        select(func.min(GoldSickLeave.quarter), func.max(GoldSickLeave.quarter))
    ).one()
    assert min_q == "2020Q1"
    assert max_q >= "2024Q4"
```

Standard integration checks per pipeline stage:
- **Row count** — does the output have the expected number of rows?
- **Unique IDs** — are all expected branch IDs / entity keys present?
- **Date range** — does the time span cover the expected quarters/periods?
- **Zero-Null** — Gold tier: no nulls in any column (Zero-Null policy)

## Common Mistakes

**Using Pandas for pipeline transformations.**
Pandas is not used in data-engineering pipelines. Polars is the default — lazy, multi-threaded, Arrow-native. The only exception is a boundary conversion (`df.to_pandas()`) when a downstream library strictly requires it.

**Using SQLAlchemy ORM at Bronze for bulk inserts.**
ORM overhead is unnecessary at the loading stage. Use SQLAlchemy Core for Bronze.

**Validating data inside SQLAlchemy models.**
`@validates` fires at flush time. Use the Pydantic Sandwich: validate at the boundary, store with SQLAlchemy.

**Pivoting target (Fact) tables in Gold.**
Target datasets must preserve the composite key. Pivoting creates Cartesian explosions.

**Writing intermediate files to disk.**
Zero-Artifact policy is absolute. State lives in the database (SQLite) or registered Parquet files (DuckLake). No temporary CSVs or JSONs between tiers.

**Running `python` directly instead of `uv run`.**
Always use `uv run` — correct environment and interpreter are guaranteed.

**Reprocessing all Raw files on every pipeline run.**
Upsert logic exists to prevent this. Processing only new files is a core efficiency constraint.
