---
name: data-science
description: Use when performing exploratory data analysis, designing features, prototyping models, evaluating model quality, conducting statistical analysis, or refactoring notebooks into production modules
---

# Data Science

## Overview

Covers the exploratory and experimental work that produces model prototypes, feature specifications, and analytical insights. Input is Gold tables (SQLite or DuckLake/Parquet) from data-engineering. Output is a validated model artifact handed to mlops, and feature specifications raised as GitHub Issues for data-engineering to implement at scale.

## Scope

**Owns:** EDA, feature selection and design (deciding what to compute — not how to compute it at scale), model prototyping and evaluation, statistical analysis, Marimo notebook conventions, notebook-to-module graduation, Pandas for EDA and prototyping on a single machine, experiment tracking usage (running experiments, logging metrics, comparing runs — not infrastructure).

**Does not own:** Feature pipeline implementation at scale (→ `data-engineering`), Polars for production pipeline transformations (→ `data-engineering`), DuckLake storage configuration (→ `data-engineering`), production model deployment or serving (→ `mlops`), experiment tracking infrastructure — MLflow server setup and model registry (→ `mlops`), data pipeline orchestration (→ `data-engineering`).

**Interfaces with:**
- `data-engineering` — feature specification raised as GitHub Issue; data-engineering implements the Gold pipeline
- `mlops` — validated model artifact and evaluation results handed off; mlops operationalises
- `code-quality` — notebook-to-module refactoring must comply with code-quality standards
- `git-workflow` — feature handoff Issues follow the TODO.md → GitHub Issue sync pattern

## When to Use

- **Trigger:** EDA on a new dataset or Gold table
- **Trigger:** Designing or selecting features for a model
- **Trigger:** Prototyping, training, or evaluating a model
- **Trigger:** Running and logging MLflow experiments
- **Trigger:** Graduating stable notebook code to `src/ml_engineering/`

**Do NOT use for:**
- Building the production feature pipeline (→ `data-engineering`)
- Deploying or serving a model (→ `mlops`)
- MLflow server or registry setup (→ `mlops`)

## Core Pattern

### Notebook-First, Migrate When Stable

All exploratory work starts in a Marimo notebook. Code migrates to `src/ml_engineering/` only when it meets the graduation threshold. Notebooks remain as readable documentation after migration — they are not deleted.

**Default notebook format: `.marimo` (Python-native)**
- Marimo notebooks are plain `.py` files — agent-readable, Git-diff friendly, importable
- Use `.ipynb` only when explicitly instructed (e.g., external stakeholder sharing)
- Naming convention: `nb_{purpose}.py` (e.g., `nb_sick_leave_eda.py`, `nb_feature_selection.py`)

**Notebook isolation rule:** Notebooks MUST import from the shared project config and utils — never redefine constants, paths, or utility functions inline.

```python
# ✅ Correct — shared config and utils
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from config import DATA_PATH, TARGET_COLUMN, FEATURES
from utils.db_handler import get_session

# ❌ Wrong — redefined inline
DATA_PATH = "data/3_Gold/gold.db"   # Drifts from config, breaks reproducibility
```

### Feature Design → Handoff

When EDA or prototyping reveals a feature that needs to be built into the Gold pipeline, the handoff to data-engineering is a GitHub Issue — not a verbal note or PR comment.

**Raise the Issue via TODO.md:**

```markdown
---
ISSUE: Add <feature_name> to Gold pipeline
**Goal**: <one sentence describing the feature and its ML purpose>
**Description**: <context from EDA — why this feature matters, what data source>
**Requirements**:
1. Compute <feature> from <source table> at Bronze/Silver layer
2. Expose in Gold as column `<column_name>` with type <type>
3. Ensure Zero-Null policy — interpolation rule: <specify>
**Acceptance Criteria**:
- [ ] Gold table contains `<column_name>` with no nulls
- [ ] Existing ML pipeline runs without schema errors
- [ ] Unit test covers the new column computation
END_ISSUE
---
```

Sync to GitHub: `task sync-todo` or `pwsh .github/scripts/sync-todo.ps1`

### Graduation Threshold

Notebook code graduates to `src/ml_engineering/` when ALL of these are true:
1. Runs end-to-end without manual intervention on a clean environment (`uv run`)
2. Validated on at least one dataset beyond the development set
3. Logic is reviewed against `code-quality` standards (type hints, guard clauses, 30-line limit)
4. MLflow experiment shows stable, reproducible results across runs

Do not migrate prematurely. A notebook that "mostly works" stays a notebook.

## Quick Reference

### Data Processing Library Selection

| Context | Library | Rationale |
|---|---|---|
| EDA, prototyping, single-machine exploration | **Pandas** | Familiar interactive API, integrates naturally with scikit-learn, sufficient for notebook scale |
| Large dataset in notebook exceeding Pandas memory/speed | **Polars** | Lazy evaluation, Arrow-native, multi-threaded — switch when Pandas becomes the bottleneck |
| Production pipeline transformations | **Polars** (→ `data-engineering`) | Not owned here — raise a data-engineering Issue |

