---
name: code-quality
description: Use when reviewing Python code, validating a pull request, approving a refactor, or enforcing code standards before merging
---

# Code Quality

## Overview

Enforces cognitive clarity, TDD compliance, and long-term codebase health at the function and module level. The goal is flat, typed, testable code — not merely functionally correct code.

## Scope

**Owns:** Python syntax standards (PEP-8, type hints, naming), function and module structure (indentation limits, size limits, guard clauses), TDD enforcement (failing test first, mocking), code review feedback format, standard library vs third-party dependency decisions.

**Does not own:** System or domain model design (→ `design-system`), domain-specific implementation patterns (→ domain skills), git operations or PR creation (→ `git-workflow`).

**Interfaces with:**
- `design-system` — architectural constraints define what code-quality enforces at the micro level
- Domain skills — code-quality applies universally; domain skills define what is being built

## When to Use

- **Trigger:** Code submitted for review or PR validation
- **Trigger:** Significant refactoring proposed
- **Trigger:** Modifying legacy code with no type hints, deep nesting, or missing tests

**Do NOT use for:**
- System design or bounded context mapping (→ `design-system`)
- Domain-specific implementation patterns (→ domain skills)

## Core Pattern

### Hard Limits — Immediate Rejection

| Constraint | Limit |
|---|---|
| Max indentation | 2 levels |
| Max function size | 30 lines |
| Max arguments | 4 |
| Type hints | 100% — no untyped functions |
| Style | Strict PEP-8 |
| Comments | "Why" only — never "What" |
| TDD | Logic changes require a failing test first |

### Guard Clauses & Loop Bouncers

Invert conditions to keep the happy path flat. Reject at the top of the function.

```python
# ❌ Nested
def process(data: dict):
    if data.get("valid"):
        if data.get("user"):
            execute_job(data["user"])

# ✅ Flat
def process(data: dict):
    if not data.get("valid"):
        return
    if not data.get("user"):
        return
    execute_job(data["user"])
```

Use `continue` and `break` aggressively in loops to avoid nesting.

### Immutability

- Prefer `frozen=True` dataclasses or strict Pydantic models
- All state variables initialized exclusively in `__init__`
- State modification through explicit methods on an Aggregate Root only

## Quick Reference

### Standard Library First

| Use | Instead of | Reason |
|---|---|---|
| `pathlib` | `os.path` | Object-oriented, cross-platform |
| `collections.Counter` | Manual loops/dicts | Optimized C implementation |
| `functools.lru_cache` | Custom cache dicts | Standardized, edge-case safe |
| `shutil` | Manual `os` file ops | Higher-level operations |

Exception: `requests` over `urllib` for HTTP calls. `numpy`/`pandas` for heavy analytical operations only — not basic math or CSV parsing.

### Naming Conventions

- Functions: Verb-Noun (`calculate_score`, `fetch_user`)
- No magic numbers — define in `constants.py`
- No single-letter variables except loop iterators

## Implementation

### TDD Enforcement

Logic changes without a failing test first are an immediate rejection. No exceptions.

- Runner: `pytest` — simple assert syntax, fixture injection
- Mocking: `unittest.mock.MagicMock` — standard library only, no third-party mock alternatives

### Communication Plan Gate

Require a bulleted implementation plan describing algorithmic intent before any code changes begin. No plan, no review.

### Feedback Format

Every review comment must follow this four-part format. Never critique without the paired solution.

- **[Observation]:** What is the violation? ("This function is 43 lines with 4 levels of nesting.")
- **[Principle]:** Why is it broken? ("High cognitive load makes this path error-prone.")
- **[Instruction]:** Before/after structural fix
- **[Reference]:** Which constraint was violated

## Common Mistakes

**Logic change without a failing test.**
Immediate rejection. No exceptions.

**Nested conditionals instead of guard clauses.**
Invert and return early. Two levels of nesting maximum.

**Missing type hints.**
Every function parameter and return type must be annotated. No untyped functions merge.

**Third-party dependency for standard library functionality.**
Exhaust stdlib options before introducing any PyPI package.
