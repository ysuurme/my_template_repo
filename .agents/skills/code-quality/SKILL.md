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

### Testing Strategy Taxonomy

Choose the test type based on what you're building. This answers "what to test" — the TDD section below answers "how to test it".

| Type | When | Key concern |
|---|---|---|
| UI | Dashboard or interactive app | End-user testing of interactive visualisations is expensive — limit to critical user journeys |
| Contract | REST APIs, service-to-service | Consumer-driven: test what the consumer expects, not what the producer assumes (→ `application-development`) |
| Integration | Data stores, ETL pipelines | Starting point for pipeline testing — check row counts, unique ID counts, min-max date ranges |
| Unit | Custom utility functions, data processing logic | Do NOT write unit tests for standard library or ML framework calls — trust the library; test your own logic only |

**ML-specific rule:** You should not need unit tests for calls into scikit-learn, XGBoost, PyTorch, or any well-tested ML framework. Write unit tests for your own data processing utilities, feature engineering functions, and validation logic.

**ETL starting point:** Integration tests on pipeline outputs (does Silver have the expected row count? are all branch IDs present? does the date range span the expected quarters?) catch more real bugs than unit tests on transformation logic.

### TDD Enforcement

Logic changes without a failing test first are an immediate rejection. No exceptions.

**Runner selection — choose based on project scope:**

| Context | Runner | Rationale |
|---|---|---|
| Simple scripts, utilities, learning context | `unittest` | Explicit class structure, no "magic" — every dependency is visible in the file. Hard to hide logic. Low setup overhead for isolated functions. |
| Full applications, data/ML pipelines | `pytest` | Assertion introspection shows colored diffs on complex failures. `@pytest.mark.parametrize` tests one function against N data distributions in 3 lines vs 30. Fixtures eliminate repeated DB/session setup. |

**Migration path for existing `unittest` projects:** `pytest` runs `unittest.TestCase` tests natively — switch the runner first (`uv run pytest`), keep existing tests untouched, write all new tests as plain functions with `assert`.

**`pytest` fixture discipline:** Define shared fixtures (DB sessions, test data) in `conftest.py`. Always add a comment on the fixture pointing to its `conftest.py` location — "spooky action at a distance" is the most common junior confusion point.

```python
# ✅ pytest — parametrize for data/ML testing
@pytest.mark.parametrize("input,expected", [
    ({"period": "2024Q1", "value": 10.0}, True),
    ({"period": "invalid",  "value": 10.0}, False),
])
def test_validate_record(input: dict, expected: bool) -> None:
    assert validate_record(input) == expected

# ✅ unittest — simple isolated function, no fixtures needed
class TestCalculateScore(unittest.TestCase):
    def test_returns_zero_for_empty_input(self) -> None:
        self.assertEqual(calculate_score([]), 0)
```

**Mocking:** `unittest.mock.MagicMock` — standard library only, no third-party mock alternatives. Works identically in both runners.

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
