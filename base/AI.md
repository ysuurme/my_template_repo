# AI.md — Project Context for AI Agents

## Project Identity

**{{ project_name }}** — {{ description }}

| Key | Value |
|-----|-------|
| Stack | Python + UV |
| Entry point | `main.py` |
| Config | `src/config.py` (pydantic-settings, loads `.env`) |

## Global Skills Available

> Invoke these before implementing manually.

| Skill | When to use |
|-------|-------------|
| `git-workflow` | Branching, commits, PRs |
| `review-code` | Code review, PR validation |
| `design-architecture` | Feature design, module boundaries |
| `design-infrastructure` | Dockerfiles, Terraform, CI/CD |
| `claude-api` | Anthropic SDK usage, prompt caching |

## Repository Layout

| Path | Purpose |
|------|---------|
| `main.py` | Entry point |
| `src/config.py` | Centralized config management |
| `src/utils/` | Generic transferable modules (`m_*.py`) |
| `src/<domain>/` | Domain-specific logic — add folders here as the project grows |
| `tests/` | Pytest suite, mirrors `src/` hierarchy |
| `.github/workflows/` | CI: lint + test on push/PR to `main` |

## Rules

1. **UV only.** `uv add`, `uv sync`, `uv run` — never `pip install`.
2. **No hardcoded secrets.** All config via `.env` + `src/config.py`.
3. **Test parity.** Every `src/**/*.py` has a matching `tests/**/test_*.py`.
4. **Lint must pass.** `ruff check` + `ruff format --check` before commit.
5. **Standard library first.** Prefer stdlib over third-party packages.
6. **`src/utils/` stays generic.** No project-specific logic in `m_*.py` files.

## Safety & Boundaries

- Never modify files outside the project root.
- Never install global packages or modify global configs.
- When in doubt, fail safely and surface the ambiguity.