### ML Framework Selection

| Task | Primary | Secondary | Avoid |
|---|---|---|---|
| Tabular ML | scikit-learn | XGBoost, LightGBM | Heavy frameworks for simple tasks |
| Deep learning | PyTorch | Keras / TensorFlow | — |
| Hyperparameter tuning | scikit-learn `GridSearchCV` / `RandomizedSearchCV` | — | Manual grid loops |
| Evaluation | scikit-learn metrics | `mlflow.log_metrics` | — |

### MLflow Experiment Logging (Current Standard)

> **Note:** Current setup logs to a local SQLite database (`data/4_eval/eval_data.db`). This is a prototyping-grade setup. Remote tracking server and structured artifact storage are a planned maturation — mark new work that assumes remote MLflow as a future dependency.

```python
import mlflow

mlflow.set_experiment("sick_leave_prediction")

with mlflow.start_run(run_name=f"{model_name}_{feature_set}"):
    mlflow.log_params({
        "model": model_name,
        "features": feature_set,
        "target": TARGET_COLUMN,
        "n_train": len(X_train),
    })
    model.fit(X_train, y_train)
    mlflow.log_metrics({"rmse": rmse, "mae": mae, "r2": r2})
    mlflow.log_artifact("model.pkl")
```

**Naming convention:** `run_name = f"{model_name}_{feature_set}"` — scannable without opening each run.

### Notebook Naming

| Purpose | Name |
|---|---|
| Exploratory data analysis | `nb_eda_{dataset}.py` |
| Feature selection / engineering | `nb_feature_{topic}.py` |
| Model prototyping | `nb_model_{algorithm}.py` |
| Evaluation / comparison | `nb_eval_{experiment}.py` |

## Implementation

### Project Structure

```
notebooks/
  data_exploration/         # EDA notebooks — nb_eda_*.py
  ml_experimentation/       # Model prototyping — nb_model_*.py, nb_eval_*.py
src/
  ml_engineering/           # Graduated production code
  utils/                    # Shared utilities — import here, never redefine
  config.py                 # Single source of truth for paths, targets, features
```

### Data Access Patterns

Access Gold data in notebooks using the appropriate backend. Pandas is the default for EDA; switch to Polars when the dataset size makes Pandas slow.

```python
import pandas as pd
import duckdb

# Option A: SQLite backend (local prototype) — Pandas default
from utils.db_handler import get_session
with get_session() as session:
    df = pd.read_sql("SELECT * FROM gold_sick_leave", session.bind)

# Option B: DuckLake backend (production data lake) — Pandas for EDA
conn = duckdb.connect()
conn.execute("LOAD ducklake;")
conn.execute("ATTACH 'ducklake:postgresql://...' AS lake (DATA_PATH 's3://...')")
df = conn.execute("SELECT * FROM lake.gold.sick_leave WHERE quarter = '2024Q1'").df()

# Option C: DuckLake — switch to Polars when Pandas is the bottleneck
import polars as pl
df = conn.execute("SELECT * FROM lake.gold.sick_leave").pl()
```

### Running Notebooks with uv

```bash
uv run marimo edit notebooks/ml_experimentation/nb_model_random_forest.py
uv run marimo run  notebooks/ml_experimentation/nb_model_random_forest.py  # headless
```

### Triggering the ML Lifecycle

```bash
uv run main.py               # Train → Evaluate → Register on existing Gold tables
uv run main.py --refresh-data  # Rebuild Gold first, then run ML lifecycle
```

### Reproducibility Checklist

Before logging an MLflow run as a valid experiment result:
- [ ] Random seeds set and logged as params
- [ ] Feature list logged as a param (not implied)
- [ ] Dataset version or record count logged
- [ ] Run reproduces within ±1% metric variance on re-execution

## Common Mistakes

**Notebook imports redefine `config.py` constants.**
Always import from `src/config.py`. Inline constants drift from production config and break reproducibility.

**Feature idea discussed in PR comments instead of raised as a GitHub Issue.**
Feature specifications must go through the TODO.md → Issue flow. A comment has no acceptance criteria and no audit trail.

**Using Polars by default in notebooks when Pandas suffices.**
Pandas is the default for EDA and prototyping — its interactive API is faster to work with at notebook scale. Switch to Polars only when Pandas becomes a memory or speed bottleneck.

**Graduating notebook code that hasn't been validated beyond the dev set.**
All four graduation criteria must be met. A notebook that "mostly works" stays a notebook.

**MLflow run names left as default (auto-generated UUIDs).**
Always set `run_name = f"{model_name}_{feature_set}"`. Unnamed runs are unscannable.

**Using `.ipynb` by default.**
Marimo is the default. `.ipynb` is explicitly opt-in. Marimo notebooks are Python files — they work with `uv run`, are readable by agents, and produce clean Git diffs.
