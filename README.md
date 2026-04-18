# python-uv-template

Copier-based Python project scaffold for UV projects. Three variants: general-purpose, machine learning, and FastAPI application. Generates a production-ready structure with structured logging, typed config, AI-assisted commit messages, test coverage mirroring `src/`, and GitHub Actions CI — ready to `uv sync` and go.

---

## Table of Contents

- [Quickstart](#quickstart)
- [Variants](#variants)
- [Repository Structure](#repository-structure)
- [Conventions](#conventions)

---

## Quickstart

Get a new project running in under 2 minutes.

**1. Install copier** — once, globally:
```bash
uv tool install copier
```

**2. Generate a new project**
```bash
uvx copier copy gh:your-username/my_template_repo path/to/new-project
```

Copier will prompt for:
- `project_name` — hyphenated name (e.g. `my-new-project`)
- `description` — one-line project description
- `variant` — `base`, `ml`, or `application`

**3. Replace the logging stub**
```bash
# Drop your m_log.py into src/utils/ — interface: f_log(), setup_logging(), f_log_execution()
```

---

## Variants

### `base` — General-purpose Python project
The foundation. Use for scripts, automation, CLI tools, or anything that doesn't fit a specialised variant.

```
src/
└── utils/                        m_log.py, m_commit.py
```

### `ml` — Machine Learning project
Adds MLflow experiment tracking, data directory structure, and model artifact storage.

```
src/
├── data/                         Data loading and preprocessing
├── models/                       Model definitions and training
└── utils/                        m_log.py, m_commit.py
data/
├── raw/                          Immutable source data
├── processed/                    Cleaned and transformed
└── features/                     Feature-engineered datasets
notebooks/                        Exploratory analysis
models/                           Serialized model artifacts
```

Extra deps: `pandas`, `scikit-learn`, `matplotlib`, `mlflow`
Extra `.env` vars: `MLFLOW_TRACKING_URI`, `EXPERIMENT_NAME`

### `application` — FastAPI service
Adds API routing, Pydantic schema layer, and application config (host, port, debug).

```
src/
├── api/                          Route handlers and middleware
├── schemas/                      Pydantic request/response models
└── utils/                        m_log.py, m_commit.py
```

Extra deps: `fastapi`, `uvicorn[standard]`
Extra `.env` vars: `HOST`, `PORT`, `DEBUG`

---

## Repository Structure

```
my_template_repo/
├── copier.yml                    Variant selector + post-generation tasks
├── LICENSE
├── README.md                     This file
├── base/                         General-purpose variant
├── ml/                           Machine learning variant
└── application/                  FastAPI application variant
```

Each variant contains a complete, self-contained scaffold. Shared files (logging, commit helper, CI, gitignore) are duplicated by design — variants evolve independently.

---

## Conventions

- **Variant selection**: answered at generation time via `copier.yml` prompt
- **Utility modules**: `m_*.py` naming in `src/utils/` — generic, no project-specific logic
- **Domain folders**: add `src/<domain>/` as the project grows — never pollute `src/utils/`
- **Test parity**: every `src/**/*.py` gets a matching `tests/**/test_*.py`
- **UV only**: `uv add`, `uv sync`, `uv run` — never `pip install`
- **Shared file drift**: when updating a shared file (e.g. `m_log.py`), update it in all three variants
- **Native Secret Management; uses local vault named 'LocalStore' for secret management
